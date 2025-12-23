from __future__ import annotations

from typing import final, override

import discord
from discord import InteractionMessage, Permissions, app_commands, ui
from discord.ext import commands

import db_handler
from helpers import SettingsCog
from main import PanternBot


class ConfigureDrinksView(ui.LayoutView):
    def __init__(
        self,
        guild_id: int,
        drink_list: list[str],
        db: db_handler.DBHandler,
    ):
        super().__init__()
        self.guild_id: int = guild_id
        self.drink_list: list[str] = drink_list
        self.db: db_handler.DBHandler = db

        self.text: ui.TextDisplay[ConfigureDrinksView] = ui.TextDisplay(
            content=self._get_drink_string(self.drink_list)
        )

        _ = self.add_item(self.text)

        # fields defined in init are always assinged last. Here we flip the
        # buttons to be after the text. This is kinda sketchy, but it works!
        self._children.append(self._children.pop(0))
        self.message: InteractionMessage | None = None

    row: ui.ActionRow[ConfigureDrinksView] = ui.ActionRow()

    @row.button(label="Add drink", style=discord.ButtonStyle.green)
    async def add_drink_button(
        self,
        interaction: discord.Interaction,
        _button: ui.Button[ConfigureDrinksView],
    ):
        _ = await interaction.response.send_modal(AddDrinkModal(self))

    @row.button(label="Remove drink", style=discord.ButtonStyle.danger)
    async def remove_drink_button(
        self,
        interaction: discord.Interaction,
        _button: ui.Button[ConfigureDrinksView],
    ):
        _ = await interaction.response.send_modal(
            RemoveDrinkModal(self, self.drink_list)
        )

    def _get_drink_string(self, drink_list: list[str]) -> str:
        message = ["These are the currently available drinks", "```"]
        for drink_name in drink_list:
            message.append(f" - {drink_name}")
        message.append("```")
        return "\n".join(message)

    async def update_drink_list(self):
        assert self.message
        self.drink_list = await self.db.get_drink_option_list(self.guild_id)
        self.text.content = self._get_drink_string(self.drink_list)
        _ = await self.message.edit(view=self)

    @classmethod
    async def create(cls, guild_id: int, db: db_handler.DBHandler):
        drink_list = await db.get_drink_option_list(guild_id)
        return ConfigureDrinksView(guild_id, drink_list, db)


class AddDrinkModal(ui.Modal, title="add drink"):
    def __init__(self, drinks_view: ConfigureDrinksView):
        super().__init__()
        self.drinks_view: ConfigureDrinksView = drinks_view

    name: ui.Label[AddDrinkModal] = ui.Label(
        text="What drink would you like to add",
        component=ui.TextInput(placeholder="name"),
    )

    @override
    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.name.component, ui.TextInput)
        # TODO: Check for duplicate drinks here
        await self.drinks_view.db.add_drink_option(
            self.drinks_view.guild_id, self.name.component.value
        )
        _ = await interaction.response.send_message(
            f"Adding {self.name.component.value} to the list of drinks!",
            ephemeral=True,
        )
        await self.drinks_view.update_drink_list()


class RemoveDrinkModal(ui.Modal, title="remove drink"):
    def __init__(
        self, drinks_view: ConfigureDrinksView, drinks_list: list[str]
    ):
        super().__init__()
        self.drinks_view: ConfigureDrinksView = drinks_view
        self.drinks_list: list[str] = drinks_list

        # TODO: Make sure that we don't have more than 25 drinks, and in that
        # case do something else (like a textInput for example)
        self.name: ui.Label[AddDrinkModal] = ui.Label(
            text="What drink would you like to remove",
            component=ui.Select(
                placeholder="select a drink",
                options=[
                    discord.SelectOption(label=name, value=name)
                    for name in self.drinks_list
                ],
                max_values=1,
            ),
        )
        _ = self.add_item(self.name)

    @override
    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.name.component, ui.Select)
        await self.drinks_view.db.remove_drink_option(
            self.drinks_view.guild_id, self.name.component.values[0]
        )
        _ = await interaction.response.send_message(
            f"Removing {self.name.component.values[0]} from the list of drinks!",
            ephemeral=True,
        )
        await self.drinks_view.update_drink_list()


@final
class ConfigureDrinksHandler(commands.Cog):

    def __init__(self, bot: PanternBot) -> None:
        self.bot = bot

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
            interaction.guild_id,
            SettingsCog.DRINKS_HANDLER,
            "change_drink_perms",
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
    @app_commands.default_permissions(Permissions(administrator=True))
    async def configure_drinks(self, interaction: discord.Interaction) -> None:
        if not interaction.guild_id:
            # If we reach this and don't have a guild id despite this
            # command being set to guild only something is very wrong...
            raise ValueError("Cannot find guild id")

        view: ConfigureDrinksView = await ConfigureDrinksView.create(
            interaction.guild_id, self.bot.db
        )
        _ = await interaction.response.send_message(view=view)
        view.message = await interaction.original_response()
        # TODO: Have it show a list of all current options and then have
        # an add and delete button at the bottom. Add gives a popup
        # where you can put in a new name, whilst remove gives you a
        # dropdown where you can select one or multiple to remove.


# ----------------------MAIN PROGRAM----------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions().
async def setup(bot: PanternBot) -> None:
    print("\tcogs.configure_drinks_handler begin loading")
    await bot.add_cog(ConfigureDrinksHandler(bot))
