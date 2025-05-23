import os
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands, tasks
from threading import Thread
from flask import Flask
import time
from gpt_chat import ask_gpt

# ==================== CẤU HÌNH ====================
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')  # Lấy token từ biến môi trường

CHANNEL_ID = 1375358813586329693  # Thay bằng ID kênh bạn muốn gửi tin nhắn
# ==================================================

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

app = Flask(__name__)

counter = 0  # Đếm số lần đã gửi tin nhắn
online_members = set()  # Lưu user_id của các thành viên đang online

def run_flask():
    app.run(host="0.0.0.0", port=8080)

@app.route('/')
def home():
    print("[Flask] / endpoint được gọi.")
    return "Bot is running!", 200

# === Sự kiện on_ready ===
@bot.event
async def on_ready():
    print(f"[Discord] Logged in as {bot.user}")
    send_count_message.start()
    check_online_members.start()

# === Sự kiện on_message ===
@bot.event
async def on_message(message):
    print(f"[on_message] Nhận tin nhắn từ {message.author}: {message.content}")
    # Nếu bot bị tag
    if bot.user.mention in message.content and not message.author.bot:
        prompt = message.content.replace(bot.user.mention, "").strip()
        if prompt:
            await message.channel.typing()
            reply = ask_gpt(prompt)
            await message.channel.send(reply)
    await bot.process_commands(message)

# === Task gửi số đếm mỗi 60s ===
@tasks.loop(seconds=60)
async def send_count_message():
    global counter
    counter += 1
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        print(f"[send_count_message] Gửi số đếm: {counter}")
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
                    print(f"[check_online_members] Hello @{member.display_name}")
                    await channel.send(f"Hello @{member.display_name}")
        # Cập nhật lại trạng thái online
        online_members.clear()
        online_members.update(current_online)

if __name__ == "__main__":
    print("[MAIN] Khởi động Flask và Discord bot...")
    Thread(target=run_flask).start()
    print("🤖 Đang khởi động bot...")
    bot.run(DISCORD_BOT_TOKEN)