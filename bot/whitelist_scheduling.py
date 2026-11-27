from app_types import WLScheduleEntry
from bot import emoji as bot_emoji
from bot.permissions import PermissionMixin, RoleLevel
from config import schedule_cache_path
from server_actions.annotations import whitelist, set_eligibility, set_reupload
from discord.ui import Button, DynamicItem
from discord import (
    ButtonStyle,
    Color,
    Interaction,
    MediaGalleryItem,
    Message,
    NotFound,
    SelectOption,
    TextChannel,
    TextStyle,
    User
)
from discord.ui import (
    Container,
    LayoutView,
    TextDisplay,
)
from typing import Literal
import bot.component_ids as cid
import discord.ui as ui
import asyncio, time, json, re, emoji


whitelist_schedule: dict[tuple, WLScheduleEntry | Literal['pending']] = {}

output_channel: TextChannel = None

with open('rules.json') as file:
    rules = json.load(file)


async def try_whitelist(interaction: Interaction, value=True):
    """Attempt to set a searchable value for a video via button interaction, and update its post accordingly"""
    post = MainView.from_message(interaction.message)
    failed = False

    try:
        await whitelist(post.get_video_link(), value)

    except Exception as e:
        print(e)
        failed = True

    await MainView.from_message(interaction.message) \
        .whitelist_update(
            value,
            interaction.user,
            failed=failed
        ).send_edit()


class MainView(LayoutView):
    def __init__(self, video_data, whitelist_timestamp):
        super().__init__()
        video_key = get_video_key(video_data)

        # eligible first since that only comes from manual checks
        priority = ['eligible', 'ineligible', 'maybe ineligible']
    
        for t in priority:
            if any(ann['type'] == t for ann in video_data['annotations']):
                eligibility = t
                break
        else:
            eligibility = 'eligible'

        title = emoji.replace_emoji(video_data['title'], ' ')

        title = TextDisplay(
            f'### [{title}]({video_data['link']})',
            id=cid.TITLE
        )

        wl_status = TextDisplay(
            f'Whitelisting <t:{whitelist_timestamp}:R>',
            id=cid.WL_STATUS
        )

        annotations = TextDisplay(
            f'### {eligibility.title()}\n{
                '\n'.join(f'- {ann['trigger']}'
                for ann in video_data['annotations'])
                or '- No issues found'
            }',
            id=cid.ANNOTATIONS
        )

        container = Container(
            title,
            wl_status,
            annotations,

            ui.MediaGallery(MediaGalleryItem(media=video_data['thumbnail'])),

            TextDisplay(f'By {video_data['creator']['channel_name']} on {video_data['platform']}'),

            ui.ActionRow(
                WhitelistButton(),
                RejectButton(),
                ReuploadButton(),
                id=cid.BUTTONS
            ),
            ui.ActionRow(EligibilitySelect(video_key)),

            accent_colour=Color.blurple()
        )

        self.add_item(container)


    @classmethod
    def from_message(cls, message: Message):
        view = super().from_message(message)

        self = cls.__new__(cls)
        LayoutView.__init__(self)

        for item in view.children:
            self.add_item(item)

        self.message = message
        return self

    def whitelist_update(self, whitelisting: bool, user: User = None, *, failed=False):
        wl_status: TextDisplay = self.find_item(cid.WL_STATUS)
        buttons: ui.ActionRow = self.find_item(cid.BUTTONS)
        buttons.clear_items()

        if failed:
            wl_status.content = ('Failed to whitelist ' if whitelisting else 'Failed to undo whitelist ') + bot_emoji.pinkie_PANIC_AHHH_WTF
            buttons.add_item(RetryButton(whitelisting))

        elif whitelisting:
            wl_status.content = 'Whitelisted ' + bot_emoji.pinkie_affirm
            buttons.add_item(UndoWhitelistButton())

        else:
            wl_status.content = 'Not whitelisted'
            buttons.add_item(WhitelistButton())

        buttons.add_item(ReuploadButton())

        if user is not None:
            wl_status.content += f'\nBy {user.mention}'

        return self

    def eligibility_update(self, judgement, reason: str = None):
        annotations: TextDisplay = self.find_item(cid.ANNOTATIONS)
        annotations.content = (
            f'### {judgement.title()}\n'
            f'- {reason or 'Manually Checked'}'
        )

        return self

    def reupload_update(self, orig_title, orig_uploader):
        return self

    def get_video_link(self) -> str:
        title = self.find_item(cid.TITLE).content
        return title[title.rfind('](') + 2 : -1]

    async def send_edit(self):
        await self.message.edit(view=self)


