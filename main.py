import os
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands, tasks
from threading import Thread
from flask import Flask
import openai
import time

# ==================== CẤU HÌNH ====================
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')  # Lấy token từ biến môi trường

# Lấy tất cả API key bắt đầu bằng GPT_API_KEY_
GPT_API_KEYS = [
    value for key, value in os.environ.items()
    if key.startswith("GPT_API_KEY_") and value
]

HISTORY_CHANNEL_NAME = "log-chat"  # Kênh lưu lịch sử hội thoại
GPT_MODEL = "gpt-4"
CHANNEL_ID = 1375358813586329693  # Thay bằng ID kênh bạn muốn gửi tin nhắn
# ==================================================

# === GPT API Key Manager ===
class GPTKeyManager:
    def __init__(self, api_keys):
        self.api_keys = api_keys
        self.current_index = 0
        self.failed_keys = set()

    def rotate_key(self):
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        print(f"🔁 Đang chuyển sang API key thứ {self.current_index + 1}")

    def get_current_key(self):
        return self.api_keys[self.current_index]

    def all_keys_failed(self):
        return len(self.failed_keys) >= len(self.api_keys)

    def mark_failed(self):
        self.failed_keys.add(self.get_current_key())

    def reset_failed(self):
        self.failed_keys.clear()

    def request_chat_completion(self, messages, **kwargs):
        retries = 0
        while retries < len(self.api_keys):
            api_key = self.get_current_key()
            client = openai.OpenAI(api_key=api_key)
            try:
                response = client.chat.completions.create(
                    model=GPT_MODEL,
                    messages=messages,
                    **kwargs
                )
                return response
            except openai.OpenAIError as e:
                print(f"⛔ OpenAI error: {e}")
            except Exception as e:
                print(f"⚠️ Lỗi khác: {e}")

            self.mark_failed()
            self.rotate_key()
            retries += 1
            time.sleep(1)

        print("🛑 Hết lượt ở tất cả API key. Tạm dừng.")
        return None

# === Thiết lập bot Discord ===
intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

gpt_manager = GPTKeyManager(GPT_API_KEYS)

app = Flask(__name__)

counter = 0  # Đếm số lần đã gửi tin nhắn
online_members = set()  # Lưu user_id của các thành viên đang online

def run_flask():
    app.run(host="0.0.0.0", port=8080)

@app.route('/')
def home():
    return "Bot is running!", 200

# === Lấy lịch sử chat từ kênh log ===
async def get_chat_history(guild: discord.Guild, limit=15):
    history_channel = discord.utils.get(guild.text_channels, name=HISTORY_CHANNEL_NAME)
    if not history_channel:
        return []

    messages = [msg async for msg in history_channel.history(limit=limit)]
    history = [
        {"role": "user" if m.author != bot.user else "assistant", "content": m.content}
        for m in reversed(messages)
    ]
    return history

# === Lưu tin nhắn vào kênh log ===
async def log_message(guild: discord.Guild, message: discord.Message, override_content=None):
    log_channel = discord.utils.get(guild.text_channels, name=HISTORY_CHANNEL_NAME)
    if log_channel:
        content = override_content if override_content else message.content
        author = "Bot" if message.author == bot.user else message.author.display_name
        await log_channel.send(f"{author}: {content}")

# === Phản hồi tin nhắn với GPT ===
async def respond_to_message(message: discord.Message):
    if message.author == bot.user:
        return

    if bot.user.mention not in message.content:
        return

    chat_history = await get_chat_history(message.guild, limit=15)
    chat_history.append({"role": "user", "content": message.content})

    response = gpt_manager.request_chat_completion(
        messages=chat_history,
        max_tokens=200,
        temperature=0.7
    )

    if response:
        reply = response.choices[0].message.content.strip()
        await message.channel.send(reply)

        # Log lại cả câu hỏi và câu trả lời
        await log_message(message.guild, message)
        await log_message(message.guild, message, override_content=reply)
    else:
        await message.channel.send("🤖 Bot tạm nghỉ do hết lượt API. Vui lòng thử lại sau!")

# === Sự kiện on_ready ===
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    send_count_message.start()
    check_online_members.start()

# === Sự kiện on_message ===
@bot.event
async def on_message(message):
    await respond_to_message(message)
    await bot.process_commands(message)

# === Task gửi số đếm mỗi 60s ===
@tasks.loop(seconds=60)
async def send_count_message():
    global counter
    counter += 1
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(str(counter))

# === Task kiểm tra thành viên online mỗi 5s ===
@tasks.loop(seconds=5)
async def check_online_members():
    guild = bot.guilds[0] if bot.guilds else None
    channel = bot.get_channel(CHANNEL_ID)
    global online_members
    if guild and channel:
        current_online = set()
        for member in guild.members:
            if member.status == discord.Status.online and not member.bot:
                current_online.add(member.id)
                if member.id not in online_members:
                    await channel.send(f"Hello @{member.display_name}")
        # Cập nhật lại trạng thái online
        online_members.clear()
        online_members.update(current_online)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    print("🤖 Đang khởi động bot...")
    bot.run(DISCORD_BOT_TOKEN)