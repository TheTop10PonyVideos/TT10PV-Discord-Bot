from discord import Intents
from discord.ext import commands
from pathlib import Path
from config import bot_token
from server_actions import client


intents = Intents.default()
intents.message_content = True


class Bot(commands.Bot):
    async def setup_hook(self):
        await client.create_session()

        for file in Path('./cogs').glob('*.py'):
            await self.load_extension(f'cogs.{file.stem}')

        await self.tree.sync()
    
    async def close(self):
        await client.session.close()
        await super().close()


bot = Bot(None, intents=intents)


@bot.event
async def on_ready():
    print('Ready!')


bot.run(bot_token)
