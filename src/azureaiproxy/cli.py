import aiohttp
from aiohttp import web
import os
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import signal
import asyncio
import argparse

# === Logging Configuration ===
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file_path = log_dir / "aiohttp_proxy.log"

logger = logging.getLogger("aiohttp_proxy")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

file_handler = logging.FileHandler(log_file_path, mode="a")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# === Load .env ===
load_dotenv()

# === Configuration ===
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://fillme.net")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "o4-mini")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01")
AZURE_TIMEOUT = int(os.getenv("AZURE_TIMEOUT", 60))  # seconds

# === Routes ===

async def health_check(request):
    return web.Response(text="OK")

async def proxy_chat(request):
    """
    Proxies chat completion requests to Azure OpenAI.
    """
    try:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            logger.error("Invalid JSON received from client.")
            return web.json_response({"error": "Invalid JSON in request body"}, status=400)

        stream = body.get("stream", False)
        logger.debug(f"Incoming request headers:{str(dict(request.headers)).strip()}")
        logger.info(f"{datetime.now()} - Forwarding request to Azure (stream={stream})")

        azure_url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/chat/completions"
        params = {"api-version": AZURE_OPENAI_API_VERSION}
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if stream else "application/json",
            "User-Agent": "AiohttpProxy/1.0",
            "api-key": AZURE_OPENAI_API_KEY,
        }

        logger.debug(f"Using URL: {azure_url}")

        # === Proxy configuration ===
        proxy_url = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        if proxy_url:
            logger.debug(f"Using proxy: {proxy_url}")
        else:
            logger.debug("No proxy configured.")

        timeout = aiohttp.ClientTimeout(total=AZURE_TIMEOUT)
        connector = aiohttp.TCPConnector(ssl=False)  # use ssl=True if proxy has valid cert

        async with aiohttp.ClientSession(headers=headers, timeout=timeout, connector=connector) as session:
            request_kwargs = {
                "params": params,
                "json": body,
            }
            if proxy_url:
                request_kwargs["proxy"] = proxy_url
            logger.debug(f"Outgoing request: url={azure_url}, params={params}, headers={headers}, proxy={request_kwargs.get('proxy')}")

            async with session.post(azure_url, **request_kwargs) as azure_response:
                logger.debug(f"Azure response status: {azure_response.status}")
                logger.debug(f"Azure response headers: {dict(azure_response.headers)}")
                if azure_response.status != 200:
                    error_detail = await azure_response.text()
                    logger.error(f"Azure returned non-200: {azure_response.status} - {error_detail}")
                    return web.json_response(
                        {"error": f"Azure error {azure_response.status}: {error_detail}"},
                        status=azure_response.status
                    )

                if not stream:
                    return await _handle_non_streaming(azure_response)

                return await _handle_streaming(azure_response, request)

    except Exception as e:
        logger.exception("General proxy error occurred.")
        return web.json_response({"error": f"Internal proxy error: {e}"}, status=500)

# === Azure response handlers ===
async def _handle_non_streaming(azure_response):
    text = await azure_response.text()
    try:
        json_response = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse Azure JSON response")
        return web.Response(text=text, status=azure_response.status)
    return web.json_response(json_response, status=azure_response.status)

async def _handle_streaming(azure_response, request):
    web_response = web.StreamResponse(status=200, headers={
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    })
    await web_response.prepare(request)
    buffer = ""
    try:
        async for chunk in azure_response.content.iter_any():
            decoded = chunk.decode("utf-8")
            buffer += decoded
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if line == "data: [DONE]":
                    logger.debug("Azure stream completed.")
                    await web_response.write(b"data: [DONE]\n\n")
                    await web_response.write_eof()
                    return web_response
                if line.startswith("data:"):
                    payload_str = line[len("data:"):].strip()
                    if payload_str:
                        try:
                            payload = json.loads(payload_str)
                            if "choices" in payload and not payload["choices"]:
                                continue
                            await web_response.write(f"data: {json.dumps(payload)}\n\n".encode("utf-8"))
                        except json.JSONDecodeError as e:
                            logger.error(f"Stream decode error: {e}")
                            await web_response.write(
                                f"data: [ERROR] Invalid JSON format: {payload_str}\n\n".encode("utf-8"))
                elif line:
                    await web_response.write(f"{line}\n\n".encode("utf-8"))
        if buffer:
            await web_response.write(f"{buffer}\n\n".encode("utf-8"))
        await web_response.write_eof()
        return web_response
    except aiohttp.ClientError as e:
        logger.exception(f"Client error during streaming: {e}")
        return web.json_response({"error": f"Streaming client error: {e}"}, status=500)
    except Exception as e:
        logger.exception(f"Unexpected streaming error: {e}")
        return web.json_response({"error": f"Unexpected streaming error: {e}"}, status=500)

# === App Initialization ===

def create_app():
    app = web.Application()
    app.router.add_post("/v1/chat/completions", proxy_chat)
    app.router.add_get("/healthz", health_check)
    return app

# === Graceful Shutdown ===

def main():
    parser = argparse.ArgumentParser(description="Proxy server")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server")
    args = parser.parse_args()
    app = create_app()
    runner = web.AppRunner(app)

    async def start_server():
        await runner.setup()
        site = web.TCPSite(runner, host="127.0.0.1", port=args.port)
        await site.start()
        logger.info(f"AIOHTTP proxy server started on http://127.0.0.1:{args.port}")

        # Log proxy environment
        if os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY"):
            logger.info(f"Proxy detected: HTTP_PROXY={os.getenv('HTTP_PROXY')}, HTTPS_PROXY={os.getenv('HTTPS_PROXY')}")
        else:
            logger.info("No proxy env vars set.")

        while True:
            await asyncio.sleep(3600)

    loop = asyncio.get_event_loop()

    def shutdown():
        logger.info("Shutting down server...")
        loop.create_task(runner.cleanup())
        loop.stop()

    loop.add_signal_handler(signal.SIGINT, shutdown)
    loop.add_signal_handler(signal.SIGTERM, shutdown)

    try:
        loop.run_until_complete(start_server())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Server interrupted, exiting...")
    finally:
        loop.close()

if __name__ == "__main__":
    main()
