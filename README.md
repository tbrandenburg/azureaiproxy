# azureaiproxy

A lightweight proxy and UI for Azure OpenAI, designed to provide a local API-compatible interface and simple user interface for interacting with Azure-hosted language models. The core idea is to make Azure OpenAI endpoints compatible with the OpenAI API, enabling tools and clients built for OpenAI to work seamlessly with Azure's service.



## Project Structure

```
azureaiproxy/
├── src/azureaiproxy/
│   ├── __init__.py
│   ├── cli.py
│   └── ui.py
├── tests/
│   ├── integration/
│   │   └── test_stream.py
│   └── test_basic.py
├── logs/
├── LICENSE
├── README.md
├── requirements.txt
└── pyproject.toml
```

## Usage

**Note:** You must configure the following environment variables in a `.env` file at the project root. Example:

```env
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-model-name
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_API_VERSION=2023-05-15
```

### 1. Create and activate a virtual environment (recommended)

```sh
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Run the proxy

```sh
python3 -m azureaiproxy.cli [--port PORT] [--log-headers] [--log-bodies]
```

**Command line options:**
- `--port PORT`: Port to bind the server (default: 8000)
- `--log-headers`: Enable logging of HTTP headers for requests and responses
- `--log-bodies`: Enable logging of HTTP request and response bodies
- `--help`: Show help message and exit

**Examples:**
```sh
# Run with default settings (no detailed HTTP logging)
python3 -m azureaiproxy.cli

# Run on port 9000 with header logging enabled
python3 -m azureaiproxy.cli --port 9000 --log-headers

# Run with both header and body logging for debugging
python3 -m azureaiproxy.cli --log-headers --log-bodies
```

**Note:** Header and body logging can generate verbose output and may expose sensitive information. Use these options primarily for debugging and development.

### 3. Run the UI

```sh
python3 -m azureaiproxy.ui
```

## Configuration in Zed

```json
{
  // ...other config...
  "language_models": {
    "openai": {
      "api_url": "http://127.0.0.1:8000/v1",
      "available_models": [
        {
          "name": "azure-openai",
          "display_name": "Azure OpenAI",
          "max_tokens": 65536
        }
      ],
      "version": "1"
    }
  }
}
```

## Development

- Install dependencies:
  ```sh
  pip install -e .[dev]
  ```
- Run tests:
  ```sh
  python -m unittest discover tests
  ```

## License

This project is licensed under the Apache License 2.0.
