import discord
from discord.ext import commands
from discord import app_commands
from utils.api import ERLC_API, get_erlc_error_message
from utils.roblox import get_roblox_usernames
from utils.emojis import clipboard_emoji, owner_emoji

api = ERLC_API()  # Use the central async API class


class InfoView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, embed_callback):
        super().__init__(timeout=180)
        self.interaction = interaction
        self.embed_callback = embed_callback

        self.add_item(discord.ui.Button(
            label="🔗 Join Server",
            style=discord.ButtonStyle.link,
            url="https://policeroleplay.community/join?code=SWATxRP&placeId=2534724415"
        ))

    @discord.ui.button(label="🔁 Refresh", style=discord.ButtonStyle.blurple)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("❌ You can't use this button.", ephemeral=True)
            return

        embed = await self.embed_callback()
        await interaction.response.edit_message(embed=embed)


async def create_server_info_embed(interaction: discord.Interaction) -> discord.Embed:
    try:
        server = await api.get_server_status()
        players = await api.get_players_in_server()
        queue = await api.get_players_in_queue()
    except Exception as e:
        raise Exception(f"Failed to fetch ERLC API data: {e}")

    if "error" in server:
        raise Exception(server["error"])

    owner_id = server.get("OwnerId")
    co_owner_ids = server.get("CoOwnerIds", [])
    usernames = await get_roblox_usernames([owner_id] + co_owner_ids)

    mods = [p for p in players if p.get("Permission") == "Server Moderator"]
    admins = [p for p in players if p.get("Permission") == "Server Administrator"]
    staff = [p for p in players if p.get("Permission") != "Normal"]

    embed = discord.Embed(
        title=f"{server.get('Name', 'ERLC Server')} - Server Info",
        color=discord.Color.blue()
    )
    embed.add_field(
        name=f"{clipboard_emoji} Basic Info",
        value=(
            f"> **Join Code:** [{server.get('JoinKey', 'N/A')}]"
            f"(https://policeroleplay.community/join/{server.get('JoinKey', '')})\n"
            f"> **Players:** {server.get('CurrentPlayers', 0)}/{server.get('MaxPlayers', 0)}\n"
            f"> **Queue:** {len(queue)}"
        ),
        inline=False
    )
    embed.add_field(
        name=f"{clipboard_emoji} Staff Info",
        value=(
            f"> **Moderators:** {len(mods)}\n"
            f"> **Administrators:** {len(admins)}\n"
            f"> **Staff in Server:** {len(staff)}"
        ),
        inline=False
    )
    embed.add_field(
        name=f"{owner_emoji} Server Ownership",
        value=(
            f"> **Owner:** [{usernames.get(owner_id, 'Unknown')}]"
            f"(https://roblox.com/users/{owner_id}/profile)\n"
            f"> **Co-Owners:** {', '.join([f'[{usernames.get(uid, 'Unknown')}]'"
            f"(https://roblox.com/users/{uid}/profile)" for uid in co_owner_ids]) or 'None'}"
        ),
        inline=False
    )

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    return embed


class ERLCInfo(commands.Cog):
    """ERLC Info commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="info", description="Get ER:LC server info with live data.")
    async def erlc_info(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            embed = await create_server_info_embed(interaction)
            view = InfoView(interaction, lambda: create_server_info_embed(interaction))
            await interaction.followup.send(embed=embed, view=view)
        except Exception as e:
            error_message = get_erlc_error_message(0)
            await interaction.followup.send(f"{error_message}\n`{str(e)}`")
            print(f"[ERROR] /erlc info failed: {e}")

    async def cog_load(self):
        erlc_group = self.bot.tree.get_command("erlc")
        if erlc_group:
            erlc_group.add_command(self.erlc_info)


async def setup(bot: commands.Bot):
    await bot.add_cog(ERLCInfo(bot))
