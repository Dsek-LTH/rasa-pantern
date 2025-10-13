from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import db_handler
from main import PanternBot


class ChoseDrinkSelector(discord.ui.Select):
    def __init__(
        self, drink_list: list[str], db: db_handler.DBHandler
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
            placeholder="Please select your drink", options=options
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not interaction.guild_id:
            print("Guild does not exist")
            await interaction.response.send_message(
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
            await interaction.response.send_message(
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
        await interaction.response.send_message(
            f"You have selected {self.values[0]}!",
            ephemeral=True,
        )


class ChoseDrinkView(discord.ui.View):
    def __init__(
        self,
        drink_list: list[str],
        db: db_handler.DBHandler,
        *,
        timeout: Optional[float] = 180.0,
    ) -> None:
        self.message: discord.Message | None = None
        self._count: int = 0
        super().__init__(timeout=timeout)
        self.selector = ChoseDrinkSelector(drink_list, db)
        self.add_item(self.selector)

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

    async def on_timeout(self) -> None:
        self.selector.disabled = True
        # TODO: remove debug statement
        print(self.id + " timed out")
        if self.message:
            await self.message.edit(
                content="Drinks have been drunk!\n-# Total drinks: "
                + str(self._count),
                view=self,
            )


class ShowFurtherTallyView(discord.ui.View):
    def __init__(self, tally: dict[str, list[int]]):
        self.tally = tally
        super().__init__()

    @discord.ui.button(label="More info", style=discord.ButtonStyle.gray)
    async def further_info(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ):
        if not interaction.guild:
            await interaction.response.send_message(
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

        await interaction.response.send_message(
            "\n".join(message), ephemeral=True
        )


class DrinkHandler(commands.Cog):
    def __init__(self, bot: PanternBot) -> None:
        self.bot = bot
        self.ctx_tally_drinks = app_commands.ContextMenu(
            name="Tally",
            callback=self.tally_drinks_callback,
        )
        self.bot.tree.add_command(self.ctx_tally_drinks)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(
            self.ctx_tally_drinks.name, type=self.ctx_tally_drinks.type
        )

    @app_commands.command()
    @app_commands.guild_only()
    async def drink(
        self, interaction: discord.Interaction, timeout: int = 0
    ) -> None:
        """
        Sends a tally for users to select what drink they had at an event.

        Args:
            interaction (discord.Interaction): The interaction object passed
                                               from calling this.
            timeout (int): Optional, the amount of seconds before
                           the interaction will time out and disable itself.
        """
        if not interaction.guild_id:
            # If we reach this and don't have a guild id despite this
            # command being set to guild only something is very wrong...
            raise ValueError("Cannot find guild id")

        drink_list = await self.bot.db.get_drink_option_list(
            interaction.guild_id
        )
        view = ChoseDrinkView(drink_list, self.bot.db, timeout=timeout)
        if not (isinstance(interaction.channel, discord.abc.Messageable)):
            # Channel is not writeable, this is not good
            raise (ValueError("channel doesn't exist, failing"))
        await interaction.response.send_message("Pick a drink:", view=view)
        view.message = await interaction.original_response()

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
            await interaction.response.send_message(
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

        await interaction.response.send_message(
            "\n".join(content), view=ShowFurtherTallyView(drink_tally)
        )


# ----------------------MAIN PROGRAM----------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions().
async def setup(bot: PanternBot) -> None:
    print("\tcogs.drinks_handler begin loading")
    await bot.add_cog(DrinkHandler(bot))
