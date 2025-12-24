from enum import Enum
from typing import final


@final
class RoleMapping:
    def __init__(
        self,
        role_id: str,
        discord_role_id: int,
        guild_id: int,
        message_id: int | None = None,
    ) -> None:
        self.message_id = message_id
        self.role_id = role_id
        self.discord_role_id = discord_role_id
        self.guild_id = guild_id


class CogSetting(Enum):
    DRINKS_HANDLER = 0
    CONFIGURE_DRINKS_HANDLER = 1
    ROLE_SYNC_HANDLER = 2
