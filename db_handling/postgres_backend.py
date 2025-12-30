# The fact that these are needed because asyncpg doesn't have proper typing
# infuriates me, but so is life I guess
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false

# asyncpg doesn't have stub files:
# pyright: reportMissingTypeStubs=false
from __future__ import annotations

import re
from typing import cast, override

import asyncpg

from db_handling.abc import Database


class PostresqlHandler(Database):
    def __init__(self, pool: asyncpg.Pool):
        self.pool: asyncpg.Pool = pool

    @classmethod
    async def create(
        cls, db_name: str, user: str, password: str, host: str
    ) -> PostresqlHandler:
        pool: asyncpg.Pool = await asyncpg.create_pool(
            user=user, password=password, database=db_name, host=host
        )
        return cls(pool)

    @override
    async def execute_query(
        self, query: str, vars: tuple[str | int, ...] = ()
    ) -> None:
        assert self.pool
        async with self.pool.acquire() as conn:
            print(f"type of con: {type(conn)}")
            async with conn.transaction():
                try:
                    await conn.execute(self.translate_sql(query), *vars)
                except asyncpg.PostgresError as e:
                    print(f"DB error: {e} occured")

    @override
    async def execute_read_query(
        self, query: str, vars: tuple[str | int, ...] = ()
    ) -> dict[str, str | int] | None:
        assert self.pool
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    row = await conn.fetchrow(self.translate_sql(query), *vars)
                    if row is None:
                        return None
                    # TODO: make this one line and remove var
                    d = cast(dict[str, str | int], dict(row))
                    print(d)
                    return d
                except asyncpg.PostgresError as e:
                    print(f"DB error: {e} occured")

    @override
    async def execute_multiple_read_query(
        self, query: str, vars: tuple[str | int, ...] = ()
    ) -> list[dict[str, str | int]] | None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    rows = await conn.fetch(self.translate_sql(query), *vars)
                    if not rows:
                        return None
                    # TODO: make this one line and remove var
                    d = [cast(dict[str, str | int], dict(row)) for row in rows]
                    print(d)
                    return d
                except asyncpg.PostgresError as e:
                    print(f"DB error: {e} occured")

    def translate_sql(self, query: str) -> str:
        """Replace ? symbols for sqlite input with $n for Postgress."""
        count: int = 0

        def replacer(_: re.Match[str]) -> str:
            nonlocal count
            count += 1
            return f"${count}"

        # TODO: make this oneline and remove debug
        output = re.sub("\\?", replacer, query)
        print(output)
        return output
