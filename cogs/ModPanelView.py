import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta

STAFF_ROLE_ID = 1375985192174354442

class ModPanelView(discord.ui.View):
    def __init__(self, target: discord.Member):
        super().__init__(timeout=None)
        self.target = target
        self.warnings_db = {}  # This should ideally be shared or persistent

    @discord.ui.button(label="⚠ Warn", style=discord.ButtonStyle.danger)
    async def warn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.warnings_db[self.target.id] = self.warnings_db.get(self.target.id, 0) + 1
        try:
            await self.target.send(f"You have been warned in **{interaction.guild.name}**. Total warnings: {self.warnings_db[self.target.id]}")
        except discord.Forbidden:
            pass
        await interaction.response.send_message(
            f"⚠️ {self.target.mention} warned. Total warnings: `{self.warnings_db[self.target.id]}`", ephemeral=False
        )

    @discord.ui.button(label="👢 Kick", style=discord.ButtonStyle.primary)
    async def kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.target.kick(reason=f"Kicked by {interaction.user}")
            await interaction.response.send_message(f"👢 {self.target.mention} has been kicked.", ephemeral=False)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I can't kick this user.", ephemeral=True)

    @discord.ui.button(label="❌ Close Panel", style=discord.ButtonStyle.secondary)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

    @discord.ui.select(
        placeholder="More actions...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="View Warnings", description="See how many warnings the user has", emoji="📄"),
            discord.SelectOption(label="Clear Warnings", description="Remove all warnings from the user", emoji="🧹"),
            discord.SelectOption(label="Timeout (10 min)", description="Put the user in timeout for 10 minutes", emoji="🔇"),
        ],
        row=1,
    )
    async def select_action(self, interaction: discord.Interaction, select: discord.ui.Select):
        choice = select.values[0]

        if choice == "View Warnings":
            count = self.warnings_db.get(self.target.id, 0)
            await interaction.response.send_message(f"🔍 {self.target.mention} has `{count}` warning(s).", ephemeral=True)

        elif choice == "Clear Warnings":
            if self.target.id in self.warnings_db:
                del self.warnings_db[self.target.id]
                try:
                    await self.target.send(f"Your warnings have been cleared in **{interaction.guild.name}**.")
                except discord.Forbidden:
                    pass
                await interaction.response.send_message(f"✅ Cleared all warnings for {self.target.mention}.", ephemeral=False)
            else:
                await interaction.response.send_message("🫧 No warnings to clear.", ephemeral=True)

        elif choice == "Timeout (10 min)":
            try:
                await self.target.timeout(timedelta(minutes=10), reason=f"Timeout by {interaction.user}")
                await interaction.response.send_message(f"🔇 {self.target.mention} has been timed out for 10 minutes.", ephemeral=False)
            except discord.Forbidden:
                await interaction.response.send_message("❌ I can't timeout this user.", ephemeral=True)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Shared warnings database (you might want to load/save this persistently)
        self.warnings_db = {}

    @app_commands.command(name="mod_panel", description="Open a moderation panel.")
    @app_commands.describe(user="The user to moderate.")
    @app_commands.checks.has_role(STAFF_ROLE_ID)
    async def mod_panel(self, interaction: discord.Interaction, user: discord.Member):
        if user == interaction.user:
            await interaction.response.send_message("❌ You can't moderate yourself.", ephemeral=True)
            return
        if user.top_role >= interaction.user.top_role:
            await interaction.response.send_message("❌ That user has a higher or equal role than you.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🛠 Moderation Panel",
            description=f"Choose an action for {user.mention}",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Username", value=str(user), inline=True)
        embed.add_field(name="User ID", value=str(user.id), inline=True)
        embed.add_field(name="Warnings", value=str(self.warnings_db.get(user.id, 0)), inline=True)
        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)

        view = ModPanelView(user)
        # Pass shared warnings_db to the view so warnings are synced
        view.warnings_db = self.warnings_db
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

    @mod_panel.error
    async def mod_panel_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingRole):
            await interaction.response.send_message("🚫 You don't have permission to use this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
