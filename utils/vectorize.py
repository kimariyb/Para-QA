from openai import OpenAI


# Deepseek API Key
API_KEY = ""

# Create a client instance
client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.deepseek.com"
) 

# Deepseek-V3 Chat API
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False
)

print(response.choices[0].message.content)