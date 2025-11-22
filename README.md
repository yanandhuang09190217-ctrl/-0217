Web-ready Music Bot (Render)
---------------------------

This package contains a Render-friendly web-version of your Discord music bot.
It uses a public Lavalink node (configurable with environment variables) so you
don't need to download or run Lavalink.jar locally.

Files:
  - main.py            : bot + small Flask webserver for health checks
  - requirements.txt   : dependencies (discord.py + wavelink 1.3.3)
  - Dockerfile         : Render-ready Dockerfile (installs ffmpeg)
  - README.md

How to deploy on Render:
 1. Create a new Web Service and connect this repo (or upload this ZIP).
 2. Set Environment variables in Render:
    - DISCORD_TOKEN = <your bot token>
    - LAVALINK_HOST = lavalink.botsfordiscord.com
    - LAVALINK_PORT = 443
    - LAVALINK_PASSWORD = youshallnotpass
    - LAVALINK_SECURE = true
    - (OPTIONAL) PORT = 10000
 3. Deploy. The web health endpoint will keep the service awake and the bot will connect to Lavalink.
 4. Use the bot in Discord: !play (follow prompts)

Notes:
 - Public Lavalink nodes can be unreliable; if you need higher stability I can help
   set up a private Lavalink (e.g., on Replit or a small VPS).
 - The Flask server runs in a background thread and is only used for health checks.