# utils/checks.py

import discord
from discord import app_commands

# ---------------- Role IDs ----------------
staff_role_id = 1316076249629851648
mod_role_id = 1316076249629851648
admin_role_id = 1316076249629851648
superviser_role_id = 1316076249629851648
management_role_id = 1316076249629851648
ia_role_id = 1316076249629851648
ownership_role_id = 1316076249629851648
session_manager_role_id = 1316076249629851648
staff_trainer_role_id = 1316076249629851648
afk_role_id = 1327359797154152539
event_role_id = 1316076249629851648
staff_help_role_id = 1316076249629851648

owner_id = 1276264248095412387

# ---------------- Generic role check factory ----------------
def has_role(role_id: int):
    """Factory function to create role-based checks"""
    async def predicate(interaction: discord.Interaction):
        if interaction.guild is None:
            return False
        return any(role.id == role_id for role in interaction.user.roles)
    return app_commands.check(predicate)

# ---------------- Specific Checks ----------------
def is_staff():
    return has_role(staff_role_id)

def is_mod():
    return has_role(mod_role_id)

def is_admin():
    return has_role(admin_role_id)

def is_superviser():
    return has_role(superviser_role_id)

def is_management():
    return has_role(management_role_id)

def is_ia():
    return has_role(ia_role_id)

def is_ownership():
    return has_role(ownership_role_id)

def is_session_manager():
    return has_role(session_manager_role_id)

def is_staff_trainer():
    return has_role(staff_trainer_role_id)

def is_afk():
    return has_role(afk_role_id)

def is_event():
    return has_role(event_role_id)

def is_staff_help():
    return has_role(staff_help_role_id)

def is_owner():
    """Check if the user is the bot owner"""
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id == OWNER_ID
    return app_commands.check(predicate)
