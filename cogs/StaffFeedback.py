import discord
from discord import app_commands
from discord.ext import commands

class StaffFeedback(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.staff_role_id = 1343234687505530902  # Replace with your staff role ID
        self.feedback_channel_id = 1343621982549311519  # Replace with your feedback channel ID

    @app_commands.command(name="staff_feedback", description="Submit feedback for a staff member.")
    @app_commands.describe(text="Your feedback text", staff="The staff member to give feedback about")
    async def staff_feedback_slash(self, interaction: discord.Interaction, text: str, staff: discord.Member):
        if interaction.user == staff:
            await interaction.response.send_message(
                "You cannot give feedback to yourself.",
                ephemeral=True
            )
            return
        
        if self.staff_role_id not in [role.id for role in staff.roles]:
            await interaction.response.send_message(
                f"{staff.mention} does not have the required staff role.",
                ephemeral=True
            )
            return
        
        if not text or len(text) < 10:
            await interaction.response.send_message(
                "Please provide valid feedback (at least 10 characters long).",
                ephemeral=True
            )
            return
        
        feedback_channel = interaction.guild.get_channel(self.feedback_channel_id)
        if not feedback_channel:
            await interaction.response.send_message(
                "Feedback channel not found. Please contact an admin.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="Staff Feedback",
            description=text,
            color=discord.Color.blue()
        )
        embed.add_field(name="Feedback for", value=staff.mention, inline=True)
        embed.add_field(name="Submitted by", value=interaction.user.mention, inline=True)
        embed.add_field(name="User ID", value=str(interaction.user.id), inline=True)
        embed.set_footer(text="SWAT Roleplay Community")

        await feedback_channel.send(f"-# <:PING:1381073968873607229> {staff.mention}", embed=embed)
        await interaction.response.send_message(
            f"Thank you for your feedback about {staff.mention}. It has been submitted for review.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(StaffFeedback(bot))
