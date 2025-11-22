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

# ============================
# 讀取 Render 環境變數
# ============================
TOKEN = os.getenv("TOKEN")
LAVALINK_HOST = os.getenv("LAVALINK_HOST")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT", 2333))
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD")
LAVALINK_SECURE = os.getenv("LAVALINK_SECURE", "true").lower() == "true"
# ============================
# Bot Ready：連接 Lavalink
# ============================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    node_uri = f"{'https' if LAVALINK_SECURE else 'http'}://{LAVALINK_HOST}:{LAVALINK_PORT}"
    print(f"🌐 Connecting to Lavalink → {node_uri}")

    # 自動重試
    for i in range(5):
        try:
            await wavelink.Pool.connect(
                client=bot,
                nodes=[
                    wavelink.Node(
                        identifier="MY_NODE",
                        uri=node_uri,
                        password=LAVALINK_PASSWORD
                    )
                ],
                cache=False
            )

            # 👉 確保節點已成功連線
            node = wavelink.Pool.get_node()
            if node and node.status == wavelink.NodeStatus.CONNECTED:
                print("🎵 Lavalink Connected!")
                return
            
            raise Exception("Node not in CONNECTED state.")

        except Exception as e:
            print(f"❌ 第 {i+1}/5 次連接失敗：{e}")
            await asyncio.sleep(3)

    print("🚨 無法連線到 Lavalink，請檢查 HOST / PORT / 密碼 / https 設定是否正確！")

# ============================
# 播放指令
# ============================
@bot.command()
async def play(ctx):
    # 檢查節點是否在線
    node = wavelink.Pool.get_node()
    if not node or node.status != wavelink.NodeStatus.CONNECTED:
        return await ctx.send("❌｜Lavalink 尚未連線（請稍後再試）")

    if not ctx.author.voice:
        return await ctx.reply("⚠️ 你必須先加入語音頻道！")

    channel = ctx.author.voice.channel
    vc: wavelink.Player = ctx.guild.voice_client

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

    search_query = f"ytsearch:{query}"

    try:
        tracks = await wavelink.Playable.search(search_query)
    except Exception as e:
        return await ctx.send(f"❌ 搜尋錯誤：{e}")

    if not tracks:
        return await ctx.send("❌ 找不到歌曲！")

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
# 啟動 Bot（asyncio.run）
# ============================
async def main():
    Thread(target=run_web).start()
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
