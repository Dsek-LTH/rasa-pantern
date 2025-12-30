from abc import ABC, abstractmethod


class Database(ABC):
    def __init__(self, db_file: str) -> None:
        self.db_file: str = db_file

    @abstractmethod
    async def execute_query(
        self, query: str, vars: tuple[str | int, ...] = ()
    ) -> None: ...

    @abstractmethod
    async def execute_read_query(
        self, query: str, vars: tuple[str | int, ...] = ()
    ) -> dict[str, str | int] | None: ...

    @abstractmethod
    async def execute_multiple_read_query(
        self, query: str, vars: tuple[str | int, ...] = ()
    ) -> list[dict[str, str | int]] | None: ...
