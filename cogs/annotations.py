from discord.ext import commands
from typing import Literal, override
from datetime import datetime
from bot import Bot, permissions
from bot.whitelist_scheduling import (
    SuccessView,
    RejectedView,
    update_post,
    unschedule_whitelist,
    check_post_exist
)
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
    get_video_data
)


class Annotating(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot


    @app_commands.command(description='Get the metadata and annotations associated with a video')
    async def get_details(self, interaction: Interaction, link: str):
        data = await get_video_data(link)

        if not data:
            embed = Embed(
                color=Color.red(),
                description='\n'.join(map(lambda a: a['details'], data['annotations']))
            )

        else:
            ma = data['manual_label']
            upload_date = datetime.fromisoformat(data['upload_date']).strftime('%b %d, %Y')
            description = [
                f'**Upload Date:** {upload_date}',
                f'**Duration:** {data['duration'] // 60}m {data['duration'] % 60}s',
                f'**Whitelisted:** {data['whitelisted']}'
            ]

            if data.get('reupload_of'):
                o_data = data['video_metadata']
                description.append(f'**Reupload Of:** [[{o_data['platform']}] {o_data['title']}]({data['reupload_of']})')

            embed = Embed(
                color=Color.blurple(),
                title=f'[{data['platform']}] {data['title']}',
                url=link,
                description='\n'.join(description)
            ).set_image(
                url=data['thumbnail']
            ).add_field(
                name='Annotations',
                value='\n\n'.join(f'**[{a['type']}]**\n{a['details']}' for a in data['annotations']) if ma is None else f'[{ma['label']}]\n{ma['content']}'
            ).set_footer(
                text=f'Uploaded to {data['platform']} by {data['uploader']}'
            )

        await interaction.response.send_message(embed=embed)


    @app_commands.command(description='Set whether the video can appear in the form search results. Default value is \'True\'')
    @permissions.series_staff()
    async def set_whitelist(self, interaction: Interaction, link: str, value: bool = True):
        res = await whitelist(link, value)
        video_key = (res.platform, res.video_id)

        post = await check_post_exist(video_key)

        if post:
            await unschedule_whitelist(video_key)

            await update_post(post, SuccessView() if value else RejectedView())

        await interaction.response.send_message(
            f'`[{res.platform}] {res.title}`\n{'added to' if value else 'removed from'} the whitelist',
            ephemeral=True
        )


    @app_commands.command(description='Makes the form suggest using the original video\'s link when the reupload is voted for')
    @permissions.series_staff()
    async def set_reupload(self, interaction: Interaction, link: str, original_link: str):
        res = await set_reupload(link, original_link)
        
        await interaction.response.send_message(
            f'`[{res.reupload_platform}] {res.reupload_title}`\nset as a reupload of\n`[{res.original_platform}] {res.original_title}`',
            ephemeral=True
        )


    @app_commands.command(description='Dissociates the video as being a reupload of another')
    @permissions.series_staff()
    async def reset_reupload(self, interaction: Interaction, link: str):
        res = await set_reupload(link, None)

        await interaction.response.send_message(
            f'`[{res.reupload_platform}] {res.reupload_title}`\nwill not be treated as a reupload',
            ephemeral=True
        )


    @app_commands.command(description='Manually set the eligibility of a video and a reason for it')
    @permissions.administrator()
    async def set_eligibility(self, interaction: Interaction, link: str, eligibility: Literal['eligible', 'ineligible'], reason: str):
        res = await set_eligibility(link, eligibility, reason)

        await interaction.response.send_message(
            f'`[{res.platform}] {res.title}`\nmarked as {eligibility} with the following reason\n```{reason}```',
            ephemeral=True
        )

    @app_commands.command(description='Remove any manual eligibility setting for a video')
    @permissions.administrator()
    async def reset_eligibility(self, interaction: Interaction, link: str):
        res = await set_eligibility(link, 'default')

        await interaction.response.send_message(
            f'`[{res.platform}] {res.title}`\nwill use automatically determined eligibility',
            ephemeral=True
        )


    @override
    async def cog_app_command_error(self, interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message('Missing permissions to use this command', ephemeral=True)
        else:
            await interaction.response.send_message(str(error), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Annotating(bot))
