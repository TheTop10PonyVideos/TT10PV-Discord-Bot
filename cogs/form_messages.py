import os, asyncio, json
from discord.ext import commands
from typing import override
from bot.whitelist_scheduling import schedule_whitelist
from config import server_api_url, server_auth_key
from discord import app_commands, Interaction
from typing import Literal
from bot import permissions
from server_actions import client
from aiohttp import ClientError


pipe_path = '/tmp/horse_vid_candidates'

class FormMessages(commands.Cog):
    """A cog that recieves video data from the form so that those not shared in the discord server can still easily be made searchable"""

    def __init__(self, bot):
        self.bot = bot
        self.buffer = b''
        self.pipe_fd = None

    @app_commands.command(description='Connect the form to have the bot receive search result candidates from it')
    @permissions.administrator()
    async def form(self, interaction: Interaction, action: Literal['connect', 'disconnect']):
        message = await self.connect(action == 'connect')

        await interaction.response.send_message(
            message or ('Connected to the form' if action == 'connect' else 'Disconnected from the form'),
            ephemeral=True
        )

    async def connect(self, value=True) -> str | None:
        if value:
            if not os.path.exists(pipe_path):
                os.mkfifo(pipe_path)

            self.pipe_fd = os.open(pipe_path, os.O_RDONLY | os.O_NONBLOCK)

            try:
                async with client.session.post(
                    f'{server_api_url}/bot_connect',
                    headers = { 'Cookie': f'uid={server_auth_key}' }
                ) as response:
                    if not response.ok:
                        raise Exception()

            except Exception as e:
                os.close(self.pipe_fd)
                self.pipe_fd = None
                return f'Could not connect to form: {e}'

            asyncio.get_running_loop().add_reader(self.pipe_fd, self.on_data)

        if self.pipe_fd is not None:
            asyncio.get_running_loop().remove_reader(self.pipe_fd)
            os.close(self.pipe_fd)
            self.pipe_fd = None
        else:
            return 'Already disconnected'

    @override
    async def cog_load(self):
        await self.connect()

    @override
    async def cog_unload(self):
        await self.connect(False)

    def on_data(self):
        chunk = os.read(self.pipe_fd, 1024)
        self.buffer += chunk

        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            line = line.decode()

            asyncio.create_task(schedule_whitelist(json.loads(line)))

    @override
    async def cog_app_command_error(self, interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message('Missing permissions to use this command', ephemeral=True)
        else:
            await interaction.response.send_message(str(error), ephemeral=True)

async def setup(bot):
    await bot.add_cog(FormMessages(bot))
