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


def _create_request_config():
    """Create the configuration for the Azure OpenAI request."""
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
    return azure_url, params, headers, body


async def _handle_error_response(response):
    """Handle non-200 response codes."""
    error_content = await response.aread()
    print(f"Error from Azure: {error_content.decode()}")
    return False


def _parse_json_data(json_str):
    """Parse JSON data and extract content if available."""
    try:
        json_data = json.loads(json_str)
        choices = json_data.get("choices", [])
        if choices and choices[0].get("delta"):
            return choices[0]["delta"].get("content", "")
    except json.JSONDecodeError:
        print(f"\n[ERROR: Failed to parse JSON: data: {json_str}]\n")
    return None


def _process_data_line(line):
    """Process a data line from the stream."""
    if line == "data: [DONE]":
        print("\n[DONE marker received]")
        return "done"
    
    if line.startswith("data:"):
        json_str = line[len("data: "):].strip()
        if json_str:
            content = _parse_json_data(json_str)
            if content:
                print(content, end="")
        return "continue"
    
    if line:
        print(f"\n[Non-data line: {line}]\n")
    return "continue"


async def _process_stream_chunk(chunk, buffer):
    """Process a single chunk from the stream."""
    decoded_chunk = chunk.decode("utf-8")
    buffer += decoded_chunk
    
    while "\n" in buffer:
        line, buffer = buffer.split("\n", 1)
        line = line.strip()
        
        result = _process_data_line(line)
        if result == "done":
            return buffer, True
    
    return buffer, False


async def _handle_streaming_response(response):
    """Handle the streaming response from Azure OpenAI."""
    buffer = ""
    
    try:
        async for chunk in response.aiter_bytes():
            buffer, is_done = await _process_stream_chunk(chunk, buffer)
            if is_done:
                break
    except httpx.StreamClosed as e:
        print(f"\n[ERROR: httpx.StreamClosed encountered during iteration: {e}]")
    except Exception as e:
        print(f"\n[ERROR: An unexpected error occurred during iteration: {e}]")


async def test_azure_streaming():
    """Test Azure OpenAI streaming chat completions."""
    azure_url, params, headers, body = _create_request_config()
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
                    await _handle_error_response(response)
                    return

                await _handle_streaming_response(response)

        except httpx.RequestError as e:
            print(f"Request failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_azure_streaming())