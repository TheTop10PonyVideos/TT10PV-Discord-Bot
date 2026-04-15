import aiohttp

session = None

async def create_session():
    global session
    session = aiohttp.ClientSession()
