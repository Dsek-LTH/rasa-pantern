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


class CogSetting(Enum):
    DRINKS_HANDLER = 0
    CONFIGURE_DRINKS_HANDLER = 1
    ROLE_SYNC_CONFIG_HANDLER = 2
