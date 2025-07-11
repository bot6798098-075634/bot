# ------------------------ ping slash command ------------------------

@tree.command(name="ping", description="Check bot's latency and uptime")
async def ping_slash(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)  # in ms
    now = datetime.now(timezone.utc)
    uptime_duration = now - bot.start_time
    uptime_str = str(timedelta(seconds=int(uptime_duration.total_seconds())))

    embed = discord.Embed(
        title=f"{logo_emoji} SWAT Roleplay Community",
        description=(
            "Information about the bot status\n"
            f"> {pong_emoji} Latency: `{latency} ms`\n"
            f"> {time_emoji} Uptime: `{uptime_str}`\n"
            f"{now.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        ),
        color=discord.Color.blue()
    )

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)

    embed.set_footer(text="SWAT Roleplay Community")
    await interaction.response.send_message(embed=embed)
