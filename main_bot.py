# main_bot.py
from dotenv import load_dotenv
import os
import json
import uuid
import subprocess
from pathlib import Path
import requests
import time

# Загружаем .env
load_dotenv()
MAIN_TOKEN = os.getenv("MAIN_BOT_TOKEN")
if not MAIN_TOKEN:
    print("ERROR: укажи MAIN_BOT_TOKEN в .env")
    exit(1)

API_URL = f"https://api.telegram.org/bot{MAIN_TOKEN}"
ROOT = Path.cwd()
INST_DIR = ROOT / "instances"
INST_DIR.mkdir(exist_ok=True)
DB_FILE = ROOT / "instances.json"

# load / save DB of instances
if DB_FILE.exists():
    INST = json.loads(DB_FILE.read_text(encoding="utf-8"))
else:
    INST = {}
    DB_FILE.write_text(json.dumps(INST), encoding="utf-8")

def save_db():
    DB_FILE.write_text(json.dumps(INST, ensure_ascii=False, indent=2), encoding="utf-8")

# get_updates simple poller (main bot)
def get_updates(offset=None, timeout=20):
    params = {"timeout": timeout}
    if offset:
        params["offset"] = offset
    r = requests.get(API_URL + "/getUpdates", params=params, timeout=timeout+10)
    return r.json()

def send_message(chat_id, text):
    requests.post(API_URL + "/sendMessage", data={"chat_id": chat_id, "text": text})

print("Main bot started. Polling for commands...")

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
            user = msg.get("from", {})
            text = msg.get("text", "") or ""

            # /start
            if text.startswith("/start"):
                send_message(
                    chat_id,
                    "👋 Привет! Я главный бот системы поддержки.\n\n"
                    "Я помогаю создавать твоих персональных support-ботов.\n\n"
                    "Команды:\n"
                    "/create <TOKEN> [имя] — создать support-бота\n"
                    "/list — список твоих ботов\n"
                    "/help — справка\n\n"
                    "👉 Чтобы начать, создай нового бота через @BotFather, получи его токен и пришли мне:\n"
                    "/create <TOKEN> [название]\n\n"
                    "После этого я запущу твоего support-бота, и ты сможешь добавить его в группу с товарами."
                )
                continue

            # /create <SUPPORT_TOKEN> [name]
            if text.startswith("/create"):
                parts = text.split(maxsplit=2)
                if len(parts) < 2:
                    send_message(chat_id, "Использование: /create <SUPPORT_BOT_TOKEN> [имя]")
                    continue

                support_token = parts[1].strip()
                name = parts[2].strip() if len(parts) > 2 else f"support-{str(uuid.uuid4())[:6]}"
                owner_id = user.get("id")

                instance_id = str(uuid.uuid4())[:8]
                instance_path = INST_DIR / instance_id
                instance_path.mkdir(parents=True, exist_ok=True)

                # write instance .env
                inst_env = instance_path / ".env"
                dee = os.getenv("DEESEEK_API_KEY", "") or ""
                inst_env.write_text(
                    f"SUPPORT_BOT_TOKEN={support_token}\n"
                    f"SUPPORT_OWNER_ID={owner_id}\n"
                    f"DEESEEK_API_KEY={dee}\n",
                    encoding="utf-8"
                )

                # copy support template to instance folder
                tpl = ROOT / "support_template.py"
                target = instance_path / "support_run.py"
                target.write_text(tpl.read_text(encoding="utf-8"), encoding="utf-8")

                # data.json initial
                dataf = instance_path / "data.json"
                dataf.write_text(
                    json.dumps({"group_id": None, "inventory": {}, "offset": None}, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )

                # record in DB (mask token)
                INST[instance_id] = {
                    "name": name,
                    "owner_id": owner_id,
                    "path": str(instance_path),
                    "token_masked": f"...{support_token[-6:]}"
                }
                save_db()

                # start support bot process
                try:
                    subprocess.Popen(["python", "support_run.py"], cwd=str(instance_path))
                    send_message(chat_id, f"✅ Support-бот '{name}' создан и запущен. Instance: {instance_id}\nДобавь этого бота в группу (добавлять должен ты).")
                except Exception as e:
                    send_message(chat_id, f"Ошибка запуска support-бота: {e}")
                continue

            # /list
            if text.startswith("/list"):
                owner = user.get("id")
                items = [(iid, info) for iid, info in INST.items() if info["owner_id"] == owner]
                if not items:
                    send_message(chat_id, "У тебя нет созданных ботов.")
                else:
                    s = "Твои боты:\n"
                    for iid, info in items:
                        s += f"- {info['name']} (id: {iid}, token: {info['token_masked']})\n"
                    send_message(chat_id, s)
                continue

            # /help
            if text.startswith("/help"):
                send_message(chat_id, "/create <TOKEN> [имя] — создать support-бота\n/list — список твоих ботов")
                continue

            # else ignore

    except Exception as e:
        print("Main poll error:", e)
        time.sleep(2)
