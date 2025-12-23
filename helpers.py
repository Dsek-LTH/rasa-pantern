from enum import Enum
from typing import final


@final
class RoleMapping:
    def __init__(
        self, message_id: int, role_id: str, discord_role_id: int
    ) -> None:
        self.message_id = message_id
        self.role_id = role_id
        self.discord_role_id = discord_role_id


class SettingsCog(Enum):
    DRINKS_HANDLER = 0
