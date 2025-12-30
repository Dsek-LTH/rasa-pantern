from sqlite3 import Error
from typing import override

import asqlite

from db_handling.abc import Database


class Sqlite_handler(Database):
    @override
    async def execute_query(
        self, query: str, vars: tuple[str | int, ...] = ()
    ) -> None:
        """Execute a query in the database.

        Args:
            query (str): The SQL query string.
            vars (tuple): The query string fill in vars.
        """
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
        """Execute a query in the database and parses the first found entry
        into a dictionary.

        Args:
            query (str): The SQL query string.
            vars (tuple): The query string fill in vars.

        Returns:
            dict: Key value pairs with data from the query results.
                  form: {field_name: value}
        """
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
        """Execute a query in the database and parses all found entries into
        a list of dictionaries.

        Args:
            query (str): The SQL query string.
            vars (tuple): The query string fill in vars.

        Returns:
            list[dict]: list of key value pairs with data from the query
                        results. form: [{field_name: value}]"""
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
