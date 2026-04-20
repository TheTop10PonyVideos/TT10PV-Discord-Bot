from discord import Intents
from discord.ext import commands
from config import bot_token
from bot import Bot


intents = Intents.default()
intents.message_content = True

bot = Bot(commands.when_mentioned, intents=intents)


@bot.event
async def on_ready():
    print('Ready!')


bot.run(bot_token)
