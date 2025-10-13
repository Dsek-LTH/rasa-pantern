import typing
from typing import final, override

import discord
from discord import app_commands
from discord.ext import commands
from discord.permissions import Permissions

import db_handler
from helpers import Cog
from main import PanternBot


class ChooseDrinkView(discord.ui.View):
    # TODO: Make a custom timeout value instead.
    # The current one counts time from the last person
    # to use it instead of from when the view was created.
    def __init__(
        self,
        drink_list: list[str],
        db: db_handler.DBHandler,
        *,
        timeout: float | None = 180.0,
    ) -> None:
        self.message: discord.Message | None = None
        self._count: int = 0
        super().__init__(timeout=timeout)
        self.selector: ChooseDrinkSelector = ChooseDrinkSelector(
            drink_list, db
        )
        _ = self.add_item(self.selector)

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

    @override
    async def on_timeout(self) -> None:
        self.selector.disabled = True
        # TODO: remove debug statement
        print(self.id + " timed out")
        if self.message:
            _ = await self.message.edit(
                content="Drinks have been drunk!\n-# Total drinks: "
                + str(self._count),
                view=self,
            )


class ChooseDrinkSelector(discord.ui.Select[ChooseDrinkView]):
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
    def __init__(self, tally: dict[str, list[int]]):
        self.tally = tally
        super().__init__()

    @discord.ui.button(label="More info", style=discord.ButtonStyle.gray)
    async def further_info(
        self,
        interaction: discord.Interaction,
        _button: discord.ui.Button[typing.Self],
    ):
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

    async def check_change_drink_perms(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        # Deprecated: We will be doing this on the discord side instead
        # This will remain as a good example of how to check settings in the db
        """
        Checks if the interaction user is in the right groups
        to make this change
        """
        # Check if user is in the right groups to make this change
        # TODO: make a dict object in bot that contains setting names, cogs
        # and descriptions. Then have a new cog that deals with changing
        # settings for things. Have a setting field called change_drink_perms
        # or similar. This could be a comma separated list or similar for what
        # discord roles are allowed to change this value.
        if not interaction.guild_id or not interaction.guild:
            # If we reach this and don't have a guild id despite this
            # command being set to guild only something is very wrong...
            raise ValueError("Cannot find guild")
        if interaction.user is not discord.Member:
            raise ValueError("user not a guild member")

        allowed_roles_raw = await self.bot.db.get_setting(
            interaction.guild_id, Cog.DRINKS_HANDLER, "change_drink_perms"
        )
        if allowed_roles_raw:
            user_roles = interaction.user.roles
            for role_id in allowed_roles_raw.split():
                role = interaction.guild.get_role(int(role_id))
                if not role:
                    print(
                        f"Error role with id {role_id} doesn't exist\
                        in Guild: {interaction.guild.name}"
                    )
                if role in user_roles:
                    return True

        return False

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
        view = ChooseDrinkView(drink_list, self.bot.db, timeout=timeout)
        if not (isinstance(interaction.channel, discord.abc.Messageable)):
            # Channel is not writeable, this is not good
            raise (ValueError("channel doesn't exist, failing"))
        _ = await interaction.response.send_message("Pick a drink:", view=view)
        view.message = await interaction.original_response()

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.default_permissions(Permissions(administrator=True))
    async def configure_drinks(self, interaction: discord.Interaction) -> None:
        if not interaction.guild_id:
            # If we reach this and don't have a guild id despite this
            # command being set to guild only something is very wrong...
            raise ValueError("Cannot find guild id")
        drink_options = await self.bot.db.get_drink_option_list(
            interaction.guild_id
        )
        message_string = "These are the currently available drinks:"
        for drink_name in drink_options:
            message_string += f"\n\t- {drink_name}"
        view = ConfigureDrinksView(drink_options, self.bot.db)
        _ = await interaction.response.send_message(message_string, view=view)
        # TODO: Have it show a list of all current options and then have
        # an add and delete button at the bottom. Add gives a popup
        # where you can put in a new name, whilst remove gives you a
        # dropdown where you can select one or multiple to remove.

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
    await bot.add_cog(DrinkHandler(bot))
