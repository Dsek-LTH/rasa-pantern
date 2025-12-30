from __future__ import annotations

from typing import final, override

import discord
from discord import (
    Client,
    Interaction,
    Message,
    PartialMessage,
    Permissions,
    app_commands,
    ui,
)
from discord.abc import GuildChannel, Messageable
from discord.ext import commands

from db_handling.handler import DBHandler
from helpers import CogSetting, RoleMapping
from main import PanternBot


class RoleConfigView(ui.LayoutView):
    def __init__(self, db: DBHandler, role_map: RoleMapping) -> None:
        super().__init__(timeout=None)
        self.message: Message | PartialMessage | None = None
        self.db: DBHandler = db
        self.role_map: RoleMapping = role_map

        self.edit_discord_role_button: ui.Button[RoleConfigView] = ui.Button[
            RoleConfigView
        ](
            style=discord.ButtonStyle.grey,
            label="Edit Discord role",
            custom_id=(
                "RCV-edit-discord-btn-"
                f"{role_map.discord_role_id}{role_map.role_id}"
            )[:100],
        )
        self.edit_discord_role_button.callback = self.edit_discord_id_callback

        self.edit_external_role_button: ui.Button[RoleConfigView] = ui.Button[
            RoleConfigView
        ](
            style=discord.ButtonStyle.grey,
            label="Edit external role",
            custom_id=(
                "RCV-edit-external-btn-"
                f"{role_map.discord_role_id}{role_map.role_id}"
            )[:100],
        )
        self.edit_external_role_button.callback = (
            self.edit_external_id_callback
        )

        self.container: ui.Container[RoleConfigView] = ui.Container(
            ui.TextDisplay(
                (
                    (
                        "mapping discord role "
                        f"<@&{self.role_map.discord_role_id}> "
                        f"to other role: `{self.role_map.role_id}`."
                    )
                    if self.role_map
                    else "Please wait a second"
                ),
                id=1,
            ),
            ui.ActionRow[RoleConfigView](
                self.edit_discord_role_button, self.edit_external_role_button
            ),
            # D-guild pink (#F280A1):
            accent_colour=discord.Colour(15892641),
        )
        #  .callback = edit_discord_id
        _ = self.add_item(self.container)

        self.delete_role_mapping_button: ui.Button[RoleConfigView] = ui.Button[
            RoleConfigView
        ](
            style=discord.ButtonStyle.danger,
            label="Delete config mapping",
            custom_id=(
                "RCV-edit-delete-btn-"
                f"{role_map.discord_role_id}{role_map.role_id}"
            )[:100],
        )
        self.delete_role_mapping_button.callback = (
            self.delete_role_mapping_callback
        )

        self.delete_row: ui.ActionRow[RoleConfigView] = discord.ui.ActionRow(
            self.delete_role_mapping_button
        )
        _ = self.add_item(self.delete_row)

    async def edit_discord_id_callback(
        self, interaction: discord.Interaction
    ) -> None:
        assert interaction.guild
        assert self.role_map
        discord_role = interaction.guild.get_role(
            self.role_map.discord_role_id
        )
        discord_role_modal: ui.Modal = ui.Modal(title="Edit discord role")
        role_select: ui.RoleSelect[RoleConfigView] = ui.RoleSelect(
            required=True,
            placeholder=(discord_role.name if discord_role else "NULL"),
        )

        _ = discord_role_modal.add_item(
            ui.Label(text="Set discord role", component=role_select)
        )
        discord_role_modal.on_submit = (
            lambda interaction: self.set_discord_role(interaction, role_select)
        )

        _ = await interaction.response.send_modal(discord_role_modal)

    async def edit_external_id_callback(
        self, interaction: discord.Interaction
    ) -> None:
        assert self.role_map
        external_role_modal: ui.Modal = ui.Modal(title="Edit external role")
        text_input: ui.TextInput[RoleConfigView] = ui.TextInput(
            label="Set external role",
            placeholder=self.role_map.role_id,
            id=11,
        )
        _ = external_role_modal.add_item(text_input)

        external_role_modal.on_submit = (
            lambda interaction: self.set_external_role(interaction, text_input)
        )
        _ = await interaction.response.send_modal(external_role_modal)

    async def delete_role_mapping_callback(
        self, interaction: discord.Interaction
    ) -> None:
        confirm_delete_modal: ui.Modal = ui.Modal(title="Confirm deletion")
        _ = confirm_delete_modal.add_item(
            ui.TextDisplay(
                content=(
                    "Warning, this will remove this role config, "
                    "are you sure you want to do that?"
                )
            )
        )
        confirm_delete_modal.on_submit = self.remove_role_mapping
        _ = await interaction.response.send_modal(confirm_delete_modal)

    async def set_discord_role(
        self,
        interaction: Interaction,
        role_select: ui.RoleSelect[RoleConfigView],
    ) -> None:
        # TODO: Make sure we can't make two identical mappings
        # AKA, make sure to check the db for duplicates before we write to it
        assert self.role_map
        self.role_map.discord_role_id = role_select.values[0].id
        _ = await interaction.response.defer()
        await self.update_role_map()

    async def set_external_role(
        # TODO: Make sure we can't make two identical mappings
        # AKA, make sure to check the db for duplicates before we write to it
        self,
        interaction: Interaction,
        text_input: ui.TextInput[RoleConfigView],
    ) -> None:
        assert self.role_map
        self.role_map.role_id = text_input.value
        _ = await interaction.response.defer()
        await self.update_role_map()

    async def remove_role_mapping(self, interaction: Interaction) -> None:
        assert self.message
        assert self.role_map
        _ = await self.db.delete_role_config(self.message.id)
        _ = await self.message.delete()
        _ = await interaction.response.send_message(
            (
                "Removed role_mapping for "
                f"<@&{self.role_map.discord_role_id}> "
                f"linking to {self.role_map.role_id}."
            ),
            ephemeral=True,
        )

    async def set_role_map(self, role_map: RoleMapping) -> None:
        self.role_map = role_map
        await self.update_role_map()

    async def set_message(self, message: Message) -> None:
        self.message = message
        _ = await self.message.edit(view=self)

    async def update_role_map(self) -> None:
        textDisplay = self.container.find_item(1)
        assert self.role_map
        assert self.message
        assert isinstance(textDisplay, ui.TextDisplay)
        await self.db.update_role_config(
            self.message.id,
            self.role_map.role_id,
            self.role_map.discord_role_id,
        )

        self.edit_discord_role_button.custom_id = (
            "RCV-edit-discord-btn-"
            f"{self.role_map.discord_role_id}{self.role_map.role_id}"
        )[:100]

        self.edit_external_role_button.custom_id = (
            "RCV-edit-external-btn-"
            f"{self.role_map.discord_role_id}{self.role_map.role_id}"
        )[:100]

        self.delete_role_mapping_button.custom_id = (
            "RCV-edit-delete-btn-"
            f"{self.role_map.discord_role_id}{self.role_map.role_id}"
        )[:100]

        textDisplay.content = (
            f"mapping discord role <@&{self.role_map.discord_role_id}> "
            f"to other role: `{self.role_map.role_id}`."
        )
        _ = await self.message.edit(view=self)

    @classmethod
    async def create(cls, db: DBHandler, message_id: int) -> RoleConfigView:
        roleMap = await db.get_role_config(message_id)
        assert roleMap
        return RoleConfigView(db, roleMap)

    @classmethod
    async def createStopped(cls, db: DBHandler, role_map: RoleMapping) -> None:
        view: RoleConfigView = RoleConfigView(db, role_map)
        # TODO: remove all buttons (if we even want to use it. It is not in use
        # currently)
        view.stop()


