import os
import discord
from discord.ext import tasks
from threading import Thread
from flask import Flask

TOKEN = os.getenv('DISCORD_BOT_TOKEN')  # Lấy token từ biến môi trường
CHANNEL_ID = 1375358813586329693  # Thay bằng ID kênh bạn muốn gửi tin nhắn (giữ nguyên số)

intents = discord.Intents.default()
intents.members = True  # Bật quyền lấy thông tin thành viên
intents.presences = True  # Bật quyền lấy trạng thái online/offline
client = discord.Client(intents=intents)

app = Flask(__name__)

counter = 0  # Đếm số lần đã gửi tin nhắn

def run_flask():
    app.run(host="0.0.0.0", port=8080)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    send_count_message.start()
    check_online_members.start()

@tasks.loop(seconds=60)
async def send_count_message():
    global counter
    counter += 1
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(str(counter))

@tasks.loop(seconds=5)
async def check_online_members():
    guild = client.guilds[0] if client.guilds else None
    channel = client.get_channel(CHANNEL_ID)
    if guild and channel:
        for member in guild.members:
            if member.status == discord.Status.online and not member.bot:
                await channel.send(f"Hello @{member.display_name}")
                break  # Chỉ gửi 1 lần cho 1 thành viên online đầu tiên

@app.route('/')
def home():
    return "Bot is running!", 200

if __name__ == "__main__":
    Thread(target=run_flask).start()
    client.run(TOKEN)