# support_template.py
import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("SUPPORT_BOT_TOKEN")
OWNER_ID = os.getenv("SUPPORT_OWNER_ID")
DEEPSEEK_KEY = os.getenv("sk-9ce012d61583463a99af5306693c6d91")

API_URL = f"https://api.telegram.org/bot{TOKEN}"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"  # эндпоинт DeepSeek

def send_message(chat_id, text):
    requests.post(API_URL + "/sendMessage", data={"chat_id": chat_id, "text": text})

def get_updates(offset=None, timeout=20):
    params = {"timeout": timeout}
    if offset:
        params["offset"] = offset
    r = requests.get(API_URL + "/getUpdates", params=params, timeout=timeout+10)
    return r.json()

def ask_deepseek(prompt):
    try:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Ты — вежливый support-бот магазина. Отвечай кратко, по делу и дружелюбно."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300
        }
        r = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        resp = r.json()
        return resp["choices"][0]["message"]["content"]
    except Exception as e:
        print("DeepSeek error:", e)
        return "Извините, произошла ошибка. Попробуйте ещё раз."

print("Support bot started...")
offset = None

while True:
    try:
        res = get_updates(offset)
        if not res.get("ok"):
            time.sleep(1)
            continue
        for u in res["result"]:
            offset = u["update_id"] + 1
            if "message" not in u:
                continue
            msg = u["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")

            # Только владелец может управлять ботом командами
            if str(chat_id) == OWNER_ID:
                if text.startswith("/ping"):
                    send_message(chat_id, "pong 🏓")
                    continue

            # Все остальные сообщения → в DeepSeek
            if text:
                answer = ask_deepseek(text)
                send_message(chat_id, answer)

    except Exception as e:
        print("Support bot error:", e)
        time.sleep(2)
