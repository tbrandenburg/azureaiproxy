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
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "o4-mini")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01")
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
        logger.debug(f"Incoming request body:\n{json.dumps(body, indent=2)}")
        logger.info(f"{datetime.now()} - Forwarding request to Azure (stream={stream})")

        azure_url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_DEPLOYMENT}/chat/completions"
        params = {"api-version": AZURE_API_VERSION}
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if stream else "application/json",
            "User-Agent": "AiohttpProxy/1.0",
            "api-key": AZURE_API_KEY,
        }

        timeout = aiohttp.ClientTimeout(total=AZURE_TIMEOUT)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.post(azure_url, params=params, json=body) as azure_response:
                if azure_response.status != 200:
                    error_detail = await azure_response.text()
                    logger.error(f"Azure returned non-200: {azure_response.status} - {error_detail}")
                    return web.json_response(
                        {"error": f"Azure error {azure_response.status}: {error_detail}"},
                        status=azure_response.status
                    )

                if not stream:
                    logger.info("Non-streaming response mode.")
                    json_response = await azure_response.json()
                    return web.json_response(json_response, status=200)

                # Streaming mode
                logger.info("Streaming response mode.")
                web_response = web.StreamResponse(status=200, headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive"
                })
                await web_response.prepare(request)

                buffer = ""
                try:
                    async for chunk in azure_response.content.iter_any():
                        decoded_chunk = chunk.decode("utf-8")
                        buffer += decoded_chunk

                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()

                            if line == "data: [DONE]":
                                logger.debug("Azure stream completed.")
                                await web_response.write(b"data: [DONE]\n\n")
                                break

                            if line.startswith("data:"):
                                json_str = line[6:].strip()
                                if json_str:
                                    try:
                                        payload = json.loads(json_str)
                                        if "choices" in payload and not payload["choices"]:
                                            continue
                                        await web_response.write(f"data: {json.dumps(payload)}\n\n".encode("utf-8"))
                                    except json.JSONDecodeError as e:
                                        logger.error(f"Stream decode error: {e}")
                                        await web_response.write(
                                            f"data: [ERROR] Invalid JSON format: {json_str}\n\n".encode("utf-8"))
                            elif line:
                                await web_response.write(f"{line}\n\n".encode("utf-8"))

                    if buffer:
                        logger.debug(f"Remaining buffer: {buffer}")
                        await web_response.write(f"{buffer}\n\n".encode("utf-8"))

                    await web_response.write_eof()
                    return web_response

                except aiohttp.ClientError as e:
                    logger.exception(f"Client error during streaming: {e}")
                except Exception as e:
                    logger.exception(f"Unexpected streaming error: {e}")

    except Exception as e:
        logger.exception("General proxy error occurred.")
        return web.json_response({"error": f"Internal proxy error: {e}"}, status=500)

# === App Initialization ===

def create_app():
    app = web.Application()
    app.router.add_post("/v1/chat/completions", proxy_chat)
    app.router.add_get("/healthz", health_check)

    return app

# === Graceful Shutdown ===

def main():
    app = create_app()
    runner = web.AppRunner(app)

    async def start_server():
        await runner.setup()
        site = web.TCPSite(runner, host="127.0.0.1", port=8000)
        await site.start()
        logger.info("AIOHTTP proxy server started on http://127.0.0.1:8000")

        # Log proxy environment
        if os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY"):
            logger.info(f"Proxy detected: HTTP_PROXY={os.getenv('HTTP_PROXY')}, HTTPS_PROXY={os.getenv('HTTPS_PROXY')}")
        else:
            logger.info("No proxy env vars set.")

        # Wait indefinitely until shutdown
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
