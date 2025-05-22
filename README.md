# azureaiproxy

## Usage

```sh
python3 main.py
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