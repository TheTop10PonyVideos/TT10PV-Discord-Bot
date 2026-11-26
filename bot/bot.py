from discord.ext import commands
from server_actions import client
from pathlib import Path
from config import output_channel_id
import bot.whitelist_scheduling as ws


class Bot(commands.Bot):
    def __init__(self, command_prefix, **kwargs):
        super().__init__(command_prefix, **kwargs)

    async def setup_hook(self):
        await client.create_session()

        self.output_channel = await self.fetch_channel(output_channel_id)
        ws.set_output_channel(self.output_channel)

        for file in Path('./cogs').glob('*.py'):
            await self.load_extension(f'cogs.{file.stem}')

        await self.tree.sync()

        self.add_dynamic_items(
            ws.WhitelistButton, 
            ws.RejectButton,
            ws.RetryButton,
            ws.UndoWhitelistButton,
            ws.EligibilitySelect
        )

    async def close(self):
        await client.session.close()
        await super().close()
