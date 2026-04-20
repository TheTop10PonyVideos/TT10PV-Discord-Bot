from discord.ext import commands
from discord import Message
from server_actions.annotations import get_video_data
from config import target_guild_id
from bot.whitelist_scheduling import schedule_whitelist
import re, asyncio


platform_check = re.compile(r'https?://(?:[\w-]+\.)?(?:pony\.tube|youtube\.com|youtu\.be|bilibili\.com|b23\.tv|vimeo\.com|thishorsie\.rocks|dailymotion\.com|dai\.ly|tiktok\.com|twitter\.com|x\.com|odysee\.com|newgrounds\.com|bsky\.app|derpibooru\.org|instagram\.com)(?:/[^\s]{0,500}(?=\s|$))')


class MessageListener(commands.Cog):
    @commands.Cog.listener()
    async def on_message(self, msg: Message):
        if msg.author.bot or msg.guild is None or msg.guild.id != target_guild_id:
            return

        links = re.findall(platform_check, msg.content)[:3]
        
        results = await asyncio.gather(
            *[get_video_data(link) for link in links],
            return_exceptions=True
        )

        result_data = [
            result for result in results
            if not isinstance(result, Exception)
        ]

        for video_data in result_data:
            if video_data['whitelisted'] or not video_data['recent']:
                continue # already whitelisted or too old
            
            seconds_12hr_timeout = 60 * 60 * 12
            await schedule_whitelist(video_data, seconds_12hr_timeout)


async def setup(bot):
    await bot.add_cog(MessageListener(bot))
