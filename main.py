from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse, Response
import httpx
import os
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
import argparse
import uvicorn

# === Logging Configuration ===

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file_path = log_dir / "proxy.log"

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
console_handler.setFormatter(formatter)

file_handler = logging.FileHandler(log_file_path, mode="a")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# === FastAPI App ===

app = FastAPI()

# === Configuration ===

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://fillme.net")
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "o4-mini")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "")
CNTLM_PROXY = os.getenv("CNTLM_PROXY", "http://localhost:3128")

# Will be set in main()
PROXY = None


# === Proxy Endpoint ===

@app.post("/v1/chat/completions")
async def proxy_chat(request: Request):
    try:
        body = await request.json()
        stream = body.get("stream", False)

        logger.debug(f"Incoming request body:\n{body}")
        logger.info(f"{datetime.now()} - Forwarding request to Azure (stream={stream})")

        azure_url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_DEPLOYMENT}/chat/completions"
        params = {"api-version": AZURE_API_VERSION}
        headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_API_KEY
        }

        async with httpx.AsyncClient(timeout=None, proxies=PROXY) as client:
            if stream:
                stream_req = client.stream(
                    "POST",
                    azure_url,
                    params=params,
                    headers=headers,
                    json=body,
                )
                azure_response = await stream_req.__aenter__()

                async def stream_response():
                    try:
                        async for line in azure_response.aiter_lines():
                            if line.strip():
                                logger.debug(f"Stream chunk: {line.strip()}")
                                yield f"data: {line.strip()}\n\n"
                    finally:
                        await azure_response.aclose()

                return StreamingResponse(stream_response(), media_type="text/event-stream")

            else:
                azure_response = await client.post(
                    azure_url,
                    params=params,
                    headers=headers,
                    json=body,
                )
                content = await azure_response.aread()
                logger.debug(f"Azure response body:\n{content.decode('utf-8')}")
                return Response(content=content, media_type="application/json", status_code=azure_response.status_code)

    except Exception as e:
        logger.exception("Proxy error")
        return JSONResponse(status_code=500, content={"error": str(e)})


# === Main Entry Point ===

def main():
    global PROXY

    parser = argparse.ArgumentParser(description="Azure OpenAI proxy server.")
    parser.add_argument("--proxy", type=str, help="Proxy URL (e.g. http://localhost:3128)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind the proxy server")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the proxy server")
    args = parser.parse_args()

    if args.proxy:
        PROXY = {"http://": args.proxy, "https://": args.proxy}
        logger.info(f"Using proxy: {args.proxy}")
    else:
        PROXY = None
        logger.info("No proxy configured.")

    logger.info(f"Starting Azure OpenAI proxy on http://{args.host}:{args.port}")
    uvicorn.run("main:app", host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
