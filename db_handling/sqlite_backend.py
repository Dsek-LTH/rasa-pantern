from sqlite3 import Error
from typing import override

import asqlite

from db_handling.abc import Database


class SqliteHandler(Database):
    def __init__(self, db_file: str):
        self.db_file: str = db_file

    @override
    async def execute_query(
        self, query: str, vars: tuple[str | int, ...] = ()
    ) -> None:
        async with asqlite.connect(self.db_file) as conn:
            async with conn.cursor() as cursor:
                try:
                    _ = await cursor.execute(query, vars)
                    await conn.commit()
                except Error as e:
                    print(f"the error {e} occured")

    @override
    async def execute_read_query(
        self, query: str, vars: tuple[str | int, ...] = ()
    ) -> dict[str, str | int] | None:
        async with asqlite.connect(self.db_file) as conn:
            async with conn.cursor() as cursor:
                try:
                    _ = await cursor.execute(query, vars)
                    result = await cursor.fetchone()
                    if not result:
                        return None
                    pairs: dict[str, str | int] = {}
                    for key in result.keys():
                        pairs[key] = result.__getitem__(key)
                except Error as e:
                    print(f"The error '{e}' occurred")

    @override
    async def execute_multiple_read_query(
        self, query: str, vars: tuple[str | int, ...] = ()
    ) -> list[dict[str, str | int]] | None:
        async with asqlite.connect(self.db_file) as conn:
            async with conn.cursor() as cursor:
                try:
                    _ = await cursor.execute(query, vars)
                    result = await cursor.fetchall()
                    if not result:
                        return None
                    output: list[dict[str, str | int]] = []
                    for entry in result:
                        pairs: dict[str, str | int] = {}
                        for key in entry.keys():
                            pairs[key] = entry.__getitem__(key)
                        output.append(pairs)
                    return output
                except Error as e:
                    print(f"The error '{e}' occurred")
