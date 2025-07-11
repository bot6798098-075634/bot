# ------------------------ Slowmode slash command ------------------------

@tree.command(name="slowmode", description="Set the slowmode duration for a channel")
@app_commands.describe(seconds="Duration of slowmode in seconds")
async def slowmode_slash(interaction: discord.Interaction, seconds: int):
    staff_role = interaction.guild.get_role(staff_role_id)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message(
            f"{failed_emoji} You don't have permission to use this command.",
            ephemeral=True
        )
        return

    await interaction.channel.edit(slowmode_delay=seconds)

    embed = discord.Embed(
        description=f"{time_emoji} Slowmode has been set to `{seconds}` seconds.",
        color=discord.Color.green()
    )

    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text="SWAT Roleplay Community")

    await interaction.response.send_message(embed=embed)
