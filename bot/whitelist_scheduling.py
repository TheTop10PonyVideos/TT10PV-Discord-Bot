from config import Roles, schedule_cache_path
from server_actions.annotations import whitelist
from bot import emoji
from app_types import WLScheduleEntry
from typing import Literal
from discord.ui import Button, DynamicItem, View, button
from bot.permissions import PermissionMixin
from discord import (
    ButtonStyle,
    Embed,
    Interaction,
    Message,
    NotFound,
    TextChannel,
    User
)
import asyncio, time, json, re


whitelist_schedule: dict[tuple, WLScheduleEntry | Literal['pending']] = {}
output_channel: TextChannel = None


async def try_whitelist(interaction: Interaction, value=True):
    """Attempt to set a searchable value for a video via button interaction, and update its view accordingly"""
    embed = interaction.message.embeds[0].copy()

    try:
        await whitelist(embed.url, value)
        view = SuccessView() if value else RejectedView()
    except Exception as e:
        print(e)
        view = FailView(value)
    
    await update_post(interaction.message, view, interaction.user)


class MainView(View):
    def __init__(self, video_key):
        super().__init__(timeout=None)
        self.add_item(WhitelistButton(video_key))
        self.add_item(RejectButton(video_key))

class WhitelistButton(PermissionMixin, DynamicItem, template=r'whitelist:(?P<platform>[^:]+):(?P<vid_id>.+)'):
    def __init__(self, video_key):
        self.video_key = video_key
        platform, vid_id = video_key

        super().__init__(
            Button(
                label='Whitelist',
                emoji='📜',
                style=ButtonStyle.primary,
                custom_id=f'whitelist:{platform}:{vid_id}',
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: Interaction, item: Button, match: re.Match[str]):
        return cls((match['platform'], match['vid_id']))

    async def callback(self, interaction: Interaction):
        unschedule_whitelist(self.video_key)
        await try_whitelist(interaction)

class RejectButton(PermissionMixin, DynamicItem, template=r'reject:(?P<platform>[^:]+):(?P<vid_id>.+)'):
    def __init__(self, video_key):
        self.video_key = video_key
        platform, vid_id = video_key

        super().__init__(
            Button(
                label='Reject',
                emoji='❌',
                style=ButtonStyle.primary,
                custom_id=f'reject:{platform}:{vid_id}',
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: Interaction, item: Button, match: re.Match[str]):
        return cls((match['platform'], match['vid_id']))

    async def callback(self, interaction: Interaction):
        unschedule_whitelist(self.video_key)

        await update_post(interaction.message, RejectedView(), interaction.user)


class SuccessView(PermissionMixin, View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label='Undo', emoji='◀️', style=ButtonStyle.primary, custom_id='undo_whitelist')
    async def undo(self, interaction, btn):
        await try_whitelist(interaction, False)


class RejectedView(PermissionMixin, View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @button(label='Whitelist', emoji='📜', style=ButtonStyle.primary, custom_id=f'whitelist')
    async def callback(self, interaction: Interaction):
        await try_whitelist(interaction)


class FailView(View):
    def __init__(self, whitelisting: bool):
        super().__init__(timeout=None)
        self.whitelisting = whitelisting
        self.add_item(RetryButton(whitelisting))

class RetryButton(PermissionMixin, DynamicItem, template=r'retry:(?P<value>True|False)'):
    def __init__(self, whitelisting: bool):
        self.whitelisting = whitelisting

        super().__init__(
            Button(
                label='Retry',
                emoji='🔄',
                custom_id=f'retry:{whitelisting}',
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: Interaction, item: Button, match: re.Match[str]):
        return cls(match['value'] == 'True')

    async def callback(self, interaction: Interaction):
        await try_whitelist(interaction, self.whitelisting)


async def update_post(post: Message, view: SuccessView | RejectedView | FailView, user: User = None):
    embed = post.embeds[0].copy()

    match view:
        case SuccessView():
            embed.description = 'Whitelisted ' + emoji.pinkie_affirm
        case RejectedView():
            embed.description = 'Not whitelisted'
        case FailView():
            embed.description = ('Failed to whitelist ' if view.whitelisting else 'Failed to undo whitelist ') + emoji.pinkie_PANIC_AHHH_WTF

    if user is not None:
        embed.description += f'\nBy {user.mention}'

    await post.edit(embed=embed, view=view)


async def get_post(video_key):
    """Get the Message object using its id if it exists, or None if it was not found"""
    post_id = whitelist_schedule.get(video_key, {}).get('post_id')

    if post_id is None:
        return

    try:
        return await output_channel.fetch_message(post_id)
    except NotFound:
        return


async def delay_whitelist(video_key, link, timeout):
    await asyncio.sleep(timeout)
    post = await get_post(video_key)

    if not post:
        del whitelist_schedule[video_key]
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
    existing_entry = whitelist_schedule.get(video_key)

    if existing_entry is not None:
        if existing_entry == 'pending':
            return # post is already about to be made

        post = await get_post(video_key)

        if post:
            return # already scheduled and post still exists

        # Cancel the previous task since the post for it was deleted or not found
        if existing_entry['task'] is not None:
            existing_entry['task'].cancel()

    whitelist_schedule[video_key] = 'pending'

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
        value='\n'.join(f'- {ann['trigger']}' for ann in video_data['annotations']) or '- No issues found'
    ).set_footer(
        text=f'By {video_data['uploader']} on {video_data['platform']}'
    )


    post = await output_channel.send(embed=embed, view=MainView(video_key))

    whitelist_schedule[video_key] = {
        'link': video_data['link'],
        'post_id': post.id,
        'task': asyncio.create_task(delay_whitelist(video_key, video_data['link'], timeout)),
        'timestamp': whitelist_timestamp
    }


def unschedule_whitelist(video_key):
    entry = whitelist_schedule.get(video_key)

    if entry and entry != 'pending' and entry['task'] is not None:
        entry['task'].cancel()
        entry['task'] = None


def load_schedule_cache():
    global whitelist_schedule

    if schedule_cache_path.exists():
        with open(schedule_cache_path, 'r', encoding='utf8') as file:
            cache = json.load(file)

        cache = [[tuple(entry['key']), entry['link'], entry['post_id'], entry['timestamp']] for entry in cache]

        for key, link, post_id, timestamp in cache:
            remaing_time = timestamp - int(time.time())

            if remaing_time < -60 * 60 * 24 * 32: # Just over 1 month
                continue # Stop keeping track of old posts

            # TODO: update post when remaining_time < 0

            whitelist_schedule[key] = {
                'link': link,
                'post_id': post_id,
                'task': None if remaing_time < 0 else asyncio.create_task(delay_whitelist(key, link, remaing_time)),
                'timestamp': timestamp
            }


def save_schedule_cache():
    with open(schedule_cache_path, 'w', encoding='utf8') as file:
        json.dump(
            [
                { 'key': key, 'link': entry['link'], 'post_id': entry['post_id'], 'timestamp': entry['timestamp'] }
                for key, entry in whitelist_schedule.items()
                if entry != 'pending'
            ],
            file
        )

def set_output_channel(channel):
    global output_channel
    output_channel = channel
