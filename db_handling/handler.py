import asyncio
from typing import final

from db_handling import postgres_backend, sqlite_backend
from db_handling.abc import Database
from helpers import CogSetting, RoleMapping


@final
class DBHandler:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def create_tables(self) -> None:
        """Initialize database if it doesn't exist"""
        create_drinks_table = """
        CREATE TABLE IF NOT EXISTS drink_options (
            "id" INTEGER PRIMARY KEY NOT NULL,
            "guild_id" INTEGER NOT NULL,
            "name" TEXT NOT NULL,
            UNIQUE(guild_id, name)
        );
        """
        await self.db.execute_query(create_drinks_table)
        print("created drinks table")

        create_drunk_table = """
        CREATE TABLE IF NOT EXISTS drunk_drinks (
            "id" INTEGER PRIMARY KEY NOT NULL,
            "guild_id" INTEGER NOT NULL,
            "message_id" INTEGER NOT NULL,
            "user_id" INTEGER NOT NULL,
            "name" TEXT NOT NULL,
            UNIQUE(guild_id, message_id, user_id)
        );
        """
        await self.db.execute_query(create_drunk_table)
        print("created drunk_table")

        create_tallies_table = """
        CREATE TABLE IF NOT EXISTS tallies (
            "id" INTEGER PRIMARY KEY NOT NULL,
            "guild_id" INTEGER NOT NULL,
            "message_id" INTEGER UNIQUE NOT NULL
        );
        """
        await self.db.execute_query(create_tallies_table)
        print("created tallies table")

        create_role_config_table = """
        CREATE TABLE IF NOT EXISTS role_configs (
            "id" INTEGER PRIMARY KEY NOT NULL,
            "message_id" INTEGER UNIQUE NOT NULL,
            "channel_id" INTEGER NOT NULL,
            "role_id" TEXT UNIQUE NOT NULL,
            "discord_role_id" INTEGER NOT NULL,
            "guild_id" INTEGER NOT NULL,
            UNIQUE(discord_role_id, role_id)
        );
        """
        await self.db.execute_query(create_role_config_table)
        print("created role config table")

        create_settings_table = """
        CREATE TABLE IF NOT EXISTS settings (
            "id" INTEGER PRIMARY KEY NOT NULL,
            "guild_id" INTEGER NOT NULL,
            "cog" INTEGER NOT NULL,
            "config_name" TEXT NOT NULL,
            "value" TEXT NOT NULL,
            UNIQUE(guild_id, cog, config_name)
        );
        """
        await self.db.execute_query(create_settings_table)
        print("created settings table")

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

        drinks = await self.db.execute_multiple_read_query(
            drink_query, (guild_id,)
        )
        # TODO: error handling here if no drinks exist in system?
        # or do we let that fall upwards?
        drink_list: list[str] = []
        if drinks:
            for drink in drinks:
                drink_list.append(str(drink.__getitem__("name")))
        return drink_list

    async def add_drink_option(self, guild_id: int, drink_name: str) -> None:
        """
        Adds a drink option to the list of valid ones for the given guild.

        Args:
            guild_id (int): The id of the guild.
            drink_name (str): The name of the drink to add.

        Throws:
            ValueError: If there is already a drink with that
                        name in the guild.
        """
        drink_check_query = """
            SELECT * FROM drink_options
            WHERE guild_id = ?
            AND
                name = ?;
        """
        drink_exist_check = await self.db.execute_read_query(
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
            await self.db.execute_query(
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
        await self.db.execute_query(
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
        current_drink = await self.db.execute_read_query(
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

        await self.db.execute_query(
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
        await self.db.execute_query(
            drink_remove_query,
            (
                guild_id,
                message_id,
                user_id,
            ),
        )

    async def get_tally(
        self, message_id: int, _guild_id: int
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
        drunk_list = await self.db.execute_multiple_read_query(
            get_drinks_query, (message_id,)
        )

        res: dict[str, list[int]] = {}
        if drunk_list:
            for drunk in drunk_list:
                if not isinstance(drunk["name"], str) or not isinstance(
                    drunk["user_id"], int
                ):
                    return res
                res.setdefault(drunk["name"], []).append(drunk["user_id"])

        return res

    async def get_all_tallies(self) -> list[tuple[int, int]]:
        """
        Returns a list of all tallies in the database.

        Returns:
            list[tuple[int, int]]: Contains (message_id, guild_id).
        """
        get_tally_query = """
            SELECT message_id, guild_id
            FROM tallies;
        """
        tallies = await self.db.execute_multiple_read_query(
            get_tally_query,
        )
        res: list[tuple[int, int]] = []
        if tallies:
            for tally in tallies:
                if not isinstance(tally["message_id"], int) or not isinstance(
                    tally["guild_id"], int
                ):
                    print(
                        "unexpected values in tallies table, "
                        + "attempting to continue without it"
                    )
                    continue
                res.append((tally["message_id"], tally["guild_id"]))
        return res

    async def create_tally(self, message_id: int, guild_id: int) -> None:
        """
        Creates a tally in the database

        Args:
            message_id (int): The message id of the tally.
            guild_id (int): The guild id of the tally.
        """
        create_tally_query = """
            INSERT INTO tallies
                (message_id, guild_id)
            VALUES (?, ?);
        """
        await self.db.execute_query(create_tally_query, (message_id, guild_id))

    async def remove_tally(self, message_id: int) -> None:
        """
        Removes a tally from the database (for example when it's completed).

        Args:
            message_id (int): The message_id for the tally.
        """
        remove_tally_query = """
            DELETE FROM tallies
            WHERE guild_id = ?
            AND
                message_id = ?
        """
        await self.db.execute_query(remove_tally_query, (message_id,))

    # ------------------------------------------------------
    # role config system:
    async def create_role_config(
        self,
        message_id: int,
        channel_id: int,
        role_id: str,
        discord_role_id: int,
        guild_id: int,
    ) -> None:
        """
        Create a role config mapping.

        Args:
            message_id (int): Id of the message that can change this
                            setting in discord.
            channel_id (int): Id of the channel this message is in.
            role_id (str): The external role id for this mapping.
            discord_role_id (int): The discord role id for this mapping.
            guild_id (int): The guild id for this mapping.
        """
        add_config_message_query = """
            INSERT INTO
                role_configs (
                    message_id,
                    channel_id,
                    role_id,
                    discord_role_id,
                    guild_id
                    )
            VALUES
                (?, ?, ?, ?, ?)
        """
        await self.db.execute_query(
            add_config_message_query,
            (message_id, channel_id, role_id, discord_role_id, guild_id),
        )

    async def update_role_config(
        self,
        message_id: int,
        role_id: str,
        discord_role_id: int,
    ) -> None:
        """
        Update mapping for a role config.

        Args:
            message_id (int): message id of the config to update.
            role_id (str): The external role id for this mapping.
            discord_role_id (int): new discord role to map to this LADP role.

        """
        update_role_config_query = """
        UPDATE role_configs
        SET
            role_id = ?,
            discord_role_id = ?
        WHERE
            message_id = ?
        """
        await self.db.execute_query(
            update_role_config_query,
            (role_id, discord_role_id, message_id),
        )

    async def delete_role_config(self, message_id: int) -> None:
        """
        Removes a given role mapping from the db.

        Args:
            message_id (int): The id of the role mapping to delete.
        """
        remove_config_message_query = """
            DELETE FROM role_configs
            WHERE message_id = ?
        """
        await self.db.execute_query(
            remove_config_message_query,
            (message_id,),
        )

    async def purge_role_configs(self, guild_id: int) -> None:
        """
        Removes all role mappings for an entire guild.

        Args:
            guild_id (int): The id of the guild.
        """
        purge_config_message_query = """
            DELETE FROM role_configs
            WHERE guild_id = ?
        """
        await self.db.execute_query(
            purge_config_message_query,
            (guild_id,),
        )

    async def get_role_config(self, message_id: int) -> RoleMapping | None:
        """
        Gets a single role mapping config given it's config message.

        Args:
            message_id (int): The message_id for the config message to get.

        Returns:
            tuple[str, int, int]: (role_id, discord_role_id , guild_id)
        """

        get_config_message_query = """
            SELECT
                role_id,
                discord_role_id,
                guild_id,
                channel_id
            FROM role_configs
            WHERE message_id = ?
        """

        role_config = await self.db.execute_read_query(
            get_config_message_query, (message_id,)
        )
        if not role_config:
            return None
        return RoleMapping(
            str(role_config["role_id"]),
            int(role_config["discord_role_id"]),
            int(role_config["guild_id"]),
            message_id,
            int(role_config["channel_id"]),
        )

    async def get_all_role_configs(self) -> list[RoleMapping]:
        """
        Gets all role mapping configs.

        Returns:
            list[RoleMapping]: A list of role mappings.
        """
        get_config_message_query = """
            SELECT message_id,
                role_id,
                discord_role_id,
                guild_id,
                channel_id
            FROM role_configs
        """
        config_messages = await self.db.execute_multiple_read_query(
            get_config_message_query
        )
        return_list: list[RoleMapping] = []
        if config_messages:
            for message in config_messages:
                if (
                    not isinstance(message["message_id"], int)
                    or not isinstance(message["role_id"], str)
                    or not isinstance(message["discord_role_id"], int)
                    or not isinstance(message["guild_id"], int)
                    or not isinstance(message["channel_id"], int)
                ):
                    return return_list
                return_list.append(
                    RoleMapping(
                        message["role_id"],
                        message["discord_role_id"],
                        message["guild_id"],
                        message["message_id"],
                        message["channel_id"],
                    )
                )
        return return_list

    async def get_guild_role_configs(self, guild_id: int) -> list[RoleMapping]:
        """
        Gets all role mapping configs.

        Args:
            guild_id: the gulid id to get config mappings from.
        Returns:
            list[RoleMapping]: A list of role mappings.
        """
        get_config_message_query = """
            SELECT message_id, role_id, discord_role_id, channel_id
            FROM role_configs
            WHERE guild_id = ?
        """
        config_messages = await self.db.execute_multiple_read_query(
            get_config_message_query, (guild_id,)
        )
        return_list: list[RoleMapping] = []
        if config_messages:
            for message in config_messages:
                if (
                    not isinstance(message["message_id"], int)
                    or not isinstance(message["role_id"], str)
                    or not isinstance(message["discord_role_id"], int)
                    or not isinstance(message["channel_id"], int)
                ):
                    return return_list
                return_list.append(
                    RoleMapping(
                        message["role_id"],
                        message["discord_role_id"],
                        guild_id,
                        message["message_id"],
                        message["channel_id"],
                    )
                )
        return return_list

    # ------------------------------------------------------
    # settings system:
    async def set_setting(
        self, guild_id: int, cog: CogSetting, setting_name: str, value: str
    ) -> None:
        """
        Sets a setting to a value in a given guild and cog.

        Args:
            guild_id (int): The guild to set the setting for.
            cog (SettingsCog): The cog to set the setting for.
            setting_name (str): The setting to set.
            value (str): The value to set it to.
        """
        # TODO: Make this both insert and update instead of having 2 functions
        # maybe?
        set_setting_query = """
            INSERT INTO
                settings (guild_id, cog, config_name, value)
            VALUES
                (?, ?, ?, ?)
        """
        await self.db.execute_query(
            set_setting_query,
            (guild_id, cog.value, setting_name, value),
        )

    async def update_setting(
        self, guild_id: int, cog: CogSetting, setting_name: str, value: str
    ) -> None:
        """
        Updates a setting with value in a given guild and cog.

        Args:
            guild_id (int): The guild to update the setting for.
            cog (SettingsCog): The cog to update the setting for.
            setting_name (str): The setting to update set.
            value (str): The value to update it to.
        """
        update_setting_query = """
            UPDATE settings
            SET value = ?
            WHERE
                guild_id = ?
            AND
                cog = ?
            AND
                config_name = ?
        """
        await self.db.execute_query(
            update_setting_query,
            (value, guild_id, cog.value, setting_name),
        )

    async def get_setting(
        self, guild_id: int, cog: CogSetting, setting_name: str
    ) -> str | None:
        """
        Gets the value of a given setting in a given cog and guild.

        Args:
            guild_id (int): The guild to search in.
            cog (SettingsCog): The cog to get settings for.
            setting_name (str): The setting to search for.

        Returns:
            str: The value of the setting.
        """
        get_setting_query = """
            SELECT value FROM
                settings
            WHERE
                guild_id = ?
            AND
                cog = ?
            AND
                config_name = ?;
        """
        table_field = await self.db.execute_read_query(
            get_setting_query, (guild_id, cog.value, setting_name)
        )
        if not table_field:
            return None
        return str(table_field["value"])

    async def get_settings(
        self, cog: CogSetting, setting_name: str
    ) -> dict[int, str] | None:
        """
        Gets all settings for the given cog and guild.

        Args:
            cog (SettingsCog): The cog to get settings for.
            setting_name (str): The setting to get.

        Returns:
            dict[int, str]: A dict mapping guils_id to value.
        """
        get_setting_query = """
            SELECT guild_id, value FROM
                settings
            WHERE
                config_name = ?
            AND
                cog = ?
        """
        db_return = await self.db.execute_multiple_read_query(
            get_setting_query, (setting_name, cog.value)
        )
        if not db_return:
            return None
        return_dict: dict[int, str] = {}
        for setting in db_return:
            return_dict[int(setting["guild_id"])] = str(setting["value"])
        return return_dict

    async def remove_setting(
        self, guild_id: int, cog: CogSetting, setting_name: str
    ) -> None:
        """
        Removes the given setting.

        Args:
            guild_id (int): The guild to to remove the setting from.
            cog (SettingsCog): The cog to remove the setting in.
            setting_name (str): The setting to remove.
        """
        remove_setting_query = """
            DELETE FROM settings
            WHERE
                guild_id = ?
            AND
                cog = ?
            AND
                config_name = ?
        """
        await self.db.execute_query(
            remove_setting_query,
            (
                guild_id,
                cog.value,
                setting_name,
            ),
        )


if __name__ == "__main__":
    print("Creating tables if they don't exist")

    from os import getenv

    from dotenv import load_dotenv

    _ = load_dotenv()

    db_name = getenv("DB_NAME")
    db_username = getenv("DB_USERNAME")
    db_password = getenv("DB_PASSWORD")
    db_host = getenv("DB_HOST")
    db_file = getenv("DB_FILE")

    if db_name and db_username and db_password and db_host:
        print("Found and connected to postgres database")
        db = asyncio.run(
            postgres_backend.PostresqlHandler.create(
                db_name, db_username, db_password, db_host
            )
        )
    elif db_file:
        print("Found and loaded sqlite database.")
        db = sqlite_backend.SqliteHandler(db_file)
    else:
        print(
            (
                "ERROR: No database connection found, "
                "please fill in environment variables "
                "for at least one database provider."
            )
        )
        exit()

    dbHandler = DBHandler(db)
    asyncio.run(dbHandler.create_tables())
    if isinstance(dbHandler.db, postgres_backend.PostresqlHandler):
        print("Finished setting up postgress server.")
    elif isinstance(dbHandler.db, sqlite_backend.SqliteHandler):
        print("Finished setting up sqlite database.")
