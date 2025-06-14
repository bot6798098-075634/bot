import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from discord.utils import get
from datetime import timedelta

MOD_ROLE_ID = 1343234687505530902  # Required role ID to run commands

def create_embed(title, desc, color=discord.Color.blurple()):
    return discord.Embed(title=title, description=desc, color=color)

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def has_mod_role(self, member: discord.Member) -> bool:
        return any(role.id == MOD_ROLE_ID for role in member.roles)

    @app_commands.command(name="kick", description="Kick a user from the server")
    @app_commands.describe(member="The member to kick", reason="Reason for kicking")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if not self.has_mod_role(interaction.user):
            return await interaction.response.send_message(embed=create_embed("Error", "You need the moderator role to use this command.", discord.Color.red()), ephemeral=True)

        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message(embed=create_embed("Error", "You don't have permission to kick members.", discord.Color.red()), ephemeral=True)

        await member.kick(reason=reason)
        await interaction.response.send_message(embed=create_embed("User Kicked", f"{member.mention} was kicked.\nReason: {reason}"))

    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(member="The member to ban", reason="Reason for banning")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if not self.has_mod_role(interaction.user):
            return await interaction.response.send_message(embed=create_embed("Error", "You need the moderator role to use this command.", discord.Color.red()), ephemeral=True)

        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message(embed=create_embed("Error", "You don't have permission to ban members.", discord.Color.red()), ephemeral=True)

        await member.ban(reason=reason)
        await interaction.response.send_message(embed=create_embed("User Banned", f"{member.mention} was banned.\nReason: {reason}"))

    @app_commands.command(name="mute", description="Mute a user for a set number of minutes")
    @app_commands.describe(member="Member to mute", duration="Duration in minutes")
    async def mute(self, interaction: discord.Interaction, member: discord.Member, duration: int = 10):
        if not self.has_mod_role(interaction.user):
            return await interaction.response.send_message(embed=create_embed("Error", "You need the moderator role to use this command.", discord.Color.red()), ephemeral=True)

        if member.id == 1276264248095412387:  # Protect specific user from mute
            return await interaction.response.send_message(embed=create_embed("Error", "You cannot mute this user.", discord.Color.red()), ephemeral=True)

        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(embed=create_embed("Error", "You don't have permission to manage roles.", discord.Color.red()), ephemeral=True)

        muted_role = get(interaction.guild.roles, name="Muted")
        if not muted_role:
            muted_role = await interaction.guild.create_role(name="Muted")
            for channel in interaction.guild.channels:
                await channel.set_permissions(muted_role, send_messages=False, speak=False)

        await member.add_roles(muted_role)
        await interaction.response.send_message(embed=create_embed("User Muted", f"{member.mention} has been muted for {duration} minutes."))

        # Wait asynchronously for duration and unmute
        await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(minutes=duration))
        await member.remove_roles(muted_role)

    @app_commands.command(name="unmute", description="Unmute a user")
    @app_commands.describe(member="Member to unmute")
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        if not self.has_mod_role(interaction.user):
            return await interaction.response.send_message(embed=create_embed("Error", "You need the moderator role to use this command.", discord.Color.red()), ephemeral=True)

        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(embed=create_embed("Error", "You don't have permission to manage roles.", discord.Color.red()), ephemeral=True)

        muted_role = get(interaction.guild.roles, name="Muted")
        if muted_role and muted_role in member.roles:
            await member.remove_roles(muted_role)
            await interaction.response.send_message(embed=create_embed("User Unmuted", f"{member.mention} has been unmuted."))
        else:
            await interaction.response.send_message(embed=create_embed("Error", f"{member.mention} is not muted.", discord.Color.red()), ephemeral=True)

    @app_commands.command(name="unban", description="Unban a user by their ID")
    @app_commands.describe(user_id="The ID of the user to unban")
    async def unban(self, interaction: discord.Interaction, user_id: str):
        if not self.has_mod_role(interaction.user):
            return await interaction.response.send_message(embed=create_embed("Error", "You need the moderator role to use this command.", discord.Color.red()), ephemeral=True)

        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message(embed=create_embed("Error", "You don't have permission to unban members.", discord.Color.red()), ephemeral=True)

        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user)
            await interaction.response.send_message(embed=create_embed("User Unbanned", f"{user.mention} has been unbanned."))
        except discord.NotFound:
            await interaction.response.send_message(embed=create_embed("Error", "User not found in ban list.", discord.Color.red()), ephemeral=True)
        except ValueError:
            await interaction.response.send_message(embed=create_embed("Error", "Invalid user ID format.", discord.Color.red()), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(embed=create_embed("Error", f"Something went wrong.\n{e}", discord.Color.red()), ephemeral=True)

    @app_commands.command(name="clear", description="Clear a number of messages in the channel")
    @app_commands.describe(amount="How many messages to delete")
    async def clear(self, interaction: discord.Interaction, amount: int):
        if not self.has_mod_role(interaction.user):
            return await interaction.response.send_message(embed=create_embed("Error", "You need the moderator role to use this command.", discord.Color.red()), ephemeral=True)

        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(embed=create_embed("Error", "You don't have permission to manage messages.", discord.Color.red()), ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(embed=create_embed("Cleared Messages", f"Deleted {len(deleted)} messages."), ephemeral=True)

    @app_commands.command(name="unlock", description="Unlock the current channel for @everyone")
    async def unlock(self, interaction: discord.Interaction):
        if not self.has_mod_role(interaction.user):
            return await interaction.response.send_message(embed=create_embed("Error", "You need the moderator role to use this command.", discord.Color.red()), ephemeral=True)

        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message(embed=create_embed("Error", "You don't have permission to manage channels.", discord.Color.red()), ephemeral=True)

        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = True
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

        await interaction.response.send_message(embed=create_embed("Channel Unlocked", f"{interaction.channel.mention} is now unlocked."))

    @app_commands.command(name="lock", description="Lock the current channel from @everyone")
    async def lock(self, interaction: discord.Interaction):
        if not self.has_mod_role(interaction.user):
            return await interaction.response.send_message(embed=create_embed("Error", "You need the moderator role to use this command.", discord.Color.red()), ephemeral=True)

        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message(embed=create_embed("Error", "You don't have permission to manage channels.", discord.Color.red()), ephemeral=True)

        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

        await interaction.response.send_message(embed=create_embed("Channel Locked", f"{interaction.channel.mention} is now locked."))

    REPORT_CHANNEL_ID = 1358405704393822288  # replace with your actual mod channel ID

    @app_commands.command(name="report", description="Report a user to the moderators")
    @app_commands.describe(user="The user you want to report", reason="The reason for the report")
    async def report(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        embed = discord.Embed(
            title="🚨 New User Report",
            description=f"**Reporter:** {interaction.user.mention}\n**Reported User:** {user.mention}\n**Reason:** {reason}",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"User ID: {user.id} | Reported from: #{interaction.channel.name}")
        embed.timestamp = discord.utils.utcnow()

        # Send report to mod channel
        mod_channel = self.bot.get_channel(self.REPORT_CHANNEL_ID)
        if mod_channel:
            await mod_channel.send(embed=embed)
            await interaction.response.send_message(embed=create_embed("Report Submitted", "Your report has been sent to the moderators. Thank you."), ephemeral=True)
        else:
            await interaction.response.send_message(embed=create_embed("Error", "Could not find the report channel. Please contact staff.", discord.Color.red()), ephemeral=True)

    @app_commands.command(name="poll", description="Create a simple yes/no poll")
    @app_commands.describe(question="The poll question")
    async def poll(self, interaction: discord.Interaction, question: str):
        class PollView(View):
            def __init__(self):
                super().__init__(timeout=None)
                self.yes_votes = 0
                self.no_votes = 0

            @discord.ui.button(label="👍 Yes", style=discord.ButtonStyle.success)
            async def yes_button(self, interaction: discord.Interaction, button: Button):
                self.yes_votes += 1
                await interaction.response.send_message("Vote counted for **Yes**!", ephemeral=True)

            @discord.ui.button(label="👎 No", style=discord.ButtonStyle.danger)
            async def no_button(self, interaction: discord.Interaction, button: Button):
                self.no_votes += 1
                await interaction.response.send_message("Vote counted for **No**!", ephemeral=True)

        embed = create_embed("📊 New Poll", question)
        await interaction.response.send_message(embed=embed, view=PollView())

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
