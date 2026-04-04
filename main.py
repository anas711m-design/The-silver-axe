import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def main():
    await bot.load_extension("cogs.voice_guard")
    await bot.start(TOKEN)

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user.name} - Monitoring disconnects.')

import asyncio
asyncio.run(main())
