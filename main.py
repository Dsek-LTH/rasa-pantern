# -*- coding: UTF-8 -*-
import traceback
from os import environ

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
token = environ["TOKEN"]

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
        super().__init__(
            intents=intents,
            command_prefix=command_prefix,
            description="D sektionens egna bot!",
            activity=discord.Game(
                name="Blockbattle"))

    async def on_ready(self) -> None:
        # login, probably want to log more info here
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        try:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} command(s).")
        except Exception as e:
            print(f"Failed to sync commands: {e}")
        print('------')

    async def setup_hook(self) -> None:
        # Do any data processing to get data into memory here:

        # Load cogs:
        print("loading cogs:")
        extensions = [
            'cogs.drinks_handler'
        ]

        for extension in extensions:
            try:
                await bot.load_extension(extension)
                print(f"\t{extension} loaded")
            except Exception as e:
                print(f'Failed to load extension {extension}.')
                traceback.print_exc()

        # Sync app commands with Discord:
        # await self.tree.sync()
        # self.tree.copy_global_to(guild=TEST_GUILD)
        # await self.tree.sync(guild=TEST_GUILD)


# ------------------------MAIN CODE-----------------------
bot = PanternBot(command_prefix="!")
if __name__ == "__main__":
    bot.run(token)  # Råsa Pantern
