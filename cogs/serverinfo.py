import discord
from discord import app_commands
from discord.ext import commands

class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="server_info", description="Get information about the server")
    async def serverinfo_slash(self, interaction: discord.Interaction):
        guild = interaction.guild

        owner = guild.owner if guild.owner else "Owner not found"
        owner_mention = owner.mention if isinstance(owner, discord.Member) else owner

        embed = discord.Embed(
            title=f"Server Info for {guild.name}",
            color=discord.Color.green()
        )

        embed.add_field(name="Server Name", value=guild.name)
        embed.add_field(name="Server ID", value=guild.id)
        embed.add_field(name="Owner", value=owner_mention)
        embed.add_field(name="Member Count", value=guild.member_count)
        embed.add_field(name="Channel Count", value=len(guild.channels))
        embed.add_field(name="Creation Date", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"))

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        else:
            embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/0.png")

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ServerInfo(bot))
