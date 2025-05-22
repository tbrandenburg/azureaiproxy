import httpx
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv() # Make sure your .env is loaded

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

async def test_azure_streaming():
    azure_url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_DEPLOYMENT}/chat/completions"
    params = {"api-version": AZURE_API_VERSION}
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "api-key": AZURE_API_KEY,
    }
    body = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Tell me a short story about a cat."},
        ],
        "stream": True,
    }

    print(f"Connecting to: {azure_url}")

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            async with client.stream(
                "POST",
                azure_url,
                params=params,
                headers=headers,
                json=body,
            ) as response:
                print(f"Received status code: {response.status_code}")
                print(f"Response headers: {response.headers}")

                if response.status_code != 200:
                    error_content = await response.aread()
                    print(f"Error from Azure: {error_content.decode()}")
                    return

                buffer = ""
                try:
                    async for chunk in response.aiter_bytes():
                        decoded_chunk = chunk.decode("utf-8")
                        buffer += decoded_chunk
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()

                            # CHECK FOR DONE MARKER FIRST!
                            if line == "data: [DONE]":
                                print("\n[DONE marker received]")
                                break # Exit the loop, stream is complete
                            elif line.startswith("data:"):
                                json_str = line[len("data: "):].strip()
                                if json_str:
                                    try:
                                        json_data = json.loads(json_str)
                                        if json_data.get("choices") and json_data["choices"][0].get("delta"):
                                            content = json_data["choices"][0]["delta"].get("content", "")
                                            if content:
                                                print(content, end="")
                                    except json.JSONDecodeError:
                                        print(f"\n[ERROR: Failed to parse JSON: {line}]\n")
                            else:
                                if line:
                                    print(f"\n[Non-data line: {line}]\n")
                except httpx.StreamClosed as e:
                    print(f"\n[ERROR: httpx.StreamClosed encountered during iteration: {e}]")
                except Exception as e:
                    print(f"\n[ERROR: An unexpected error occurred during iteration: {e}]")

        except httpx.RequestError as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_azure_streaming())