import discord
from discord.ext import commands
from discord import app_commands
import json
from datetime import datetime

class EventManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.events = []
        self.events_file = "events.json"
        self.load_events()

    def load_events(self):
        try:
            with open(self.events_file, "r") as f:
                self.events = json.load(f)
        except FileNotFoundError:
            self.events = []

    def save_events(self):
        with open(self.events_file, "w") as f:
            json.dump(self.events, f, indent=4)

    @app_commands.command(name="event", description="Create an event")
    @app_commands.describe(
        event_name="Name of the event",
        event_date="Date of the event (YYYY-MM-DD)",
        event_time="Time of the event (HH:MM, 24-hour)",
        event_description="Description of the event"
    )
    async def event_slash(self, interaction: discord.Interaction, event_name: str, event_date: str, event_time: str, event_description: str):
        try:
            event_datetime = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")
        except ValueError:
            await interaction.response.send_message(
                "Invalid date/time format. Please use 'YYYY-MM-DD' for the date and 'HH:MM' for the time.",
                ephemeral=True
            )
            return

        event_data = {
            "name": event_name,
            "date": event_datetime.strftime("%Y-%m-%d"),
            "time": event_datetime.strftime("%H:%M"),
            "description": event_description,
            "creator": interaction.user.name
        }
        self.events.append(event_data)
        self.save_events()

        embed = discord.Embed(
            title=f"Event Created: {event_name}",
            description=(
                f"**Date:** {event_data['date']}\n"
                f"**Time:** {event_data['time']}\n"
                f"**Description:** {event_description}\n"
                f"**Creator:** {interaction.user.name}"
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="events", description="View upcoming events")
    async def events_slash(self, interaction: discord.Interaction):
        if not self.events:
            await interaction.response.send_message(
                "There are no upcoming events at the moment.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Upcoming Events",
            description="Here are the upcoming events for the server:",
            color=discord.Color.blue()
        )

        for event in self.events:
            embed.add_field(
                name=event["name"],
                value=(
                    f"**Date:** {event['date']}\n"
                    f"**Time:** {event['time']}\n"
                    f"**Description:** {event['description']}\n"
                    f"**Creator:** {event['creator']}"
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(EventManager(bot))
