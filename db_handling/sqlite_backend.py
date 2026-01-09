from datetime import datetime, timedelta, timezone
from sqlite3 import Error
from typing import override

import asqlite

from db_handling.abc import Database


class SqliteHandler(Database):
    def __init__(self, db_file: str):
        self.db_file: str = db_file
        import sqlite3

        # --- Adapters & converters ---
        def convert_to_naive_timestamp(dt: datetime) -> str:
            if dt.tzinfo:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt.isoformat(timespec="microseconds")

        sqlite3.register_adapter(datetime, convert_to_naive_timestamp)

        sqlite3.register_converter(
            "TIMESTAMP", lambda s: datetime.fromisoformat(s.decode())
        )

        # We store time-deltas in ms instead of µs just so we don't overload
        # the integer type. It can support intervals up to 292 years or so, but
        # I'm paranoid someone will accidentally break something... It's not
        # like we really need the precison anyways
        sqlite3.register_adapter(
            timedelta,
            lambda td: td.days * 86400000
            + td.seconds * 1000
            + td.microseconds // 1000,  # ms
        )
        sqlite3.register_converter(
            "INTERVAL", lambda s: timedelta(milliseconds=int(s))
        )

    @override
    async def execute_query(
        self,
        query: str,
        vars: tuple[str | int | datetime | timedelta | bool | None, ...] = (),
    ) -> None:
        async with asqlite.connect(
            self.db_file,
            detect_types=asqlite.PARSE_DECLTYPES | asqlite.PARSE_COLNAMES,
        ) as conn:
            async with conn.cursor() as cursor:
                try:
                    _ = await cursor.execute(query, vars)
                    await conn.commit()
                except Error as e:
                    print(f"the error {e} occured")

    @override
    async def execute_read_query(
        self,
        query: str,
        vars: tuple[str | int | datetime | timedelta | bool | None, ...] = (),
    ) -> dict[str, str | int | datetime | timedelta | bool] | None:
        async with asqlite.connect(
            self.db_file,
            detect_types=asqlite.PARSE_DECLTYPES | asqlite.PARSE_COLNAMES,
        ) as conn:
            async with conn.cursor() as cursor:
                try:
                    _ = await cursor.execute(query, vars)
                    result = await cursor.fetchone()
                    if not result:
                        return None
                    pairs: dict[
                        str, str | int | datetime | timedelta | bool
                    ] = {}
                    for key in result.keys():
                        pairs[key] = result.__getitem__(key)
                except Error as e:
                    print(f"The error '{e}' occurred")

    @override
    async def execute_multiple_read_query(
        self,
        query: str,
        vars: tuple[str | int | datetime | timedelta | bool | None, ...] = (),
    ) -> list[dict[str, str | int | datetime | timedelta | bool]] | None:
        async with asqlite.connect(
            self.db_file,
            detect_types=asqlite.PARSE_DECLTYPES | asqlite.PARSE_COLNAMES,
        ) as conn:
            async with conn.cursor() as cursor:
                try:
                    _ = await cursor.execute(query, vars)
                    result = await cursor.fetchall()
                    if not result:
                        return None
                    output: list[
                        dict[str, str | int | datetime | timedelta | bool]
                    ] = []
                    for entry in result:
                        pairs: dict[
                            str, str | int | datetime | timedelta | bool
                        ] = {}
                        for key in entry.keys():
                            pairs[key] = entry.__getitem__(key)
                        output.append(pairs)
                    return output
                except Error as e:
                    print(f"The error '{e}' occurred")
