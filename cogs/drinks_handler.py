from __future__ import annotations

import typing
from typing import final, override

import discord
from discord import app_commands
from discord.ext import commands

import db_handler
from main import PanternBot


class ChooseDrinkView(discord.ui.View):
    # TODO: Make a custom timeout value.
    def __init__(
        self,
        message_id: int,
        guild_id: int,
        drink_list: list[str],
        db: db_handler.DBHandler,
    ) -> None:
        # Having this field is kind of ugly now that we keep the message_id,
        # but I can't be arsed to fix it rn.
        self.message: discord.Message | None = None
        self.message_id: int = message_id
        self.db: db_handler.DBHandler = db
        self._count: int = 0
        super().__init__(timeout=None)
        selector: ChooseDrinkSelector = ChooseDrinkSelector(
            message_id, guild_id, drink_list, db
        )
        self.selector: ChooseDrinkSelector = selector
        _ = self.add_item(selector)

    @classmethod
    async def create(
        cls, message_id: int, guild_id: int, db: db_handler.DBHandler
    ) -> ChooseDrinkView:
        drink_list = await db.get_drink_option_list(guild_id)
        return ChooseDrinkView(message_id, guild_id, drink_list, db)

    async def increment_count(self) -> None:
        """
        Increments the amount of drinks had in this poll.
        """
        self._count += 1

    async def decrement_count(self) -> None:
        """
        Decrement the amount of drinks had in this poll.
        """
        self._count -= 1

    async def remove(self) -> None:
        self.selector.disabled = True
        # TODO: remove debug statement
        print(self.id + " timed out")
        if self.message:
            _ = await self.message.edit(
                content="Drinks have been drunk!\n-# Total drinks: "
                + str(self._count),
                view=self,
            )
        await self.db.remove_tally(self.message_id)


class ChooseDrinkSelector(discord.ui.Select[ChooseDrinkView]):
    def __init__(
        self,
        message_id: int,
        guild_id: int,
        drink_list: list[str],
        db: db_handler.DBHandler,
    ) -> None:
        self.db: db_handler.DBHandler = db
        options = [
            discord.SelectOption(
                label="nothing",
                value="nothing",
                default=True,
            )
        ]

        for drink in drink_list:
            options.append(discord.SelectOption(label=drink, value=drink))
        super().__init__(
            placeholder="Please select your drink",
            options=options,
            custom_id=f"tally-{message_id}-{guild_id}",
        )

    @override
    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild_id:
            print("Guild does not exist")
            _ = await interaction.response.send_message(
                "ERROR, failed to find guild, please contact an admin"
            )
            return
        if not self.view:
            raise (
                ReferenceError("This should actually be impossible to reach")
            )
        if not self.view.message:
            print(
                "Message does not exist in guild " + str(interaction.guild_id)
            )
            _ = await interaction.response.send_message(
                "ERROR, failed to find message, please contact an admin"
            )
            return

        if self.values[0] == "nothing":
            await self.db.remove_drunk_drink(
                interaction.guild_id, self.view.message.id, interaction.user.id
            )
            await self.view.decrement_count()
        else:
            edited = await self.db.set_drunk_drink(
                interaction.guild_id,
                self.view.message.id,
                interaction.user.id,
                self.values[0],
            )
            if edited:
                await self.view.increment_count()
        _ = await interaction.response.send_message(
            f"You have selected {self.values[0]}!",
            ephemeral=True,
        )


@final
class ShowFurtherTallyView(discord.ui.View):
    def __init__(self, tally: dict[str, list[int]]) -> None:
        self.tally = tally
        super().__init__()

    @discord.ui.button(label="More info", style=discord.ButtonStyle.gray)
    async def further_info(
        self,
        interaction: discord.Interaction,
        _button: discord.ui.Button[typing.Self],
    ) -> None:
        if not interaction.guild:
            _ = await interaction.response.send_message(
                "Could not find guild, please contact an admin"
            )
            raise ValueError("Could not find guild")

        message = ["Here is what everyone had to drink:", "```"]
        for drink_name in self.tally:
            message.append(drink_name + ":")
            for user_id in self.tally[drink_name]:
                user = interaction.guild.get_member(user_id)
                if user:
                    message.append(f"    - {user.display_name} ({user.id})")
                else:
                    message.append(f"    - unknown ({user_id})")

        message.append("```")

        _ = await interaction.response.send_message(
            "\n".join(message), ephemeral=True
        )


@final
class DrinkHandler(commands.Cog):
    def __init__(self, bot: PanternBot) -> None:
        self.bot = bot
        self.ctx_tally_drinks = app_commands.ContextMenu(
            name="Tally",
            callback=self.tally_drinks_callback,
        )
        self.bot.tree.add_command(self.ctx_tally_drinks)

    @override
    async def cog_unload(self) -> None:
        _ = self.bot.tree.remove_command(
            self.ctx_tally_drinks.name, type=self.ctx_tally_drinks.type
        )

    @app_commands.command()
    @app_commands.guild_only()
    async def drink(self, interaction: discord.Interaction) -> None:
        """
        Sends a tally for users to select what drink they had at an event.

        Args:
            interaction (discord.Interaction): The interaction object passed
                                               from calling this.
        """
        if not interaction.guild_id:
            # If we reach this and don't have a guild id despite this
            # command being set to guild only something is very wrong...
            raise ValueError("Cannot find guild id")

        if not (isinstance(interaction.channel, discord.abc.Messageable)):
            # Channel is not writeable, this is not good
            raise (ValueError("channel doesn't exist, failing"))
        _ = await interaction.response.send_message("Pick a drink:")
        message = await interaction.original_response()
        view = await ChooseDrinkView.create(
            message.id, interaction.guild_id, self.bot.db
        )
        updated_message = await message.edit(view=view)
        view.message = updated_message
        await self.bot.db.create_tally(
            updated_message.id, interaction.guild_id
        )

    @app_commands.guild_only()
    async def tally_drinks_callback(
        self, interaction: discord.Interaction, message: discord.Message
    ) -> None:
        """
        Tallies the amount of people who clicked a message.

        Args:
            interaction (discord.Interaction): Context to run in.
            message (discord.Message): The drink tally message to get info for.
        """
        if not message.guild:
            _ = await interaction.response.send_message(
                "Guild could not be found, please contact an admin",
                ephemeral=True,
            )
            return

        drink_tally = await self.bot.db.get_tally(message.id, message.guild.id)

        drink_count = 0
        content = ["```"]
        for drink in drink_tally:
            drink_count += len(drink_tally[drink])
            content.append(f"{drink}: {len(drink_tally[drink])}")

        content.insert(0, f"Total drinks drunk: {drink_count}")
        if drink_count == 0:
            content = ["Nobody logged anything with this tally."]
        else:
            content.append("```")

        _ = await interaction.response.send_message(
            "\n".join(content), view=ShowFurtherTallyView(drink_tally)
        )


# ----------------------MAIN PROGRAM----------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions().
async def setup(bot: PanternBot) -> None:
    print("\tcogs.drinks_handler begin loading")
    print("\t\tloading tallies from database:")
    tallies = await bot.db.get_all_tallies()
    for message_id, guild_id in tallies:
        print(f"\t\t\tloading tally in message: {message_id}")
        bot.add_view(
            await ChooseDrinkView.create(message_id, guild_id, bot.db)
        )
    if not tallies:
        print("\t\t\tNo tallies in db!")
    await bot.add_cog(DrinkHandler(bot))
