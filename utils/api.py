import aiohttp
from dotenv import load_dotenv

load_dotenv()  # make sure this is at the top

API_KEY = os.getenv("API_KEY")
API_BASE = os.getenv("API_BASE")



def get_erlc_error_message(status: int) -> str:
    """Return a human-readable error message from ER:LC API status codes"""
    if status == 401:
        return "Unauthorized: Invalid API key."
    elif status == 403:
        return "Forbidden: You don't have access to this server's data."
    elif status == 404:
        return "Not Found: This server doesn't exist or isn't available."
    elif status == 500:
        return "Internal Server Error: ER:LC API is having issues."
    return f"Unexpected error (status {status})."


class ERLC_API:
    def __init__(self):
        self.base = API_BASE
        self.headers = HEADERS

    async def _fetch(self, endpoint: str):
        """Internal request handler"""
        url = f"{self.base}{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as resp:
                if resp.status != 200:
                    return {"error": get_erlc_error_message(resp.status), "status": resp.status}
                return await resp.json()

    async def get_server_status(self):
        return await self._fetch("/server")

    async def get_players_in_server(self):
        return await self._fetch("/server/players")

    async def get_players_in_queue(self):
        return await self._fetch("/server/queue")

    async def get_bans(self):
        return await self._fetch("/server/bans")

    async def run_command(self, command: str):
        url = f"{self.base}/server/command"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json={"command": command}) as resp:
                if resp.status != 200:
                    return {"error": get_erlc_error_message(resp.status), "status": resp.status}
                return await resp.json()
