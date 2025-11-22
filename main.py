import os
import asyncio
import discord
from discord.ext import commands
import wavelink
from flask import Flask
from threading import Thread

# ============================
# Flask 保持 Render Web Service 醒著
# ============================
app = Flask(__name__)

@app.route("/")
def home():
    return "Music Bot is running!"

def run_web():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ============================
# Discord Bot 設定
# ============================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 讀取 Render Variables
TOKEN = os.getenv("TOKEN")

LAVALINK_HOST = os.getenv("LAVALINK_HOST", "lavalink-replit.fly.dev")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT", "443"))
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")
LAVALINK_SECURE = True  # 你用免費雲端，必定 https

# ============================
# Bot Ready：連接 Lavalink
# ============================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    if not wavelink.Pool.nodes:
        await wavelink.Pool.connect(
            client=bot,
            nodes=[
                wavelink.Node(
                    uri=f"https://{LAVALINK_HOST}:{LAVALINK_PORT}",
                    password=LAVALINK_PASSWORD
                )
            ],
        )

    print("🎵 Lavalink Connected!")


# ============================
# 播放指令（使用 YouTube Relay，不會跳驗證！）
# ============================
@bot.command()
async def play(ctx):
    if not ctx.author.voice:
        return await ctx.reply("⚠️ 你必須先加入語音頻道！")

    channel = ctx.author.voice.channel
    vc: wavelink.Player = ctx.guild.voice_client

    # 如果沒有在語音頻道 → 加入
    if not vc:
        try:
            vc = await channel.connect(cls=wavelink.Player)
            await ctx.send("🔊 已加入語音頻道！")
        except Exception as e:
            return await ctx.send(f"❌｜無法加入語音：{e}")

    ask = await ctx.send("🎵 請輸入歌曲名稱或 YouTube 連結（60 秒內）")

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
        query = msg.content
        await ask.delete()
        try:
            await msg.delete()
        except:
            pass
    except asyncio.TimeoutError:
        return await ctx.send("⏳ 超時取消。")

    # 🎵 使用 Lavalink Relay 模式（不會遇到 YouTube Login）
    search_query = f"ytsearch:{query}"

    try:
        tracks = await wavelink.Playable.search(search_query)
    except Exception as e:
        return await ctx.send(f"❌ 搜尋時發生錯誤：{e}")

    if not tracks:
        return await ctx.send("❌ 找不到相關歌曲！")

    track = tracks[0]

    try:
        await vc.play(track)
    except Exception as e:
        return await ctx.send(f"❌ 播放失敗：{e}")

    await ctx.send(f"▶ 正在播放：**{track.title}**")


# ============================
# 離開
# ============================
@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        return await ctx.send("👋 已離開語音頻道")
    await ctx.send("⚠️ 我本來就不在語音頻道喔")


# ============================
# 啟動
# ============================
if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.run(TOKEN)
