import discord
from discord.ext import commands
from discord import app_commands

from datetime import timedelta

SESSION_VOTE_PING_ROLE_ID = 1375985192174354442
SESSION_ROLE_ID = 1375985192174354442
TARGET_CHANNEL_ID = 1373707060977340456
REQUIRED_VOTES = 2
JOIN_LINK = "https://policeroleplay.community/join?code=SWATxRP&placeId=2534724415"

class SessionView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.message = None
        self.current_votes = set()
        self.session_state = "idle"

        # Buttons
        self.vote_button = discord.ui.Button(label="Vote", style=discord.ButtonStyle.primary)
        self.vote_button.callback = self.vote_callback

        self.start_button = discord.ui.Button(label="Start Session", style=discord.ButtonStyle.success)
        self.start_button.callback = self.start_session

        self.shutdown_button = discord.ui.Button(label="Shutdown Session", style=discord.ButtonStyle.danger)
        self.shutdown_button.callback = self.shutdown_session

        self.low_button = discord.ui.Button(label="Low Session", style=discord.ButtonStyle.secondary)
        self.low_button.callback = self.set_low_session

        self.full_button = discord.ui.Button(label="Full Session", style=discord.ButtonStyle.secondary)
        self.full_button.callback = self.set_full_session

        self.start_vote_button = discord.ui.Button(label="Start Vote", style=discord.ButtonStyle.primary)
        self.start_vote_button.callback = self.reset_vote

        self.reset_buttons_to_vote()

    def reset_buttons_to_vote(self):
        self.clear_items()
        self.add_item(self.vote_button)
        self.add_item(self.start_button)
        self.add_item(self.shutdown_button)

    def set_buttons_to_session(self):
        self.clear_items()
        self.add_item(self.low_button)
        self.add_item(self.full_button)
        self.add_item(self.shutdown_button)

    def set_buttons_to_idle(self):
        self.clear_items()
        self.add_item(self.start_vote_button)
        self.add_item(self.start_button)

    async def vote_callback(self, interaction: discord.Interaction):
        member = interaction.user
        if member.id in self.current_votes:
            self.current_votes.remove(member.id)
        else:
            self.current_votes.add(member.id)

        vote_count = len(self.current_votes)
        embed = discord.Embed(title="Session Voting", description=f"**{vote_count} of {REQUIRED_VOTES} votes**", color=discord.Color.blurple())
        await self.message.edit(embed=embed, view=self)

        if vote_count >= REQUIRED_VOTES:
            self.remove_item(self.vote_button)
            embed.description = "✅ **Vote complete. Ready to start the session.**"
            await self.message.edit(embed=embed, view=self)

            for user_id in self.current_votes:
                user = await self.bot.fetch_user(user_id)
                try:
                    join_view = discord.ui.View()
                    join_view.add_item(discord.ui.Button(label="Join", url=JOIN_LINK))
                    dm_embed = discord.Embed(title="Session Invite", description="**Code: SWATxRP**\n**Owner: misnew12**", color=discord.Color.green())
                    await user.send(embed=dm_embed, view=join_view)
                except discord.Forbidden:
                    print(f"Could not DM {user_id}")

        await interaction.response.defer()

    async def start_session(self, interaction: discord.Interaction):
        if not self._has_session_role(interaction.user):
            return await interaction.response.send_message("You don’t have permission to start a session.", ephemeral=True)

        self.set_buttons_to_session()
        self.session_state = "idle"

        embed = discord.Embed(title="Session Started", description="**Code: SWATxRP**\n**Owner: misnew12**", color=discord.Color.green())

        join_button = discord.ui.Button(label="Join", url=JOIN_LINK)
        view = discord.ui.View()
        view.add_item(join_button)
        view.add_item(self.low_button)
        view.add_item(self.full_button)
        view.add_item(self.shutdown_button)

        await self.message.edit(embed=embed, view=view)
        await interaction.response.defer()

        for user_id in self.current_votes:
            user = await self.bot.fetch_user(user_id)
            try:
                join_view = discord.ui.View()
                join_view.add_item(discord.ui.Button(label="Join", url=JOIN_LINK))
                dm_embed = discord.Embed(title="Session Invite", description="**Code: SWATxRP**\n**Owner: misnew12**", color=discord.Color.green())
                await user.send(embed=dm_embed, view=join_view)
            except discord.Forbidden:
                print(f"Could not DM {user_id}")

    async def set_low_session(self, interaction: discord.Interaction):
        if not self._has_session_role(interaction.user):
            return await interaction.response.send_message("You don’t have permission.", ephemeral=True)

        self.session_state = "low"
        embed = discord.Embed(title="Low Session Active", description="**Code: SWATxRP**\n**Owner: misnew12**", color=discord.Color.orange())
        await self.message.edit(embed=embed, view=self)
        await interaction.response.defer()

    async def set_full_session(self, interaction: discord.Interaction):
        if not self._has_session_role(interaction.user):
            return await interaction.response.send_message("You don’t have permission.", ephemeral=True)

        self.session_state = "full"
        embed = discord.Embed(title="Full Session Active", description="**Code: SWATxRP**\n**Owner: misnew12**", color=discord.Color.red())
        await self.message.edit(embed=embed, view=self)
        await interaction.response.defer()

    async def shutdown_session(self, interaction: discord.Interaction):
        if not self._has_session_role(interaction.user):
            return await interaction.response.send_message("You don’t have permission to shut down the session.", ephemeral=True)

        self.set_buttons_to_idle()
        self.current_votes.clear()
        self.session_state = "idle"
        embed = discord.Embed(title="⚠️ Session Shut Down", color=discord.Color.dark_red())
        await self.message.edit(embed=embed, view=self)
        await interaction.response.defer()

    async def reset_vote(self, interaction: discord.Interaction):
        if not self._has_session_role(interaction.user):
            return await interaction.response.send_message("You don’t have permission to start a vote.", ephemeral=True)

        self.reset_buttons_to_vote()
        self.current_votes.clear()
        embed = discord.Embed(title="Session Voting", description=f"**0 of {REQUIRED_VOTES} votes**", color=discord.Color.blurple())
        await self.message.edit(content=f"<@&{SESSION_VOTE_PING_ROLE_ID}>", embed=embed, view=self)
        await interaction.response.defer()

    def _has_session_role(self, member: discord.Member):
        return any(role.id == SESSION_ROLE_ID for role in member.roles)


class SessionCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session_view = None

    @app_commands.command(name="vote", description="Start a session vote")
    async def vote(self, interaction: discord.Interaction):
        if interaction.channel.id != TARGET_CHANNEL_ID:
            return await interaction.response.send_message("You can only start the vote in the designated session channel.", ephemeral=True)

        view = SessionView(self.bot)
        embed = discord.Embed(title="Session Voting", description=f"**0 of {REQUIRED_VOTES} votes**", color=discord.Color.blurple())
        msg = await interaction.channel.send(content=f"<@&{SESSION_VOTE_PING_ROLE_ID}>", embed=embed, view=view)
        view.message = msg

        self.session_view = view

        await interaction.response.send_message("✅ Session vote started.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(SessionCog(bot))
