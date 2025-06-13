import discord
from discord.ext import commands
from discord import app_commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.remove_command("help")

    @commands.command(name="help", description="Show all available commands and their descriptions")
    async def help_prefix(self, ctx):
        embed = self.create_help_embed(prefix=True)
        await ctx.send(embed=embed)

    @app_commands.command(name="help", description="Show all available commands and their descriptions")
    async def help_slash(self, interaction: discord.Interaction):
        embed = self.create_help_embed()
        await interaction.response.send_message(embed=embed)

    def create_help_embed(self, prefix=False):
        embed = discord.Embed(
            title="Bot Commands List",
            description="Explore the available commands grouped by category. Use `/command [command name]` for more details."
            if prefix else "Explore the available commands grouped by category. Use </command:1381009162334503014> for more details.",
            color=discord.Color.blurple()
        )

        sections = {
            "**\U0001F6E0\uFE0F General**": ["ping", "say", "embed"],
            "**\u2699\uFE0F Moderation**": ["slowmode", "clear", "nickname", "warn", "warnings", "unwarn", "clear_all_warnings", "shutdown", "kick", "ban", "unban", "mute", "unmute"],
            "**\U0001F6A8 ER:LC Management**": ["session vote"],
            "**\U0001F512 Channel Management**": ["lock", "unlock"],
            "**\u23F0 AFK Management**": ["afk", "unafk"],
            "**\U0001F4BC Other (Part 1)**": ["roleinfo", "invite", "server_info", "user_info", "remindme", "servericon", "suggestion", "staff_suggestion", "staff_feedback", "events"],
            "**\U0001F4BC Other (Part 2)**": ["event", "mod_panel", "report", "poll", "setreportticket", "settickets", "up_time", "dm"]
        }

        for name, cmds in sections.items():
            if prefix:
                value = ", ".join(f"`{cmd}`" for cmd in cmds)
            else:
                value = "\n".join(f"</{cmd}:ID>" for cmd in cmds) + "\nUse </command:1381009162334503014> for more details."
            embed.add_field(name=name, value=value, inline=False)

        embed.set_footer(text="The SWAT Roleplay Community | Use /command [command name] for more details.")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1234567890/1234567890/thumbnail_image.png")
        return embed

    @app_commands.command(name="command", description="Get detailed help for a specific command")
    async def command_help_slash(self, interaction: discord.Interaction, command_name: str):
        await self.send_command_help(interaction.response.send_message, command_name)

    @commands.command(name="command", description="Get detailed help for a specific command")
    async def command_help_prefix(self, ctx, command_name: str):
        await self.send_command_help(ctx.send, command_name)

    async def send_command_help(self, send_func, command_name):
        command_name = command_name.lower()
        command_details = {
            "ping": "Ping the bot to check if it's online.",
            "help": "Show all available commands and their descriptions.",
            "command": "Get detailed help for a specific command.",
            "say": "Let the bot repeat a message of your choice.",
            "embed": "Create a custom embed message with specified fields.",
            "slowmode": "Set slowmode in a channel to restrict message frequency.",
            "clear": "Clear a specified number of messages in a channel.",
            "kick": "Kick a member from the server.",
            "ban": "Ban a member from the server.",
            "unban": "Unban a member from the server.",
            "mute": "Mute a member so they can't send messages.",
            "unmute": "Unmute a member to allow them to send messages.",
            "giverole": "Give a role to a member.",
            "removerole": "Remove a role from a member.",
            "muteall": "Mute all members in the server.",
            "unmuteall": "Unmute all members in the server.",
            "lock": "Lock the current channel so no one can send messages.",
            "unlock": "Unlock the current channel to allow messages.",
            "lockdown": "Lock all channels in the server.",
            "stop_lockdown": "Unlock all channels in the server.",
            "afk": "Set yourself as AFK.",
            "unafk": "Remove your AFK status.",
            "roleinfo": "Get information about a specific role.",
            "invite": "Get the invite link for the bot.",
            "server_info": "Get information about the server.",
            "user_info": "Get information about a specific user.",
            "poll": "Create a poll to ask the server a question.",
            "remindme": "Set a reminder that notifies you at a specified time.",
            "servericon": "Get the server's icon.",
            "suggestion": "Submit a suggestion for the bot or server.",
            "staff_feedback": "Submit feedback for a staff member.",
            "events": "View upcoming events.",
            "event": "Create an event.",
            "shutdown": "Shut down the bot (OWNER ONLY).",
            "clear_all_warnings": "Clear all warnings for a member.",
            "nickname": "Change a user's nickname.",
            "warn": "Warn a member for breaking the rules.",
            "warnings": "View all warnings for a member.",
            "unwarn": "Remove a specific warning from a member.",
            "staff_suggestion": "Submit a suggestion only visible to staff.",
            "mod_panel": "Open a panel with moderator tools.",
            "report": "Report a user to the moderation team.",
            "setreportticket": "Send the In-Game Report ticket buttons.",
            "settickets": "Send support ticket buttons for various topics.",
            "up_time": "Show how long the bot has been running.",
            "dm": "Send yourself a DM with embed/message builder tools.",
            "session vote": "Start a vote for an ER:LC session action."
        }

        matching = [name for name in command_details if command_name in name]

        if len(matching) == 1:
            cmd = matching[0]
            embed = discord.Embed(
                title=f"Help: /{cmd}",
                description=command_details[cmd],
                color=discord.Color.green()
            )
            await send_func(embed=embed)
        elif len(matching) > 1:
            await send_func(f"Multiple matches found: {', '.join(matching)}. Please be more specific.")
        else:
            await send_func(f"Sorry, no detailed information found for `/command {command_name}`.")


async def setup(bot):
    await bot.add_cog(Help(bot))
