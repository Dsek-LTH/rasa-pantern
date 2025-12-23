from __future__ import annotations

from typing import final, override

import discord
from discord import Client, Message, Permissions, app_commands, ui
from discord.abc import GuildChannel, Messageable
from discord.ext import commands

from db_handler import DBHandler
from helpers import CogSetting
from main import PanternBot


class RoleConfigView(ui.LayoutView):
    def __init__(self):
        super().__init__()
        self.message: Message | None = None

    text: ui.TextDisplay[RoleConfigView] = ui.TextDisplay("test")


class SetupChannelModal(ui.Modal, title="Set up role sync config channel"):
    def __init__(self, db: DBHandler):
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
            CogSetting.ROLE_SYNC_HANDLER,
            "config_channel_id",
        )
        assert isinstance(self.channel.component, ui.ChannelSelect)
        _ = await self.db.set_setting(
            interaction.guild_id,
            CogSetting.ROLE_SYNC_HANDLER,
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
    def __init__(self, db: DBHandler):
        super().__init__()
        self.db: DBHandler = db

    discord_role: ui.Label[AddRoleConfig] = ui.Label(
        text="What discord role do you want to link?",
        component=ui.RoleSelect(required=True, placeholder="Discord role"),
    )

    authentic_role: ui.Label[AddRoleConfig] = ui.Label(
        text="What Authentic role should it be linked to?",
        component=ui.TextInput(placeholder="Authentic role id"),
    )

    @override
    async def on_submit(self, interaction: discord.Interaction) -> None:
        assert interaction.guild
        assert isinstance(self.discord_role.component, ui.RoleSelect)
        assert isinstance(self.authentic_role.component, ui.TextInput)
        channel_id = await self.db.get_setting(
            interaction.guild.id,
            CogSetting.ROLE_SYNC_HANDLER,
            "config_channel_id",
        )
        if not channel_id:
            _ = interaction.response.send_message(
                (
                    "There is no config channel set up for this server, "
                    "please ask an administrator to run the setup command"
                ),
                ephemeral=True,
            )
            return
        channel = interaction.guild.get_channel_or_thread(int(channel_id))
        if not isinstance(channel, GuildChannel):
            _ = interaction.response.send_message(
                "Error whilst trying to find channel, please contact an admin",
                ephemeral=True,
            )
            print(
                (
                    "error in AddRoleConfig whilst trying to get channel. "
                    f"Got {type(channel)} but was expecting GuildChannel"
                )
            )
            return
        assert isinstance(channel, Messageable)
        view = RoleConfigView()
        message = await channel.send(view=view)
        view.message = message

        _ = await self.db.create_role_config(
            message.id,
            self.authentic_role.component.value,
            self.discord_role.component.values[0].id,
            interaction.guild.id,
        )
        _ = await interaction.response.send_message(
            (
                f"Set up <@&{self.discord_role.component.values[0].id}> "
                f"to link to `{self.authentic_role.component.value}`."
            ),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )


@final
class RoleSyncHandler(commands.Cog):
    def __init__(self, bot: PanternBot):
        super().__init__()
        self.bot = bot

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.default_permissions(Permissions(administrator=True))
    # TODO: write description
    async def initialize_role_sync(
        self, interaction: discord.Interaction
    ) -> None:
        assert interaction.guild_id
        config_channel_id = await self.bot.db.get_setting(
            interaction.guild_id,
            CogSetting.ROLE_SYNC_HANDLER,
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

    async def reset_configs(self, interaction: discord.Interaction[Client]):
        assert interaction.guild_id
        await self.bot.db.remove_setting(
            interaction.guild_id,
            CogSetting.ROLE_SYNC_HANDLER,
            "config_channel_id",
        )
        await self.bot.db.purge_role_configs(interaction.guild_id)
        _ = await interaction.response.send_message(
            (
                "Config channel and all Role sync mappings have been purged.\n"
                "Please use this command again to re-configure role sync"
            ),
        )

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.default_permissions(Permissions(administrator=True))
    # TODO: write description
    async def create_role_mapping(self, interaction: discord.Interaction):
        assert interaction.guild_id
        config_channel_id = await self.bot.db.get_setting(
            interaction.guild_id,
            CogSetting.ROLE_SYNC_HANDLER,
            "config_channel_id",
        )
        if not config_channel_id:
            _ = await interaction.response.send_message(
                "Please run /initialize_role_sync to set up the bot",
                ephemeral=True,
            )
            return

        if not interaction.channel_id == int(config_channel_id):
            _ = await interaction.response.send_message(
                (
                    "This is not a role config channel, "
                    f"please configure the bot in <#{config_channel_id}>"
                ),
                ephemeral=True,
            )
        _ = await interaction.response.send_modal(AddRoleConfig(self.bot.db))


# ----------------------MAIN PROGRAM----------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions().
async def setup(bot: PanternBot) -> None:
    print("\tcogs.role_sync_handler begin loading")

    await bot.add_cog(RoleSyncHandler(bot))
