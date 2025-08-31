import discord
from discord.ext import commands
from utils.anti_nuke import get_guild_settings, punish_executor

class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------------------- ANTI-BAN --------------------
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        entry = await guild.audit_logs(limit=1, action=discord.AuditLogAction.ban).flatten()
        if not entry:
            return
        executor = entry[0].user
        settings = await get_guild_settings(guild.id)
        if executor.id in settings["whitelisted_users"]:
            return

        if settings.get("anti_ban", True):
            await guild.unban(user, reason="Anti-Nuke: Unauthorized ban")
            await punish_executor(executor, reason="Anti-Nuke: Unauthorized ban")

    # -------------------- ANTI-KICK --------------------
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild
        entry = await guild.audit_logs(limit=1, action=discord.AuditLogAction.kick).flatten()
        if not entry:
            return
        executor = entry[0].user
        settings = await get_guild_settings(guild.id)
        if executor.id in settings["whitelisted_users"]:
            return

        if settings.get("anti_kick", True):
            await punish_executor(executor, reason="Anti-Nuke: Unauthorized kick")

    # -------------------- ANTI-ROLE DELETE --------------------
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        guild = role.guild
        entry = await guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete).flatten()
        if not entry:
            return
        executor = entry[0].user
        settings = await get_guild_settings(guild.id)
        if executor.id in settings["whitelisted_users"]:
            return

        if settings.get("anti_role_delete", True):
            await punish_executor(executor, reason="Anti-Nuke: Unauthorized role deletion")

def setup(bot):
    bot.add_cog(AntiNuke(bot))
