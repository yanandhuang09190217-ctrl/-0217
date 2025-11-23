import discord
from discord.ext import commands
import wavelink
import os
import asyncio

# =============================
# 讀取環境變數
# =============================
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

LAVALINK_HOST = os.getenv("LAVALINK_HOST")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT", "2333"))
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD")
LAVALINK_SECURE = os.getenv("LAVALINK_SECURE", "false").lower() == "true"

# ---- Debug print ----
print("========== Lavalink Config ==========")
print("TOKEN:", "OK" if TOKEN else "❌ None")
print("HOST:", LAVALINK_HOST)
print("PORT:", LAVALINK_PORT)
print("PASSWORD:", LAVALINK_PASSWORD)
print("SECURE:", LAVALINK_SECURE)
print("=====================================")

if TOKEN is None:
    print("❌ 錯誤：你的 DISCORD_BOT_TOKEN 沒有設定！")
    print("請到 Render → Environment → 新增： DISCORD_BOT_TOKEN = <你的BotToken>")
    raise SystemExit


# =============================
# Discord Bot
# =============================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# =============================
# Bot 啟動事件
# =============================
@bot.event
async def on_ready():
    print(f"Bot 已啟動：{bot.user}")

    await asyncio.sleep(1)

    print("正在連線到 Lavalink 伺服器…")

    node = wavelink.Node(
        uri=f"http{'s' if LAVALINK_SECURE else ''}://{LAVALINK_HOST}:{LAVALINK_PORT}",
        password=LAVALINK_PASSWORD,
        secure=LAVALINK_SECURE
    )

    try:
        await wavelink.Pool.connect(nodes=[node], client=bot)
        print("✔️ 成功連線到 Lavalink！")
    except Exception as e:
        print("❌ 無法連線到 Lavalink：", e)


# =============================
# 指令
# =============================
@bot.command()
async def join(ctx):
    if not ctx.author.voice:
        return await ctx.reply("你需要在語音頻道內。")

    channel = ctx.author.voice.channel
    await channel.connect(cls=wavelink.Player)
    await ctx.reply(f"已加入：{channel}")


@bot.command()
async def play(ctx, *, search: str):
    if ctx.voice_client is None:
        return await ctx.reply("Bot 尚未加入語音頻道，用 `!join`")

    results = await wavelink.Playable.search(search)
    if not results:
        return await ctx.reply("找不到歌曲。")

    track = results[0]
    await ctx.voice_client.play(track)
    await ctx.reply(f"🎵 播放：**{track.title}**")


@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.reply("已離開語音頻道。")
    else:
        await ctx.reply("我沒有在語音頻道。")


# =============================
# 啟動 BOT
# =============================
bot.run(TOKEN)
