import os
import asyncio
import discord
from discord.ext import commands
import wavelink

# ========== 1️⃣ Fake Web Server（讓 Render 偵測到 PORT） ==========
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_web():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# 啟動 Fake Web Server
Thread(target=run_web).start()

# ========== 2️⃣ Discord Bot 基本設定 ==========
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

LAVALINK_HOST = os.getenv("LAVALINK_HOST")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT"))
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD")
LAVALINK_SECURE = os.getenv("LAVALINK_SECURE", "false").lower() == "true"

print("===== Lavalink Config =====")
print("HOST:", LAVALINK_HOST)
print("PORT:", LAVALINK_PORT)
print("PASS:", LAVALINK_PASSWORD)
print("SECURE:", LAVALINK_SECURE)
print("===========================")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ========== 3️⃣ Bot Ready → 連接 Lavalink ==========
@bot.event
async def on_ready():
    print(f"Bot 已啟動：{bot.user}")

    await asyncio.sleep(1)

    url = f"http{'s' if LAVALINK_SECURE else ''}://{LAVALINK_HOST}:{LAVALINK_PORT}"
    print(f"Connecting Lavalink → {url}")

    try:
        await wavelink.Pool.connect(
            nodes=[
                wavelink.Node(
                    uri=url,
                    password=LAVALINK_PASSWORD,
                    secure=LAVALINK_SECURE
                )
            ],
            client=bot
        )
        print("✔️ Lavalink 連接成功！")
    except Exception as e:
        print("❌ Lavalink 連線失敗：", e)


# ========== 4️⃣ 音樂指令 ==========
@bot.command()
async def join(ctx):
    if ctx.author.voice is None:
        return await ctx.reply("你需要在語音頻道內。")

    channel = ctx.author.voice.channel
    await channel.connect(cls=wavelink.Player)
    await ctx.reply(f"已加入：{channel}")

@bot.command()
async def play(ctx, *, search: str):
    if ctx.voice_client is None:
        return await ctx.reply("Bot 尚未加入語音頻道，請先使用 `!join`")

    query = await wavelink.Playable.search(search)
    if not query:
        return await ctx.reply("找不到歌曲。")

    track = query[0]
    await ctx.voice_client.play(track)
    await ctx.reply(f"🎵 正在播放：**{track.title}**")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        return await ctx.reply("已離開語音頻道。")
    await ctx.reply("Bot 不在語音頻道。")


# ========== 5️⃣ 啟動 Bot ==========
bot.run(TOKEN)
