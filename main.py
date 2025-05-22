from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse, Response
import httpx
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import uvicorn

# === Logging Configuration ===

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file_path = log_dir / "proxy.log"

logger = logging.getLogger()
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
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "")

# === FastAPI App ===

app = FastAPI()

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

        async with httpx.AsyncClient(timeout=None) as client:
            if stream:
                azure_response = await client.stream(
                    "POST",
                    azure_url,
                    params=params,
                    headers=headers,
                    json=body,
                )

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

if __name__ == "__main__":
    logger.info("Starting Azure OpenAI proxy on http://127.0.0.1:8000")
    if os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY"):
        logger.info(f"Proxy detected in environment: HTTP_PROXY={os.getenv('HTTP_PROXY')}, HTTPS_PROXY={os.getenv('HTTPS_PROXY')}")
    else:
        logger.info("No proxy detected in environment.")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