class SetupChannelModal(ui.Modal, title="Set up role sync config channel"):
    def __init__(self, db: DBHandler) -> None:
        super().__init__()
        self.db: DBHandler = db

    channel: ui.Label[SetupChannelModal] = ui.Label(
        text="Where do you want to configure the roles?",
        component=ui.ChannelSelect(
            required=True,
            placeholder="Config Channel",
            channel_types=[discord.ChannelType.text],
        ),
    )

    @override
    async def on_submit(self, interaction: discord.Interaction) -> None:
        assert interaction.guild_id
        assert not await self.db.get_setting(
            interaction.guild_id,
            CogSetting.ROLE_SYNC_CONFIG_HANDLER,
            "config_channel_id",
        )
        assert isinstance(self.channel.component, ui.ChannelSelect)
        _ = await self.db.set_setting(
            interaction.guild_id,
            CogSetting.ROLE_SYNC_CONFIG_HANDLER,
            "config_channel_id",
            str(self.channel.component.values[0].id),
        )
        _ = await interaction.response.send_message(
            (
                "Successfully set "
                f"<#{self.channel.component.values[0].id}> "
                "as config channel"
            )
        )


class AddRoleConfig(ui.Modal, title="Add role config"):
    def __init__(self, db: DBHandler) -> None:
        super().__init__()
        self.db: DBHandler = db

    discord_role: ui.Label[AddRoleConfig] = ui.Label(
        text="What discord role do you want to link?",
        component=ui.RoleSelect(required=True, placeholder="Discord role"),
    )

    role: ui.Label[AddRoleConfig] = ui.Label(
        text="What external role should it be linked to?",
        component=ui.TextInput(placeholder="Other role id"),
    )

    @override
    async def on_submit(self, interaction: discord.Interaction) -> None:
        assert interaction.guild
        assert isinstance(self.discord_role.component, ui.RoleSelect)
        assert isinstance(self.role.component, ui.TextInput)
        channel_id = await self.db.get_setting(
            interaction.guild.id,
            CogSetting.ROLE_SYNC_CONFIG_HANDLER,
            "config_channel_id",
        )
        if not channel_id:
            _ = interaction.response.send_message(
                (
                    "There is no config channel set up for this server, "
                    "please ask an administrator to run the setup command."
                ),
                ephemeral=True,
            )
            return
        channel = interaction.guild.get_channel_or_thread(int(channel_id))
        if not isinstance(channel, GuildChannel):
            _ = interaction.response.send_message(
                (
                    "Error whilst trying to find channel,"
                    "please contact an admin."
                ),
                ephemeral=True,
            )
            print(
                (
                    "Error in AddRoleConfig whilst trying to get channel. "
                    f"Got {type(channel)} but was expecting GuildChannel."
                )
            )
            return
        assert isinstance(channel, Messageable)
        role_map = RoleMapping(
            self.role.component.value,
            self.discord_role.component.values[0].id,
            interaction.guild.id,
        )
        view = RoleConfigView(self.db, role_map)
        message = await channel.send(view=view)
        await view.set_message(message)

        _ = await self.db.create_role_config(
            message.id,
            channel.id,
            self.role.component.value,
            self.discord_role.component.values[0].id,
            interaction.guild.id,
        )
        _ = await interaction.response.defer()


