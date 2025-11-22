# main.py
import os
import asyncio
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import yt_dlp
import tempfile
import shutil

# ========== Flask keep-alive ==========
app = Flask(__name__)

@app.route("/")
def home():
    return "Music bot is running!", 200

def run_web():
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)

# ========== Discord Bot setup ==========
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN environment variable not set. Set TOKEN in Render Environment Variables.")

# yt-dlp options (no download, just get stream URL)
YTDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "geo_bypass": True,
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTS)

FFMPEG_BEFORE_OPTS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
FFMPEG_OPTIONS = "-vn"

# helper: get a direct streamable URL from yt-dlp info
def extract_stream_url(info_dict):
    # If it's a search result, info might contain 'entries'
    if "entries" in info_dict:
        entries = info_dict["entries"]
        if not entries:
            return None, None
        info = entries[0]
    else:
        info = info_dict

    # choose best audio format url
    formats = info.get("formats") or []
    # prefer audio-only formats
    audio_formats = [f for f in formats if f.get("acodec") and (f.get("vcodec") in (None, "none", "none"))]
    if audio_formats:
        fmt = audio_formats[-1]  # usually best is last
    elif formats:
        fmt = formats[-1]
    else:
        # fallback: sometimes direct url is available in info['url']
        if info.get("url"):
            return info["url"], info.get("title", "Unknown")
        return None, info.get("title", "Unknown")

    return fmt.get("url"), info.get("title", "Unknown")

async def get_info(query):
    loop = asyncio.get_event_loop()
    try:
        # ytsearch: if query not a URL, default_search will search automatically
        info = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        return info
    except Exception as e:
        # try a search fallback
        try:
            info = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{query}", download=False))
            return info
        except Exception as e2:
            raise e

# ========== Bot events & commands ==========
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    print("Bot is ready. Waiting for commands...")

@bot.command(name="join")
async def join(ctx):
    """讓 bot 加入使用者所在的語音頻道"""
    if ctx.author.voice is None or ctx.author.voice.channel is None:
        return await ctx.send("❌｜你不在語音頻道內，無法加入。")

    channel = ctx.author.voice.channel
    try:
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
            await ctx.send(f"🔁｜已移動到語音頻道：**{channel.name}**")
        else:
            await channel.connect()
            await ctx.send(f"🎧｜已加入語音頻道：**{channel.name}**")
    except Exception as e:
        await ctx.send(f"❌｜加入語音頻道失敗：{e}")

@bot.command(name="leave")
async def leave(ctx):
    """讓 bot 離開語音頻道"""
    vc = ctx.voice_client
    if not vc:
        return await ctx.send("⚠️｜我目前不在語音頻道中。")
    await vc.disconnect()
    await ctx.send("👋｜已離開語音頻道。")

@bot.command(name="stop")
async def stop(ctx):
    """停止播放並清除音源"""
    vc = ctx.voice_client
    if not vc or not vc.is_connected():
        return await ctx.send("⚠️｜我不在語音頻道中。")
    vc.stop()
    await ctx.send("⏹️｜已停止播放。")

@bot.command(name="pause")
async def pause(ctx):
    vc = ctx.voice_client
    if not vc or not vc.is_playing():
        return await ctx.send("⚠️｜目前沒有播放中的音樂。")
    vc.pause()
    await ctx.send("⏸️｜已暫停。")

@bot.command(name="resume")
async def resume(ctx):
    vc = ctx.voice_client
    if not vc or not vc.is_paused():
        return await ctx.send("⚠️｜目前沒有暫停中的音樂。")
    vc.resume()
    await ctx.send("▶️｜已恢復播放。")

@bot.command(name="play")
async def play(ctx, *, query: str = None):
    """
    使用方式：
    !play <url or keywords>
    或直接 !play 然後在頻道內回覆要播放的網址或關鍵字（會在頻道詢問並等候回覆）
    """
    author = ctx.author

    # 使用者沒有在語音頻道
    if not author.voice or not author.voice.channel:
        return await ctx.reply("⚠️｜你需要先加入語音頻道才能使用此功能！")

    channel = author.voice.channel

    # connect bot to voice channel if not connected
    vc = ctx.voice_client
    if not vc:
        try:
            vc = await channel.connect()
            await asyncio.sleep(0.3)
        except Exception as e:
            return await ctx.send(f"❌｜無法連接語音頻道：{e}")

    # if no query provided, ask user in the channel
    if not query:
        ask_msg = await ctx.send("🎵｜要播放的音樂網址或關鍵字是什麼呢？請在 **60 秒內** 回覆。")
        def check(m):
            return m.author == author and m.channel == ctx.channel
        try:
            reply = await bot.wait_for("message", check=check, timeout=60)
            query = reply.content.strip()
            # 嘗試刪除提示與使用者回覆（若機器人有權限）
            try:
                await ask_msg.delete()
                await reply.delete()
            except:
                pass
        except asyncio.TimeoutError:
            return await ctx.send("⏳｜超過 60 秒未回覆，播放取消。")

    # Now we have query (either url or search keywords)
    await ctx.send("🔎｜正在搜尋…")
    try:
        info = await get_info(query)
    except Exception as e:
        return await ctx.send(f"❌｜搜尋歌曲失敗：{e}")

    stream_url, title = extract_stream_url(info)
    if not stream_url:
        return await ctx.send("❌｜找不到可播放的串流網址，請確認網址或改用關鍵字。")

    # construct ffmpeg source
    source = discord.FFmpegPCMAudio(
        stream_url,
        executable="ffmpeg",
        before_options=FFMPEG_BEFORE_OPTS,
        options=FFMPEG_OPTIONS
    )

    # Play
    try:
        # if already playing, stop and play new
        if vc.is_playing():
            vc.stop()
        vc.play(source, after=lambda e: print("Player error:", e) if e else None)
    except Exception as e:
        return await ctx.send(f"❌｜播放失敗：{e}")

    # send feedback and DM the user
    try:
        await ctx.send(f"▶️｜正在播放：**{title}**")
        try:
            await author.send(f"🎧｜已為你開始播放：**{title}**")
        except:
            # DM 失敗就不用理會
            pass
    except Exception as e:
        print("Send message error:", e)

# small helpful command
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("Pong! 🏓")

# ========== Start bot and Flask ==========
if __name__ == "__main__":
    # start the web server in a background thread for Render keepalive
    Thread(target=run_web, daemon=True).start()
    # run bot
    bot.run(TOKEN)
