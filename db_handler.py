import asyncio
from sqlite3 import Error
from typing import Any

import asqlite


class DBHandler:
    def __init__(self, db_file) -> None:
        self.db_file = db_file

    async def _create_tables(self) -> None:
        """Initialize database if it doesn't exist"""
        create_drinks_table = """
        CREATE TABLE IF NOT EXISTS drink_options (
            "id" INTEGER PRIMARY KEY NOT NULL,
            "guild_id" INTEGER NOT NULL,
            "name" TEXT NOT NULL
        );
        """
        await self._execute_query(create_drinks_table)
        pass

    async def _execute_query(self, query: str, vars: tuple = ()) -> None:
        """Execute a query in the database.

        Args:
            query (str): The SQL query string.
            vars (tuple): The query string fill in vars.
        """
        async with asqlite.connect(self.db_file) as conn:
            async with conn.cursor() as cursor:
                try:
                    await cursor.execute(query, vars)
                    await conn.commit()
                except Error as e:
                    print(f"the error {e} occured")

    async def _execute_read_query(
        self, query: str, vars: tuple = ()
    ) -> dict[str, Any] | None:
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
                    await cursor.execute(query, vars)
                    result = await cursor.fetchone()
                    if not result:
                        return None
                    pairs = {}
                    for key in result.keys():
                        pairs[key] = result.__getitem__(key)
                    return pairs
                except Error as e:
                    print(f"The error '{e}' occurred")

    async def _execute_multiple_read_query(
        self, query: str, vars: tuple = ()
    ) -> list[dict[str, Any]] | None:
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
                    await cursor.execute(query, vars)
                    result = await cursor.fetchall()
                    if not result:
                        return None
                    output = []
                    for entry in result:
                        pairs = {}
                        for key in entry.keys():
                            pairs[key] = entry.__getitem__(key)
                        output.append(pairs)
                    return output
                except Error as e:
                    print(f"The error '{e}' occurred")

    # ------------------------------------------------------
    # Drink system:
    async def get_drink_list(self, guild_id: int) -> list[str]:
        drink_query = """
            SELECT * FROM drink_options
            WHERE guild_id = ?;
        """

        drinks = await self._execute_multiple_read_query(drink_query, (guild_id,))
        # TODO: error handling here if no drinks exist in system?
        # or do we let that fall upwards?
        drink_list = []
        print(drinks)
        if drinks:
            for drink in drinks:
                drink_list.append(drink.__getitem__("name"))
        return drink_list

    async def add_drink(self, guild_id: int, drink_name: str) -> None:
        drink_check_query = """
            SELECT * FROM drink_options
            WHERE guild_id = ?
            AND
                name = ?;
        """
        drink_exist_check = await self._execute_read_query(
            drink_check_query,
            (
                guild_id,
                drink_name,
            ),
        )
        if drink_exist_check:
            # WARN: We have duplicate drinks in database, handle gracefully
            # later
            print(f"Duplicate drinks {drink_name} in server: {guild_id}")
        else:
            # Add drink to database:
            drink_create_query = """
                INSERT INTO
                    drink_options (guild_id, name)
                VALUES
                    (?, ?);
            """
            await self._execute_query(
                drink_create_query,
                (
                    guild_id,
                    drink_name,
                ),
            )

    async def remove_drink(self, guild_id: int, drink_name: str) -> None:
        drink_remove_query = """
            DELETE FROM drink_options
            WHERE guild_id = ?
            AND
                name = ?;
        """
        await self._execute_query(
            drink_remove_query,
            (
                guild_id,
                drink_name,
            ),
        )
        pass


if __name__ == "__main__":
    print("Creating tables if they don't exist")

    from os import environ

    from dotenv import load_dotenv

    load_dotenv()
    db_file = environ["DB_FILE"]

    dbHandler = DBHandler(db_file)
    asyncio.run(dbHandler._create_tables())
