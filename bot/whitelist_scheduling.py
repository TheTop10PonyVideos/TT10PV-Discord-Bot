from config import Roles
from server_actions.annotations import whitelist
from bot import Bot, emoji
from discord import (
    ButtonStyle,
    Embed,
    Interaction,
    Message,
    NotFound,
    ui
)
import asyncio, time


whitelist_post_ids = {}
scheduled_whitelists: dict[tuple, asyncio.Task] = {}


async def try_whitelist(interaction: Interaction, value=True):
    """Attempt to set a searchable value a video via button interaction, and update its view accordingly"""
    embed = interaction.message.embeds[0].copy()

    try:
        await whitelist(embed.url, value)

        embed.description = 'Whitelisted ' + emoji.pinkie_affirm if value else 'Not whitelisted'
        view = SuccessView() if value else RejectedView()

    except Exception as e:
        print(e)
        embed.description = ('Failed to whitelist ' if value else 'Failed to undo whitelist ') + emoji.pinkie_PANIC_AHHH_WTF
        view = FailView(value)

    await interaction.response.edit_message(embed=embed, view=view)


class PermissionedView(ui.View):
    """A view that checks a users permissions before allowing any interaction callbacks to run"""

    async def interaction_check(self, interaction):
        return (
            interaction.user.guild_permissions.administrator
            or any(role.id in (Roles.MODERATOR, Roles.SERIES_STAFF) for role in interaction.user.roles)
        )


class MainView(PermissionedView):
    def __init__(self, video_key):
        super().__init__(timeout=None)
        self.key = video_key
    
    @ui.button(label='Whitelist', emoji='📜', style=ButtonStyle.primary)
    async def whitelist(self, interaction: Interaction, btn: ui.Button):        
        await try_whitelist(interaction)

    @ui.button(label='Reject', emoji='❌', style=ButtonStyle.primary)
    async def reject(self, interaction: Interaction, btn: ui.Button):
        unschedule_whitelist(self.key)

        embed = interaction.message.embeds[0]
        embed.description = 'Not whitelisted'

        await interaction.response.edit_message(embed=embed, view=RejectedView())


class SuccessView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label='Undo', emoji='◀️', style=ButtonStyle.primary)
    async def undo(self, interaction: Interaction, btn: ui.Button):
        await try_whitelist(interaction, False)


class FailView(ui.View):
    def __init__(self, whitelisting: bool):
        super().__init__(timeout=None)
        self.whitelisting = whitelisting

    @ui.button(label='Retry', emoji='🔄')
    async def retry(self, interaction: Interaction, btn: ui.Button):
        await try_whitelist(interaction, self.whitelisting)


class RejectedView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label='Whitelist', emoji='📜', style=ButtonStyle.primary)
    async def whitelist(self, interaction: Interaction, btn: ui.Button):
        await try_whitelist(interaction)


async def update_post(post: Message, view: SuccessView | RejectedView | FailView):
    embed = post.embeds[0].copy()

    match view:
        case SuccessView():
            embed.description = 'Whitelisted ' + emoji.pinkie_affirm
        case RejectedView():
            embed.description = 'Not whitelisted'
        case FailView():
            embed.description = ('Failed to whitelist ' if view.whitelisting else 'Failed to undo whitelist ') + emoji.pinkie_PANIC_AHHH_WTF

    await post.edit(embed=embed, view=view)


async def check_post_exist(video_key):
    post_id = whitelist_post_ids.get(video_key)

    if post_id is None:
        scheduled_task = scheduled_whitelists.get(video_key)

        if scheduled_task is not None:
            scheduled_task.cancel()
            del scheduled_whitelists[video_key]

        return False

    try:
        return await Bot.instance.output_channel.fetch_message(post_id)
    except NotFound:
        return False


async def delay_whitelist(video_key, link, timeout):
    await asyncio.sleep(timeout)
    del scheduled_whitelists[video_key]

    post = await check_post_exist(video_key)

    if not post:
        return

    try:
        await whitelist(link)
    except Exception as e:
        print(e)
        await update_post(post, FailView(True))
        return

    await update_post(post, SuccessView())


async def schedule_whitelist(video_data, timeout: int):
    video_key = (video_data['platform'], video_data['video_id'])
    existing_post = whitelist_post_ids.get(video_key)

    if existing_post is not None:
        if existing_post == 'pending':
            return # post is already about to be made

        post = await check_post_exist(video_key)

        if post:
            return # already scheduled or rejected

    whitelist_post_ids[video_key] = 'pending'

    # eligible first since that only comes from manual checks
    priority = ['eligible', 'ineligible', 'maybe ineligible']

    for t in priority:
        if any(ann['type'] == t for ann in video_data['annotations']):
            eligibility = t
            break
    else:
        eligibility = 'eligible'

    whitelist_timestamp = int(time.time()) + timeout

    embed = Embed(
        title=video_data['title'],
        url=video_data['link'],
        description=f'Whitelisting <t:{whitelist_timestamp}:R>'
    ).set_image(
        url=video_data['thumbnail']
    ).add_field(
        name=eligibility.title(),
        value='\n'.join(f'- {ann.trigger}' for ann in video_data['annotations']) or '- No issues found'
    ).set_footer(
        text=f'By {video_data['uploader']} on {video_data['platform']}'
    )


    post = await Bot.instance.output_channel.send(embed=embed, view=MainView(video_key))

    whitelist_post_ids[video_key] = post.id
    scheduled_whitelists[video_key] = asyncio.create_task(delay_whitelist(video_key, video_data['link'], timeout))


def unschedule_whitelist(video_key):
    if task := scheduled_whitelists.get(video_key):
        task.cancel()
        del scheduled_whitelists[video_key]
