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
python3 -m azureaiproxy.cli [--port PORT]
```

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
