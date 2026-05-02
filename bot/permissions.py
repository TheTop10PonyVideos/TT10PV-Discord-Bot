from discord.app_commands import checks, check
from discord import Interaction
from config import Roles


def administrator():
    return checks.has_permissions(administrator=True)


def moderator():
    def predicate(interaction: Interaction):
        return (
            interaction.user.guild_permissions.administrator
            or any(role.id == Roles.MODERATOR for role in interaction.user.roles)
        )

    return check(predicate)


def series_staff():
    def predicate(interaction: Interaction):
        return (
            interaction.user.guild_permissions.administrator
            or any(role.id in (Roles.MODERATOR, Roles.SERIES_STAFF) for role in interaction.user.roles)
        )

    return check(predicate)


class PermissionMixin:
    """Checks a users permissions before allowing a button interaction's callback to run"""

    async def interaction_check(self, interaction: Interaction):
        return (
            interaction.user.guild_permissions.administrator
            or any(role.id in (Roles.MODERATOR, Roles.SERIES_STAFF) for role in interaction.user.roles)
        )
