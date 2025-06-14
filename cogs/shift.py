import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
import json

# Constants
STAFF_ROLE_ID = 1343234687505530902
LOA_ROLE_ID = 1343299322804043900
SUSPENDED_INFRACTION_TYPE = "suspended"

SHIFT_ROLE_ID = 1343299303459913761
BREAK_ROLE_ID = 1343299319939207208
SHIFT_LOG_CHANNEL_ID = 1381409066156425236

INFRACTION_FILE = "infractions.json"
SHIFT_DATA_FILE = "shift_data.json"


def create_embed(title, description, color=discord.Color.blue()):
    return discord.Embed(title=title, description=description, color=color)


def load_infractions():
    try:
        with open(INFRACTION_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_infractions(data):
    with open(INFRACTION_FILE, "w") as f:
        json.dump(data, f, indent=4)


def load_shift_data():
    try:
        with open(SHIFT_DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_shift_data(data):
    with open(SHIFT_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def format_seconds(seconds: float) -> str:
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}h {m}m {s}s"


class ShiftCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.infractions = load_infractions()
        self.shift_data = load_shift_data()

    def is_staff(self, member: discord.Member):
        return any(role.id == STAFF_ROLE_ID for role in member.roles)

    def has_loa_role(self, member: discord.Member):
        return any(role.id == LOA_ROLE_ID for role in member.roles)

    def is_suspended(self, user_id: str):
        user_infractions = self.infractions.get(user_id, [])
        for inf in user_infractions:
            if inf.get("type") == SUSPENDED_INFRACTION_TYPE:
                return True
        return False

    def save_infractions(self):
        save_infractions(self.infractions)

    def save_shift_data(self):
        save_shift_data(self.shift_data)

    @app_commands.command(name="infraction_add", description="Add an infraction to a user")
    @app_commands.describe(user="User to add infraction to", reason="Reason for the infraction", infraction_type="Type of infraction (optional)")
    async def infraction_add(self, interaction: discord.Interaction, user: discord.Member, reason: str, infraction_type: str = "general"):
        if not self.is_staff(interaction.user):
            await interaction.response.send_message(embed=create_embed("Permission Denied", "You must be staff to add infractions.", discord.Color.red()), ephemeral=True)
            return

        user_id = str(user.id)
        entry = {
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": infraction_type.lower()
        }
        self.infractions.setdefault(user_id, []).append(entry)
        self.save_infractions()

        await interaction.response.send_message(embed=create_embed(
            "Infraction Added",
            f"Infraction added to {user.mention}\nReason: {reason}\nType: {infraction_type}"
        ))

        # If suspended infraction added, forcibly end shift & break
        if infraction_type.lower() == SUSPENDED_INFRACTION_TYPE:
            if user_id in self.shift_data:
                shift_user = self.shift_data[user_id]
                now_ts = datetime.now(timezone.utc).timestamp()
                if shift_user.get("current_shift_start"):
                    worked = now_ts - shift_user["current_shift_start"]
                    shift_user["total_shift"] = shift_user.get("total_shift", 0) + worked
                    shift_user["current_shift_start"] = None
                    shift_user["shift_type"] = None
                if shift_user.get("current_break_start"):
                    brk = now_ts - shift_user["current_break_start"]
                    shift_user["total_break"] = shift_user.get("total_break", 0) + brk
                    shift_user["current_break_start"] = None
                self.save_shift_data()

                member = interaction.guild.get_member(int(user_id))
                if member:
                    try:
                        await member.remove_roles(interaction.guild.get_role(SHIFT_ROLE_ID), interaction.guild.get_role(BREAK_ROLE_ID))
                    except Exception:
                        pass

    @app_commands.command(name="infraction_view", description="View infractions for a user")
    @app_commands.describe(user="User to view infractions for")
    async def infraction_view(self, interaction: discord.Interaction, user: discord.Member):
        if not self.is_staff(interaction.user):
            await interaction.response.send_message(embed=create_embed("Permission Denied", "You must be staff to view infractions.", discord.Color.red()), ephemeral=True)
            return

        user_id = str(user.id)
        user_infractions = self.infractions.get(user_id, [])
        if not user_infractions:
            await interaction.response.send_message(embed=create_embed(f"No Infractions", f"{user.mention} has no infractions.", discord.Color.green()))
            return

        embed = discord.Embed(title=f"Infractions for {user}", color=discord.Color.orange())
        for i, inf in enumerate(user_infractions, start=1):
            ts = inf.get("timestamp")
            reason = inf.get("reason")
            typ = inf.get("type", "general")
            embed.add_field(name=f"#{i} [{typ}]", value=f"**Reason:** {reason}\n**Time:** {ts}", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shift_start", description="Start your shift with a shift type")
    @app_commands.describe(shift_type="Type of shift (e.g. day, night)")
    async def shift_start(self, interaction: discord.Interaction, shift_type: str):
        user = interaction.user
        user_id = str(user.id)

        if not self.is_staff(user):
            await interaction.response.send_message(embed=create_embed("Permission Denied", "Only staff can start shifts.", discord.Color.red()), ephemeral=True)
            return

        if self.has_loa_role(user):
            await interaction.response.send_message(embed=create_embed("LOA Active", "You are currently marked as LOA and cannot start a shift.", discord.Color.red()), ephemeral=True)
            return

        if self.is_suspended(user_id):
            await interaction.response.send_message(embed=create_embed("Suspended", "You have a suspension infraction and cannot start a shift.", discord.Color.red()), ephemeral=True)
            return

        user_shift = self.shift_data.setdefault(user_id, {
            "total_shift": 0,
            "total_break": 0,
            "current_shift_start": None,
            "current_break_start": None,
            "shift_type": None
        })

        if user_shift["current_shift_start"]:
            await interaction.response.send_message(embed=create_embed("Shift Already Started", "You are already on shift.", discord.Color.red()), ephemeral=True)
            return

        if user_shift["current_break_start"]:
            await interaction.response.send_message(embed=create_embed("On Break", "You cannot start a new shift while on a break. End your break first.", discord.Color.red()), ephemeral=True)
            return

        # Start shift
        user_shift["current_shift_start"] = datetime.now(timezone.utc).timestamp()
        user_shift["shift_type"] = shift_type.lower()
        self.save_shift_data()

        guild = interaction.guild
        shift_role = guild.get_role(SHIFT_ROLE_ID)
        break_role = guild.get_role(BREAK_ROLE_ID)
        member = guild.get_member(user.id)

        if break_role in member.roles:
            await member.remove_roles(break_role)
        if shift_role not in member.roles:
            await member.add_roles(shift_role)

        log_chan = guild.get_channel(SHIFT_LOG_CHANNEL_ID)
        if log_chan:
            embed = create_embed("Shift Started", f"{user.mention} started a **{shift_type}** shift.", discord.Color.green())
            await log_chan.send(embed=embed)

        await interaction.response.send_message(embed=create_embed("Shift Started", f"Your **{shift_type}** shift has started."), ephemeral=True)

    @app_commands.command(name="shift_end", description="End your current shift")
    async def shift_end(self, interaction: discord.Interaction):
        user = interaction.user
        user_id = str(user.id)

        if not self.is_staff(user):
            await interaction.response.send_message(embed=create_embed("Permission Denied", "Only staff can end shifts.", discord.Color.red()), ephemeral=True)
            return

        user_shift = self.shift_data.get(user_id)
        if not user_shift or not user_shift.get("current_shift_start"):
            await interaction.response.send_message(embed=create_embed("No Shift", "You are not currently on shift.", discord.Color.red()), ephemeral=True)
            return

        shift_start_ts = user_shift["current_shift_start"]
        shift_end_ts = datetime.now(timezone.utc).timestamp()
        worked = shift_end_ts - shift_start_ts
        user_shift["total_shift"] = user_shift.get("total_shift", 0) + worked
        user_shift["current_shift_start"] = None
        shift_type = user_shift.get("shift_type")
        user_shift["shift_type"] = None
        self.save_shift_data()

        guild = interaction.guild
        shift_role = guild.get_role(SHIFT_ROLE_ID)
        break_role = guild.get_role(BREAK_ROLE_ID)
        member = guild.get_member(user.id)

        roles_to_remove = []
        if shift_role in member.roles:
            roles_to_remove.append(shift_role)
        if break_role in member.roles:
            roles_to_remove.append(break_role)
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)

        log_chan = guild.get_channel(SHIFT_LOG_CHANNEL_ID)
        if log_chan:
            embed = create_embed(
                "Shift Ended",
                f"{user.mention} ended their shift.\nShift Type: **{shift_type or 'Unknown'}**\nDuration: {format_seconds(worked)}",
                discord.Color.orange()
            )
            await log_chan.send(embed=embed)

        await interaction.response.send_message(embed=create_embed("Shift Ended", f"Your shift has ended. Duration: {format_seconds(worked)}"), ephemeral=True)

    @app_commands.command(name="break_start", description="Start your break")
    async def break_start(self, interaction: discord.Interaction):
        user = interaction.user
        user_id = str(user.id)

        if not self.is_staff(user):
            await interaction.response.send_message(embed=create_embed("Permission Denied", "Only staff can start breaks.", discord.Color.red()), ephemeral=True)
            return

        if self.has_loa_role(user):
            await interaction.response.send_message(embed=create_embed("LOA Active", "You are currently marked as LOA and cannot start a break.", discord.Color.red()), ephemeral=True)
            return

        if self.is_suspended(user_id):
            await interaction.response.send_message(embed=create_embed("Suspended", "You have a suspension infraction and cannot start a break.", discord.Color.red()), ephemeral=True)
            return

        user_shift = self.shift_data.get(user_id)
        if not user_shift or not user_shift.get("current_shift_start"):
            await interaction.response.send_message(embed=create_embed("Not On Shift", "You must be on shift to start a break.", discord.Color.red()), ephemeral=True)
            return

        if user_shift.get("current_break_start"):
            await interaction.response.send_message(embed=create_embed("Already On Break", "You are already on a break.", discord.Color.red()), ephemeral=True)
            return

        user_shift["current_break_start"] = datetime.now(timezone.utc).timestamp()
        self.save_shift_data()

        guild = interaction.guild
        shift_role = guild.get_role(SHIFT_ROLE_ID)
        break_role = guild.get_role(BREAK_ROLE_ID)
        member = guild.get_member(user.id)

        if shift_role in member.roles:
            await member.remove_roles(shift_role)
        if break_role not in member.roles:
            await member.add_roles(break_role)

        log_chan = guild.get_channel(SHIFT_LOG_CHANNEL_ID)
        if log_chan:
            embed = create_embed("Break Started", f"{user.mention} started a break.", discord.Color.gold())
            await log_chan.send(embed=embed)

        await interaction.response.send_message(embed=create_embed("Break Started", "You have started your break."), ephemeral=True)

    @app_commands.command(name="break_end", description="End your break and return to shift")
    async def break_end(self, interaction: discord.Interaction):
        user = interaction.user
        user_id = str(user.id)

        if not self.is_staff(user):
            await interaction.response.send_message(embed=create_embed("Permission Denied", "Only staff can end breaks.", discord.Color.red()), ephemeral=True)
            return

        if self.has_loa_role(user):
            await interaction.response.send_message(embed=create_embed("LOA Active", "You are currently marked as LOA and cannot end a break.", discord.Color.red()), ephemeral=True)
            return

        if self.is_suspended(user_id):
            await interaction.response.send_message(embed=create_embed("Suspended", "You have a suspension infraction and cannot end a break.", discord.Color.red()), ephemeral=True)
            return

        user_shift = self.shift_data.get(user_id)
        if not user_shift or not user_shift.get("current_break_start"):
            await interaction.response.send_message(embed=create_embed("Not On Break", "You are not currently on a break.", discord.Color.red()), ephemeral=True)
            return

        break_start_ts = user_shift["current_break_start"]
        break_end_ts = datetime.now(timezone.utc).timestamp()
        brk = break_end_ts - break_start_ts
        user_shift["total_break"] = user_shift.get("total_break", 0) + brk
        user_shift["current_break_start"] = None
        self.save_shift_data()

        guild = interaction.guild
        shift_role = guild.get_role(SHIFT_ROLE_ID)
        break_role = guild.get_role(BREAK_ROLE_ID)
        member = guild.get_member(user.id)

        if break_role in member.roles:
            await member.remove_roles(break_role)
        if shift_role not in member.roles:
            await member.add_roles(shift_role)

        log_chan = guild.get_channel(SHIFT_LOG_CHANNEL_ID)
        if log_chan:
            embed = create_embed("Break Ended", f"{user.mention} ended their break.", discord.Color.green())
            await log_chan.send(embed=embed)

        await interaction.response.send_message(embed=create_embed("Break Ended", f"Your break has ended after {format_seconds(brk)}."), ephemeral=True)

    @app_commands.command(name="shift_leaderboard", description="View leaderboard for total shift and break times")
    async def shift_leaderboard(self, interaction: discord.Interaction):
        if not self.shift_data:
            await interaction.response.send_message(embed=create_embed("No Data", "No shift data available.", discord.Color.red()), ephemeral=True)
            return

        leaderboard = []
        for uid, data in self.shift_data.items():
            total_shift = data.get("total_shift", 0)
            total_break = data.get("total_break", 0)
            leaderboard.append((uid, total_shift, total_break))
        leaderboard.sort(key=lambda x: x[1], reverse=True)

        embed = discord.Embed(title="Shift Leaderboard", color=discord.Color.purple())
        top = leaderboard[:10]
        for rank, (uid, shift_sec, break_sec) in enumerate(top, start=1):
            member = interaction.guild.get_member(int(uid))
            name = member.display_name if member else f"User ID {uid}"
            embed.add_field(
                name=f"{rank}. {name}",
                value=f"Shift Time: {format_seconds(shift_sec)}\nBreak Time: {format_seconds(break_sec)}",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ShiftCog(bot))
