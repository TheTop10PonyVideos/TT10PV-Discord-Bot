import dotenv, os

dotenv.load_dotenv()

bot_token = os.getenv('TOKEN')
server_api_url = os.getenv('API_ENDPOINT')
server_auth_key = os.getenv('SERVER_AUTH_KEY')
