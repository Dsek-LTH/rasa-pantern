from __future__ import annotations

from typing import final, override

import discord
from discord import (
    InteractionMessage,
    PartialMessage,
    Permissions,
    abc,
    app_commands,
    ui,
)
from discord.ext import commands

from db_handling.handler import DBHandler
from helpers import CogSetting
from main import PanternBot


class ConfigureDrinksView(ui.LayoutView):
    def __init__(
        self,
        guild_id: int,
        drink_list: list[str],
        db: DBHandler,
    ):
        super().__init__(timeout=None)
        self.guild_id: int = guild_id
        self.drink_list: list[str] = drink_list
        self.db: DBHandler = db
        self.message: InteractionMessage | PartialMessage | None = None

        self.text: ui.TextDisplay[ConfigureDrinksView] = ui.TextDisplay(
            content=_get_drink_string(self.drink_list)
        )

        self.add_button: ui.Button[ConfigureDrinksView] = ui.Button(
            label="Add drink",
            style=discord.ButtonStyle.green,
            custom_id=f"{self.guild_id}ConfigureDrinksViewAddDrink",
        )
        self.add_button.callback = self.add_drink_button

        self.remove_button: ui.Button[ConfigureDrinksView] = ui.Button(
            label="Remove drink",
            style=discord.ButtonStyle.danger,
            custom_id=f"{self.guild_id}ConfigureDrinksViewRemoveDrink",
        )
        self.remove_button.callback = self.remove_drink_button

        self.row: ui.ActionRow[ConfigureDrinksView] = ui.ActionRow()
        _ = self.row.add_item(self.add_button).add_item(self.remove_button)

        _ = self.add_item(self.text).add_item(self.row)

    async def add_drink_button(
        self,
        interaction: discord.Interaction,
    ):
        _ = await interaction.response.send_modal(AddDrinkModal(self))

    async def remove_drink_button(
        self,
        interaction: discord.Interaction,
    ):
        _ = await interaction.response.send_modal(
            RemoveDrinkModal(self, self.drink_list)
        )

    async def update_drink_list(self):
        assert self.message

        self.drink_list = await self.db.get_drink_option_list(self.guild_id)
        self.text.content = _get_drink_string(self.drink_list)
        _ = await self.message.edit(view=self)

    @classmethod
    async def create(cls, guild_id: int, db: DBHandler):
        drink_list = await db.get_drink_option_list(guild_id)
        return ConfigureDrinksView(guild_id, drink_list, db)

    @classmethod
    async def create_deactivated(
        cls, message: PartialMessage, guild_id: int, db: DBHandler
    ):
        drink_list = await db.get_drink_option_list(guild_id)
        view = ConfigureDrinksView(guild_id, drink_list, db)
        view.message = message
        view.remove_button.disabled = True
        view.add_button.disabled = True
        view.stop()
        return view


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
        if (
            self.name.component.value
            in await self.drinks_view.db.get_drink_option_list(
                self.drinks_view.guild_id
            )
        ):
            _ = await interaction.response.send_message(
                f"{self.name.component.value} already exists in the list."
            )
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
        self.large_input: bool = False

        if len(self.drinks_list) > 25:
            self.large_input = True
            # For some reason ui.TextDisplay can't have ui.Modal as a generic,
            # so we're just ignoring typing here. Lessgo python
            self.long_list: ui.TextDisplay = ui.TextDisplay(  # pyright: ignore
                _get_drink_string(drinks_list)
            )
            self.input_name: ui.Label[RemoveDrinkModal] = ui.Label(
                text="What drink would you like to remove",
                component=ui.TextInput(placeholder="name"),
            )
            _ = self.add_item(self.long_list)  # pyright: ignore
            _ = self.add_item(self.input_name)
        else:
            self.select_name: ui.Label[RemoveDrinkModal] = ui.Label(
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
            _ = self.add_item(self.select_name)

    @override
    async def on_submit(self, interaction: discord.Interaction):
        assert self.drinks_view.message
        value: str
        if self.large_input:
            assert isinstance(self.input_name.component, ui.TextInput)
            value = self.input_name.component.value
        else:
            assert isinstance(self.select_name.component, ui.Select)
            value = self.select_name.component.values[0]

        await self.drinks_view.db.remove_drink_option(
            self.drinks_view.guild_id, value
        )
        _ = await interaction.response.send_message(
            f"Removing {value} from the list of drinks!",
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
            CogSetting.CONFIGURE_DRINKS_HANDLER,
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
        assert interaction.guild
        assert interaction.guild_id

        view: ConfigureDrinksView = await ConfigureDrinksView.create(
            interaction.guild_id, self.bot.db
        )
        _ = await interaction.response.send_message(view=view)
        view.message = await interaction.original_response()

        old_config = await self.bot.db.get_setting(
            interaction.guild_id,
            CogSetting.CONFIGURE_DRINKS_HANDLER,
            "config_message",
        )
        if old_config:
            channel_id, message_id = map(int, old_config.split("|"))
            channel = interaction.guild.get_channel_or_thread(channel_id)
            if isinstance(channel, abc.Messageable):
                message = channel.get_partial_message(message_id)
                # WARN: This doesn't properly remove the existing class afaik,
                # which in theory could lead to memory leaks. But then again...
                # It's python.
                old_view: ConfigureDrinksView = (
                    await ConfigureDrinksView.create_deactivated(
                        message, interaction.guild_id, self.bot.db
                    )
                )
                _ = await message.edit(view=old_view)

            await self.bot.db.update_setting(
                interaction.guild_id,
                CogSetting.CONFIGURE_DRINKS_HANDLER,
                "config_message",
                f"{interaction.channel_id}|{view.message.id}",
            )
        else:
            await self.bot.db.set_setting(
                interaction.guild_id,
                CogSetting.CONFIGURE_DRINKS_HANDLER,
                "config_message",
                f"{interaction.channel_id}|{view.message.id}",
            )


def _get_drink_string(drink_list: list[str]) -> str:
    message = ["These are the currently available drinks", "```"]
    for drink_name in drink_list:
        message.append(f" - {drink_name}")
    message.append("```")
    return "\n".join(message)


# ----------------------MAIN PROGRAM----------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions().
async def setup(bot: PanternBot) -> None:
    print("\t\tloading config from database:")
    # Holds guild_id and a string id with <channel_id>|<message_id>
    settings = await bot.db.get_settings(
        CogSetting.CONFIGURE_DRINKS_HANDLER, "config_message"
    )
    if settings:
        for guild_id in settings:
            guild = bot.get_guild(guild_id)
            print(f"\t\t\t loaded config for guild: {guild}, id: {guild_id}")
            view = await ConfigureDrinksView.create(guild_id, bot.db)
            if guild:
                channel_id, message_id = map(
                    int, settings[guild_id].split("|")
                )
                channel = guild.get_channel_or_thread(channel_id)
                if isinstance(channel, abc.Messageable):
                    view.message = channel.get_partial_message(message_id)

            bot.add_view(view)
    else:
        print("\t\t\t no config entries in database!")

    await bot.add_cog(ConfigureDrinksHandler(bot))
