import dotenv, os, pathlib

dotenv.load_dotenv()

bot_token = os.getenv('TOKEN')
server_api_url = os.getenv('API_ENDPOINT')
server_auth_key = os.getenv('SERVER_AUTH_KEY')
output_channel_id = int(os.getenv('OUTPUT_CHANNEL_ID'))
target_guild_id = int(os.getenv('GUILD_ID'))
ignore_channels = [int(channel_id) for channel_id in os.getenv('IGNORE_CHANNELS').split(',')]
schedule_cache_path = pathlib.Path('schedule_cache.json')

class Roles:
    MODERATOR = 749754741399224422
    SERIES_STAFF = 749330617505939547
