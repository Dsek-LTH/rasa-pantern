from enum import Enum
from typing import final, override


@final
class RoleMapping:
    def __init__(
        self,
        role_id: str,
        discord_role_id: int,
        guild_id: int,
        message_id: int | None = None,
        channel_id: int | None = None,
    ) -> None:
        self.message_id = message_id
        self.channel_id = channel_id
        self.role_id = role_id
        self.discord_role_id = discord_role_id
        self.guild_id = guild_id

    @override
    def __repr__(self) -> str:
        return (
            f"role: {self.role_id} linking to "
            f"{self.discord_role_id} in guild {self.guild_id}"
        )


@final
class SyncOutputData:
    def __init__(self):
        self.total_users_to_change: int = 0
        self.failed_users: int = 0
        self.non_changed_users: int = 0
        self.non_syncable_roles: list[int] = []

    def user_failed(self):
        """
        Increment failed user count.
        """
        self.failed_users += 1

    def user_no_change(self):
        """
        Increment non changed user count.
        """
        self.non_changed_users += 1

    def add_non_syncable_role(self, role_id: int):
        """
        Add a role the bot cannot sync to the list.
        """
        self.non_syncable_roles.append(role_id)

    def get_changed_amount(self) -> int:
        return (
            self.total_users_to_change
            - self.failed_users
            - self.non_changed_users
        )


class CogSetting(Enum):
    DRINKS_HANDLER = 0
    CONFIGURE_DRINKS_HANDLER = 1
    ROLE_SYNC_CONFIG_HANDLER = 2
