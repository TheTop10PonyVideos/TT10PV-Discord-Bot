from discord.ext import commands
from typing import Literal, override
from datetime import datetime
from discord import (
    app_commands,
    Interaction,
    Embed,
    Color
)
from server_actions.annotations import (
    whitelist,
    set_eligibility,
    set_reupload,
    validate
)


class Annotating(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(description='Get the metadata and annotations associated with a video')
    async def get_details(self, interaction: Interaction, link: str):
        res = await validate(link)
        data = res.get('video_data')

        if not data:
            embed = Embed(
                color=Color.red(),
                description='\n'.join(map(lambda a: a['details'], res['field_flags']))
            )

        else:
            ma = data['manual_label']
            upload_date = datetime.fromisoformat(data['upload_date']).strftime('%b %d, %Y')

            embed = Embed(
                color=Color.blurple(),
                title=f'[{data['platform']}] {data['title']}',
                url=link,
                description=f'**Upload Date**: {upload_date}\n**Duration**: {data['duration'] // 60}m {data['duration'] % 60}s\n**Whitelisted**: {data['whitelisted']}'
            ).set_image(
                url=data['thumbnail']
            ).add_field(
                name='Annotations',
                value='\n\n'.join(f'**[{a['type']}]**\n{a['details']}' for a in res['field_flags']) if ma is None else f'[{ma['label']}]\n{ma['content']}'
            ).set_footer(
                text=f'Uploaded to {data['platform']} by {data['uploader']}'
            )

        await interaction.response.send_message(embed=embed)


    @app_commands.command(description='Set whether the video can appear in the form search results. Default value is \'True\'')
    async def set_whitelist(self, interaction: Interaction, link: str, value: bool = True):
        res = await whitelist(link, value)

        await interaction.response.send_message(
            f'`[{res.platform}] {res.title}`\n{'added to' if value else 'removed from'} the whitelist',
            ephemeral=True
        )


    @app_commands.command(description='Makes the form suggest using the original video\'s link when the reupload is voted for')
    async def set_reupload(self, interaction: Interaction, link: str, original_link: str):
        res = await set_reupload(link, original_link)
        
        await interaction.response.send_message(
            f'`[{res.reupload_platform}] {res.reupload_title}`\nset as a reupload of\n{res.original_platform} {res.original_title}',
            ephemeral=True
        )


    @app_commands.command(description='Dissociates the video as being a reupload of another')
    async def reset_reupload(self, interaction: Interaction, link: str):
        res = await set_reupload(link, None)

        await interaction.response.send_message(
            f'`[{res.reupload_platform}] {res.reupload_title}`\nwill not be treated as a reupload',
            ephemeral=True
        )


    @app_commands.command(description='Manually set the eligibility of a video and a reason for it')
    async def set_eligibility(self, interaction: Interaction, link: str, eligibility: Literal['eligible', 'ineligible'], reason: str):
        res = await set_eligibility(link, eligibility, reason)

        await interaction.response.send_message(
            f'`[{res.platform}] {res.title}`\nmarked as {eligibility} with the following reason\n```{reason}```',
            ephemeral=True
        )

    @app_commands.command(description='Remove any manual eligibility setting for a video')
    async def reset_eligibility(self, interaction: Interaction, link: str):
        res = await set_eligibility(link, link, 'default')

        await interaction.response.send_message(
            f'`[{res.platform}] {res.title}`\nwill use automatically determined eligibility',
            ephemeral=True
        )


    @override
    async def cog_app_command_error(self, interaction, error):
        await interaction.response.send_message(str(error), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Annotating(bot))