@final
class RoleSyncConfigHandler(commands.Cog):
    def __init__(self, bot: PanternBot) -> None:
        super().__init__()
        self.bot = bot

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.default_permissions(Permissions(administrator=True))
    # TODO: write description
    async def initialize_role_sync_config(
        self, interaction: discord.Interaction
    ) -> None:
        assert interaction.guild_id
        config_channel_id = await self.bot.db.get_setting(
            interaction.guild_id,
            CogSetting.ROLE_SYNC_CONFIG_HANDLER,
            "config_channel_id",
        )
        if config_channel_id:
            # TODO: Make the user have to confirm by typing something here,
            # just for a bit more safety. Maybe spin this out to it's own
            # class.
            modal = ui.Modal(title="Warning")
            _ = modal.add_item(
                ui.TextDisplay(
                    content=(
                        "You have already configured this feature. "
                        "Continuing will remove all existing role configs. "
                        "Make sure that you know what you are doing before "
                        "you do."
                    ),
                )
            )
            modal.on_submit = self.reset_configs
            _ = await interaction.response.send_modal(modal)
            return

        _ = await interaction.response.send_modal(
            SetupChannelModal(self.bot.db)
        )

    async def reset_configs(
        self, interaction: discord.Interaction[Client]
    ) -> None:
        assert interaction.guild
        old_channel_id = await self.bot.db.get_setting(
            interaction.guild.id,
            CogSetting.ROLE_SYNC_CONFIG_HANDLER,
            "config_channel_id",
        )
        assert old_channel_id

        await self.bot.db.remove_setting(
            interaction.guild.id,
            CogSetting.ROLE_SYNC_CONFIG_HANDLER,
            "config_channel_id",
        )
        mappings: list[RoleMapping] = await self.bot.db.get_guild_role_configs(
            interaction.guild.id
        )
        channel = interaction.guild.get_channel_or_thread(int(old_channel_id))
        if channel:
            assert isinstance(channel, Messageable)
            for mapping in mappings:
                if mapping.message_id:
                    _ = await channel.get_partial_message(
                        mapping.message_id
                    ).delete()

        await self.bot.db.purge_role_configs(interaction.guild.id)
        _ = await interaction.response.send_message(
            (
                "Config channel and all Role sync mappings have been purged.\n"
                "Please use this command again to re-configure role sync."
            ),
        )

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.default_permissions(Permissions(administrator=True))
    # TODO: write description
    # TODO: Make sure we can't make two identical mappings
    async def create_role_mapping(
        self, interaction: discord.Interaction
    ) -> None:
        assert interaction.guild_id
        config_channel_id = await self.bot.db.get_setting(
            interaction.guild_id,
            CogSetting.ROLE_SYNC_CONFIG_HANDLER,
            "config_channel_id",
        )
        if not config_channel_id:
            _ = await interaction.response.send_message(
                "Please run /initialize_role_sync_config to set up the bot",
                ephemeral=True,
            )
            return

        if not interaction.channel_id == int(config_channel_id):
            _ = await interaction.response.send_message(
                (
                    "This is not a role config channel, "
                    f"please configure the bot in <#{config_channel_id}>."
                ),
                ephemeral=True,
            )
            return

        _ = await interaction.response.send_modal(AddRoleConfig(self.bot.db))


