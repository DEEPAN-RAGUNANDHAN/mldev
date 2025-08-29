import requests

def generate_text(content, openai_api_key, model="gpt-3.5-turbo"):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": content}
        ],
        "temperature": 0.8
    }

    response = requests.post(url, headers=headers, json=data).json()

    try:
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        raise Exception(f"Failed to get response: {response}")
