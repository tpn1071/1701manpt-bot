import os
import openai

GPT_MODEL = "gpt-3.5-turbo"
GPT_API_KEYS = [
    value for key, value in os.environ.items()
    if key.startswith("GPT_API_KEY_") and value
]

def ask_gpt(prompt):
    for api_key in GPT_API_KEYS:
        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7
            )
            print("[ask_gpt] GPT trả lời thành công.")
            return response.choices[0].message.content.strip()
        except openai.OpenAIError as e:
            print(f"[ask_gpt] Lỗi với key {api_key[:8]}...: {e}")
        except Exception as e:
            print(f"[ask_gpt] Lỗi khác: {e}")
    return "🤖 Bot tạm nghỉ do hết lượt API. Vui lòng thử lại sau!"