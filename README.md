# azureaiproxy

## Usage

### 1. Run the proxy

```sh
python3 main.py
```

### 2. Run the UI

```sh
python3 ui.py
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