class WhitelistButton(
    PermissionMixin,
    DynamicItem,
    permitted=RoleLevel.SERIES_STAFF,
    template=r'whitelist'
):
    def __init__(self):
        super().__init__(
            Button(
                label='Whitelist',
                emoji='📜',
                style=ButtonStyle.primary,
                custom_id=f'whitelist',
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls()

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()

        video_key = get_bearer_key(self.view)
        unschedule_whitelist(video_key)

        await try_whitelist(interaction)

class RejectButton(
    PermissionMixin,
    DynamicItem,
    permitted=RoleLevel.SERIES_STAFF,
    template=r'reject'
):
    def __init__(self):
        super().__init__(
            Button(
                label='Reject',
                emoji='❌',
                style=ButtonStyle.primary,
                custom_id=f'reject',
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls()

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()

        video_key = get_bearer_key(self.view)
        unschedule_whitelist(video_key)

        await try_whitelist(interaction, False)

class UndoWhitelistButton(
    PermissionMixin,
    DynamicItem,
    permitted=RoleLevel.SERIES_STAFF,
    template='undo'
):
    def __init__(self):
        super().__init__(
            Button(
                label='Undo',
                emoji='◀️',
                style=ButtonStyle.primary,
                custom_id='undo',
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls()

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        await try_whitelist(interaction, False)

class RetryButton(
    PermissionMixin,
    DynamicItem,
    permitted=RoleLevel.SERIES_STAFF,
    template=r'retry:(?P<value>True|False)'
):
    def __init__(self, whitelisting: bool):
        self.whitelisting = whitelisting

        super().__init__(
            Button(
                label='Retry',
                emoji='🔄',
                custom_id=f'retry:{whitelisting}'
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match: re.Match[str]):
        return cls(match['value'] == 'True')

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        await try_whitelist(interaction, self.whitelisting)

class ReuploadButton(
    PermissionMixin,
    DynamicItem,
    permitted=RoleLevel.SERIES_STAFF,
    template='set_reupload'
):
    def __init__(self):
        super().__init__(
            Button(
                label='Reupload',
                emoji='🔗',
                custom_id=f'set_reupload',
                style=ButtonStyle.primary,
                disabled=True # TODO
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls()

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(SetReuploadModal())


class EligibilitySelect(
    PermissionMixin,
    DynamicItem,
    template=r'eligibility:.+'
):
    def __init__(self, video_key):
        select = ui.Select(
            id=cid.KEY_BEARER,
            custom_id=f'eligibility:{':'.join(video_key)}',
            placeholder='Set Eligibility...',
            options=(
                [SelectOption(label='Eligible')] +
                [
                    SelectOption(
                        label=rule['label'],
                        description=rule['description'],
                    )
                    for rule in rules
                ] +
                [SelectOption(label='Other')]
            )
        )

        super().__init__(select)

    @classmethod
    async def from_custom_id(cls, interaction, item: ui.Select, match):
        return cls(item.custom_id.split(':')[1:])

    async def callback(self, interaction: Interaction):
        selection = self.item.values[0]
        eligible = selection == 'Eligible'

        prompt = (
            'Why is this video ineligible?'
            if selection == 'Other'
            else
            'Why is this video eligible? (Optional)'
            if eligible
            else None
        )

        if prompt is not None:
            return await interaction.response.send_modal(ManualAnnotationModal(prompt, eligible))

        await interaction.response.defer()

        reason = next(rule for rule in rules if rule['label'] == selection)['full']
        await do_eligibility_update(interaction, eligible, selection, reason)

class ManualAnnotationModal(ui.Modal, title='Manual Annotation'):
    def __init__(self, prompt, eligible):
        super().__init__()
        self.eligible = eligible
        self.reason = ui.Label(
            text=prompt,
            component=ui.TextInput(
                style=TextStyle.paragraph,
                required=not eligible
            )
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer()

        reason = self.reason.component.value.strip()
        label = reason if len(reason) < 37 else (reason[:37] + '...')
        await do_eligibility_update(interaction, self.eligible, label or 'Manually checked', reason)

async def do_eligibility_update(interaction: Interaction, eligible: bool, label, reason):
    post = MainView.from_message(interaction.message)
    url = post.get_video_link()

    if post.find_item(cid.WL_STATUS).content.startswith('Whitelisting'):
        key = get_bearer_key(post)
        unschedule_whitelist(key)

        try:
            await whitelist(url, eligible)
        except Exception as e:
            print(e)
            return await post.whitelist_update(eligible, interaction.user, failed=True).send_edit()

        post.whitelist_update(eligible, interaction.user)

    try:
        await set_eligibility(post.get_video_link(), 'eligible' if eligible else 'ineligible', reason)
    except Exception as e:
        print(e)
        await post.send_edit()
        await interaction.followup.send('Soz. An error occured ;-;', ephemeral=True)
        return
    
    await post.eligibility_update('eligible' if eligible else 'ineligible', label).send_edit()


class SetReuploadModal(ui.Modal, title='Set Reupload'):
    original_link = ui.Label(text='Enter the link that this video is a reupload of', component=ui.TextInput(style=TextStyle.short))

    async def on_submit(self, interaction: Interaction):
        post = MainView.from_interaction(interaction)
        try:
            await set_reupload(post.get_video_link(), self.original_link.component.value)
        except Exception as e:
            print(e)
            await interaction.response.send_message('Soz. An error occured ;-;', ephemeral=True)

        await post.reupload_update().send_edit()


async def find_post(video_key):
    """Get the Message object using its id if it exists, or None if it was not found"""
    post_id = whitelist_schedule.get(video_key, {}).get('post_id')

    if post_id is None:
        return

    try:
        return MainView.from_message(await output_channel.fetch_message(post_id))
    except NotFound:
        return


async def delay_whitelist(video_key, link, timeout):
    await asyncio.sleep(timeout)
    post = await find_post(video_key)

    if not post:
        del whitelist_schedule[video_key]
        return

    failed = False
    try:
        await whitelist(link)
    except Exception as e:
        print(e)
        failed = True

    await post.whitelist_update(True, failed=failed).send_edit()


async def schedule_whitelist(video_data, timeout = 60 * 60 * 12):
    video_key = get_video_key(video_data)
    existing_entry = whitelist_schedule.get(video_key)

    if existing_entry is not None:
        if existing_entry == 'pending':
            return # post is already about to be made

        post = await find_post(video_key)

        if post:
            return # already scheduled and post still exists

        # Cancel the previous task since the post for it was deleted or not found
        if existing_entry['task'] is not None:
            existing_entry['task'].cancel()

    whitelist_schedule[video_key] = 'pending'

    whitelist_timestamp = int(time.time()) + timeout

    post = await output_channel.send(view=MainView(video_data, whitelist_timestamp))

    whitelist_schedule[video_key] = {
        'link': video_data['link'],
        'post_id': post.id,
        'task': asyncio.create_task(delay_whitelist(video_key, video_data['link'], timeout)),
        'timestamp': whitelist_timestamp
    }


def get_video_key(video_data):
    return video_data['platform'], video_data['video_id']

def get_bearer_key(post: LayoutView):
    bearer: ui.Select = post.find_item(cid.KEY_BEARER)
    _, platform, vid_id = bearer.custom_id.split(':')

    return platform, vid_id


def unschedule_whitelist(video_key):
    entry = whitelist_schedule.get(video_key)

    if entry and entry != 'pending' and entry['task'] is not None:
        entry['task'].cancel()
        entry['task'] = None
        entry['timestamp'] = None


def load_schedule_cache():
    global whitelist_schedule

    if schedule_cache_path.exists():
        with open(schedule_cache_path, 'r', encoding='utf8') as file:
            cache = json.load(file)

        cache = [[tuple(entry['key']), entry['link'], entry['post_id'], entry['timestamp']] for entry in cache]

        for key, link, post_id, timestamp in cache:
            remaining_time = None

            if timestamp is not None:
                remaining_time = timestamp - int(time.time())

                if remaining_time < -60 * 60 * 24 * 32: # Just over 1 month
                    continue # Stop keeping track of old posts

            # TODO: update post when remaining_time < 0

            whitelist_schedule[key] = {
                'link': link,
                'post_id': post_id,
                'task': None if remaining_time is None or remaining_time < 0 else asyncio.create_task(delay_whitelist(key, link, remaining_time)),
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
