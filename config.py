import dotenv, os

dotenv.load_dotenv()

bot_token = os.getenv('TOKEN')
server_api_url = os.getenv('API_ENDPOINT')
server_auth_key = os.getenv('SERVER_AUTH_KEY')
output_channel_id = int(os.getenv('OUTPUT_CHANNEL_ID'))
target_guild_id = int(os.getenv('GUILD_ID'))
