# azureaiproxy

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
