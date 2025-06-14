import discord
from discord.ext import commands
from discord import app_commands

class Info(commands.Cog):
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

    @app_commands.command(name="user_info", description="Get information about a user.")
    async def userinfo_slash(self, interaction: discord.Interaction, member: discord.Member):
        roles = [role.mention for role in member.roles if role != member.guild.default_role]
        roles_display = ", ".join(roles) if roles else "No roles"

        embed = discord.Embed(
            title=f"👤 User Information: {member}",
            color=member.color if member.color.value else discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)

        embed.add_field(name="📝 Username", value=f"{member.name}#{member.discriminator}", inline=True)
        embed.add_field(name="🆔 User ID", value=member.id, inline=True)
        embed.add_field(name="📆 Account Created", value=member.created_at.strftime("%B %d, %Y at %H:%M UTC"), inline=False)
        embed.add_field(name="📥 Joined Server", value=member.joined_at.strftime("%B %d, %Y at %H:%M UTC"), inline=False)
        embed.add_field(name="🎭 Roles", value=roles_display, inline=False)
        embed.add_field(name="📶 Status", value=str(member.status).title(), inline=True)
        embed.add_field(name="🤖 Bot?", value="Yes" if member.bot else "No", inline=True)

        if interaction.user.avatar:
            embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.avatar.url)
        else:
            embed.set_footer(text=f"Requested by {interaction.user}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roleinfo", description="Get information about a specific role")
    async def roleinfo_slash(self, interaction: discord.Interaction, role: discord.Role):
        permissions = [perm[0] for perm in role.permissions if perm[1]]
        permissions_str = ", ".join(permissions) if permissions else "None"

        embed = discord.Embed(
            title=f"Role Info for {role.name}",
            color=role.color
        )
        embed.add_field(name="Role Name", value=role.name, inline=False)
        embed.add_field(name="Created At", value=role.created_at.strftime("%B %d, %Y"), inline=False)
        embed.add_field(name="Position", value=role.position, inline=False)
        embed.add_field(name="Permissions", value=permissions_str, inline=False)

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Info(bot))
