from discord.ext import commands
from server_actions import client
from pathlib import Path
from config import output_channel_id
from bot import whitelist_scheduling as ws


class Bot(commands.Bot):
    def __init__(self, command_prefix, **kwargs):
        super().__init__(command_prefix, **kwargs)

    async def setup_hook(self):
        await client.create_session()

        for file in Path('./cogs').glob('*.py'):
            await self.load_extension(f'cogs.{file.stem}')

        await self.tree.sync()

        Bot.output_channel = await self.fetch_channel(output_channel_id)
        ws.set_output_channel(Bot.output_channel)

        for view in (ws.SuccessView, ws.RejectedView):
            self.add_view(view())

        self.add_dynamic_items(
            ws.WhitelistButton, 
            ws.RejectButton,
            ws.RetryButton
        )

    async def close(self):
        await client.session.close()
        await super().close()