# ----------------------MAIN PROGRAM----------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions().
async def setup(bot: PanternBot) -> None:
    role_mappings = await bot.db.get_all_role_configs()
    for mapping in role_mappings:
        assert mapping.channel_id
        assert mapping.message_id
        view = RoleConfigView(bot.db, mapping)
        guild = bot.get_guild(mapping.guild_id)
        if not guild:
            try:
                guild = await bot.fetch_guild(mapping.guild_id)
            except discord.NotFound:
                print(
                    (
                        f"guild with ID: {mapping.guild_id}"
                        "could not be found, skipping"
                    )
                )
                continue

        print(
            (
                f"\t\tloading mapping in guild: {guild.name} | "
                f"for discord role id: {mapping.discord_role_id}, external: "
                f"{mapping.role_id}"
            )
        )

        channel = guild.get_channel_or_thread(mapping.channel_id)
        if not channel:
            try:
                channel = await guild.fetch_channel(mapping.channel_id)
            except discord.NotFound:
                print(
                    (
                        f"channel with ID: {mapping.channel_id} "
                        "could not be found, skipping"
                    )
                )
                continue
        assert isinstance(channel, Messageable)
        message = channel.get_partial_message(mapping.message_id)

        view.message = message
        bot.add_view(view)

    await bot.add_cog(RoleSyncConfigHandler(bot))
