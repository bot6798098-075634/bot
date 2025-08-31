import aiohttp

async def get_roblox_usernames(user_ids: list[int]) -> dict[int, str]:
    """
    Given a list of Roblox user IDs, return a dict mapping {id: username}.
    """
    usernames = {}
    async with aiohttp.ClientSession() as session:
        for user_id in user_ids:
            try:
                async with session.get(f"https://users.roblox.com/v1/users/{user_id}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        usernames[user_id] = data.get("name", "Unknown")
                    else:
                        usernames[user_id] = "Unknown"
            except:
                usernames[user_id] = "Unknown"
    return usernames
