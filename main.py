# -*- coding: UTF-8 -*-
import traceback
from os import environ
from typing import override

import discord
from discord.ext import commands
from dotenv import load_dotenv

import db_handler

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

        self.db: db_handler.DBHandler = db_handler.DBHandler(db_file)
        super().__init__(
            intents=intents,
            command_prefix=command_prefix,
            description="D sektionens egna bot!",
            activity=discord.Game(name="Blockbattle"),
        )

    async def on_ready(self) -> None:
        # login, probably want to log more info here
        if self.user is None:
            # Failed login
            print("WARNING: Failed login, quitting")
            quit()

        print(f"Logged in as {self.user} (ID: {self.user.id})")
        try:
            # We might want to make a command that deals with this instead.
            # Syncing on every startup is excessive and eats both time and
            # our allowed api calls.
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} command(s).")
        except Exception as e:
            print(f"Failed to sync commands: {e}")
        print("------")

    @override
    async def setup_hook(self) -> None:
        # Do any data processing to get data into memory here:

        # Load cogs:
        print("loading cogs:")
        extensions = [
            "cogs.drinks_handler",
            "cogs.configure_drinks_handler",
        ]
        for extension in extensions:
            try:
                await bot.load_extension(extension)
                print(f"\t{extension} loaded")
            except Exception:
                print(f"Failed to load extension {extension}.")
                traceback.print_exc()

        # Sync app commands with Discord:
        # await self.tree.sync()
        # self.tree.copy_global_to(guild=TEST_GUILD)
        # await self.tree.sync(guild=TEST_GUILD)


# ------------------------MAIN CODE-----------------------
bot = PanternBot(command_prefix="!")
if __name__ == "__main__":
    bot.run(token)  # Råsa Pantern
