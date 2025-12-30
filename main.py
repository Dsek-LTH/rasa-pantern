# -*- coding: UTF-8 -*-

import traceback
from asyncio import Event
from os import environ
from typing import override

import discord
from discord.ext import commands
from dotenv import load_dotenv

from db_handling.handler import DBHandler

_ = load_dotenv()
token = environ["TOKEN"]
db_file = environ["DB_FILE"]

# -----------------------STATIC VARS----------------------
# test guild, discord bot testing grounds
# TEST_GUILD = discord.Object(put ID of guild here)


# -----------------------MAIN CLASS-----------------------
class PanternBot(commands.Bot):
    def __init__(self, command_prefix: str) -> None:
        # Set up intents and initialize the bot.
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        self.late_load_done: Event = Event()

        self.db: DBHandler = DBHandler(db_file)
        super().__init__(
            intents=intents,
            command_prefix=command_prefix,
            description="D sektionens egna bot!",
            activity=discord.Game(name="Blockbattle"),
        )

    @override
    async def setup_hook(self) -> None:
        # Do any data processing to get data into memory here:

        # Load cogs:
        print("loading cogs:")
        early_load_extensions = [
            "cogs.drinks_handler",
            "cogs.role_sync_handler",
        ]
        for extension in early_load_extensions:
            try:
                print(f"\t{extension} begin loading")
                await bot.load_extension(extension)
                print(f"\t{extension} loaded")
            except Exception:
                print(f"Failed to load extension {extension}.")
                traceback.print_exc()

        print("done loading cogs")
        _ = self.loop.create_task(self.late_load())

    async def late_load(self) -> None:
        await self.wait_until_ready()
        print("Loading late cogs:")
        late_load_extensions = [
            "cogs.configure_drinks_handler",
            "cogs.role_sync_config_handler",
        ]
        for extension in late_load_extensions:
            try:
                print(f"\t{extension} begin loading")
                await bot.load_extension(extension)
                print(f"\t{extension} loaded")
            except Exception:
                print(f"Failed to load extension {extension}.")
                traceback.print_exc()
        print("Done loading late cogs \n")
        self.late_load_done.set()

    async def on_ready(self) -> None:
        # login, probably want to log more info here
        if self.user is None:
            # Failed login
            print("WARNING: Failed login, quitting")
            quit()

        # wait for late load to complete
        _ = await self.late_load_done.wait()

        print("-" * 100)
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("-" * 100)

        try:
            # We might want to make a command that deals with this instead.
            # Syncing on every startup is excessive and eats both time and
            # our allowed api calls.
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} command(s).")

            # Sync app commands with Discord:
            # await self.tree.sync()
            # self.tree.copy_global_to(guild=TEST_GUILD)
            # await self.tree.sync(guild=TEST_GUILD)
        except Exception as e:
            print(f"Failed to sync commands: {e}")
        print("------")


# ------------------------MAIN CODE-----------------------
bot = PanternBot(command_prefix="!")
if __name__ == "__main__":
    bot.run(token)  # Råsa Pantern
