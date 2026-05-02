from discord import Intents
from discord.ext import commands
from config import bot_token
from bot import Bot
from bot.whitelist_scheduling import (
    load_schedule_cache,
    save_schedule_cache
)
import signal, asyncio


intents = Intents.default()
intents.message_content = True

bot = Bot(commands.when_mentioned, intents=intents)


@bot.event
async def on_ready():
    print('Ready!')


async def shutdown():
    save_schedule_cache()
    await bot.close()


async def main():
    load_schedule_cache()

    loop = asyncio.get_running_loop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))

    async with bot:
        await bot.start(bot_token)


asyncio.run(main())
