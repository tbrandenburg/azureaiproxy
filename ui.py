import gradio as gr
import httpx

PROXY_API_URL = "http://localhost:8000/v1/chat/completions"

def chat_with_azure(user_input):
    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_input}
        ],
        "stream": False  # could add streaming in a future version
    }

    try:
        response = httpx.post(PROXY_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {e}"

iface = gr.Interface(
    fn=chat_with_azure,
    inputs=gr.Textbox(label="Your prompt", lines=4, placeholder="Ask something..."),
    outputs=gr.Textbox(label="Azure AI Response"),
    title="Azure OpenAI Chat Proxy UI",
    description="Send a prompt to your local Azure OpenAI proxy.",
)

if __name__ == "__main__":
    iface.launch()
