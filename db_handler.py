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
            "name" TEXT NOT NULL,
            UNIQUE(guild_id, name)
        );
        """
        await self._execute_query(create_drinks_table)

        create_drunk_table = """
        CREATE TABLE IF NOT EXISTS drunk_drinks (
            "id" INTEGER PRIMARY KEY NOT NULL,
            "guild_id" INTEGER NOT NULL,
            "message_id" INTEGER NOT NULL,
            "user_id" INTEGER NOT NULL,
            "name" TEXT NOT NULL,
            UNIQUE(guild_id, message_id, user_id)
        )
        """
        await self._execute_query(create_drunk_table)

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
    async def get_drink_option_list(self, guild_id: int) -> list[str]:
        """
        Get a list of all drinks accepted in the given guild.

        Args:
            guild_id(int): The id of the guild to search for.

        Returns:
            list[str]: A list of drink names.

        """

        drink_query = """
            SELECT * FROM drink_options
            WHERE guild_id = ?;
        """

        drinks = await self._execute_multiple_read_query(
            drink_query, (guild_id,)
        )
        # TODO: error handling here if no drinks exist in system?
        # or do we let that fall upwards?
        drink_list = []
        if drinks:
            for drink in drinks:
                drink_list.append(drink.__getitem__("name"))
        return drink_list

    async def add_drink_option(self, guild_id: int, drink_name: str) -> None:
        """
        Adds a drink option to the list of valid ones for the given guild.

        Args:
            guild_id (int): The id of the guild.
            drink_name (str): The name of the drink to add.

        Throws:
            ValueError: If there is already a drink with that name in the guild.
        """
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
            raise (
                ValueError(
                    f"Duplicate drinks {drink_name} in server: {guild_id}"
                )
            )
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

    async def remove_drink_option(
        self, guild_id: int, drink_name: str
    ) -> None:
        """
        Remove a drink option to the list of valid ones for the given guild.

        Args:
            gulid_id (int): The id of the guild.
            drink_name (str): The name of the drink to add.
        """
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

    async def set_drunk_drink(
        self, guild_id: int, message_id: int, user_id: int, drink_name: str
    ) -> bool:
        """
        Sets the drink for a certain user and poll to the given value.
        If the user already has an entry for the given poll it is
        updated instead.

        Args:
            guild_id (int): The id of the guild.
            message_id (int): The id of the tally message.
            user_id (int): The id of the user.
            drink_name (str): The name of the drink.

        Returns:
            bool: If a new entry was added.
        """
        # TODO: We might want to check that only valid drinks can be entered
        # into the system. This is not a user facing function, so it should be
        # fine, but you never know...

        if drink_name == "nothing":
            print(
                "Error: Tried adding empty drink to database for message: "
                + str(message_id)
            )
            return False
        current_drink_query = """
            SELECT * FROM drunk_drinks
            WHERE
                guild_id = ?
            AND
                message_id = ?
            AND
                user_id = ?
        """
        current_drink = await self._execute_read_query(
            current_drink_query, (guild_id, message_id, user_id)
        )

        if current_drink:
            if current_drink["name"] == drink_name:
                return False
            else:
                new_entry = False
                # Replace current drink
                drink_add_query = """
                    UPDATE drunk_drinks
                    SET name = ?
                    WHERE
                        guild_id = ?
                    AND
                        message_id = ?
                    AND
                        user_id = ?
                """
        else:
            new_entry = True
            drink_add_query = """
                INSERT INTO
                    drunk_drinks (name, guild_id, message_id, user_id)
                VALUES
                    (?, ?, ?, ?)
            """

        await self._execute_query(
            drink_add_query,
            (
                drink_name,
                guild_id,
                message_id,
                user_id,
            ),
        )

        return new_entry

    async def remove_drunk_drink(
        self, guild_id: int, message_id: int, user_id: int
    ) -> None:
        """
        Remove any drink for a certain user and poll.

        Args:
            guild_id (int): The id of the guild.
            message_id (int): The id of the tally message.
            user_id (int): The id of the user.
        """
        drink_remove_query = """
            DELETE FROM drunk_drinks
            WHERE guild_id = ?
            AND
                message_id = ?
            AND
                user_id = ?;
        """
        await self._execute_query(
            drink_remove_query,
            (
                guild_id,
                message_id,
                user_id,
            ),
        )

    async def get_tally(
        self, message_id: int, guild_id: int
    ) -> dict[str, list[int]]:
        """
        Gets drink tally information from a message.

        Args:
            message_id (int): The message id of the tally to find data from.
            guild_id (int): The guild id of the tally to find data from.

        Returns:
            dict[str, list[int]]: A dict mapping the name of drinks to all
            users who selected that drink
        """
        get_drinks_query = """
            SELECT user_id, name
            FROM drunk_drinks
            WHERE message_id = ?;
        """
        drunk_list = await self._execute_multiple_read_query(
            get_drinks_query, (message_id,)
        )

        res = {}
        if drunk_list:
            for drunk in drunk_list:
                res.setdefault(drunk["name"], []).append(drunk["user_id"])

        return res


if __name__ == "__main__":
    print("Creating tables if they don't exist")

    from os import environ

    from dotenv import load_dotenv

    load_dotenv()
    db_file = environ["DB_FILE"]

    dbHandler = DBHandler(db_file)
    asyncio.run(dbHandler._create_tables())
