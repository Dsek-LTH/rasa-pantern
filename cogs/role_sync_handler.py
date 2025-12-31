from collections import defaultdict
from dis import disco
from typing import final, override

import discord
from discord import Guild, Interaction, Permissions, Role, app_commands
from discord.ext import commands, tasks

from main import PanternBot


@final
class RoleSyncHandler(commands.Cog):
    def __init__(self, bot: PanternBot, dry_run_mode: bool) -> None:
        self.bot = bot
        # TODO: make this a database entry that defaults to false
        # We also want database entries for when a certain
        self.dry_run = dry_run_mode

    @override
    async def cog_load(self) -> None:
        # TODO: load timezone and synctime per guild here so we can run the
        # sync task only when we need to
        return await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        # TODO: Consider if we need to handle what happens if the cog gets
        # unloaded whlist running a sync, a dirty flag in the database maybe?
        await super().cog_unload()
        pass

    async def _sync(self, guild: Guild) -> None:
        print("starting sync")

        if self.bot.get_guild(guild.id) is None:
            guild = await self.bot.fetch_guild(guild.id)

        # Make sure our users are cached as cheaply as possible:
        if not guild.chunked:
            # WARN: This is very intensive and may take a long time for very
            # big servers (thankfully ours doesn't count as one).
            _ = await guild.chunk()

        all_roles = guild.roles
        new_roles: dict[int, set[int]] = defaultdict(set)
        old_roles: dict[int, set[int]] = defaultdict(set)
        role_LUT: dict[int, Role] = {}
        roles_to_sync = await self.bot.db.get_guild_role_configs(guild.id)

        # print(f"roles_to_sync: {roles_to_sync}")
        # Make a list of all non syncing roles
        for role in all_roles:
            role_LUT[role.id] = role

            if not role.is_assignable():
                print(f"\t no permissions to assign to {role.name}")
                # TODO: add these values into some form of output object so
                # We can give info back to the user.
                for user in role.members:
                    old_roles[user.id].add(role.id)
                    new_roles[user.id].add(role.id)
                continue

            sync_roles = role.id not in map(
                lambda r: r.discord_role_id, roles_to_sync
            )
            for user in role.members:
                old_roles[user.id].add(role.id)
                if sync_roles:
                    new_roles[user.id].add(role.id)

        # # WARN: This is debug output please remove
        # for user in new_roles:
        #     print(f"\t user: {guild.get_member(user)}")
        #     for role in new_roles[user]:
        #         print(f"\t\t{role_LUT[role]}")
        # # WARN: This is debug output please remove

        # TODO: Get linked users and their external roles:
        # (external_id: [external_role_1, external_role_2])
        external_linked_users: dict[str, list[str]] = {}
        linked_users: dict[int, list[str]] = {}
        for user_id in external_linked_users:
            discord_user_id = await self.bot.db.get_discordId_from_externalId(
                user_id
            )
            if discord_user_id:
                linked_users[discord_user_id] = external_linked_users[user_id]
            else:
                print(
                    f"external user {user_id} did not map to any discord user"
                )

        # append syncing roles
        # TODO: This needs a major refactoring for speedups and general
        # readability, it's a tripple nested for loop for gods sake...
        for user_id in linked_users:
            for external_role in linked_users[user_id]:
                role = list(
                    filter(lambda r: r.role_id == external_role, roles_to_sync)
                )
                if role != []:
                    new_roles[user_id].add(role[0].discord_role_id)
                    print(
                        f"adding {role[0].role_id} (discord: {guild.get_role(role[0].discord_role_id)}) to {guild.get_member(user_id)}"
                    )

        print()

        for user_id in new_roles:
            if new_roles[user_id] == old_roles[user_id]:
                # We don't need to set the roles for a user if we don't need to
                # change them, and thus we don't need to load them either
                continue

            # This should never be required, but make sure that we actually
            # have a user object to work on even if we cache all guild members
            # in the beginning of this function.
            member = guild.get_member(user_id)
            if member is None:
                try:
                    member = await guild.fetch_member(user_id)
                except discord.NotFound:
                    print(
                        (
                            f"ERROR: user with id: {user_id} "
                            f"could not be found in guild: {guild.name}"
                            ". Skipping them..."
                        )
                    )
                    continue

            print(
                f"settings roles of {member.name} to {[role_LUT[r].name for r in new_roles[user_id]]}"
            )
            try:
                _ = await member.edit(
                    roles=[role_LUT[role_id] for role_id in new_roles[user_id]]
                )
            except discord.Forbidden as e:
                user_role_list = [
                    role_LUT[role_id].name for role_id in new_roles[user_id]
                ]
                print(
                    (
                        "\n ERROR: "
                        f"a role for user {user_id} "
                        "is too high to assign, trying to skip and continue. "
                        f"It could be any of the following: "
                        f"{user_role_list}"
                        " or a role the user already has. "
                        f"Stack is as follows {e}\n"
                    )
                )

        print("sync done")

    @tasks.loop(hours=24)
    async def sync_task(self) -> None:
        # TODO: make this check what guild to update
        for guild in self.bot.guilds:
            await self._sync(guild)

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.default_permissions(Permissions(administrator=True))
    # TODO: add description
    async def sync_roles(self, interaction: Interaction) -> None:
        assert interaction.guild
        _ = await interaction.response.defer()

        await self._sync(interaction.guild)

        _ = await interaction.followup.send(
            f"next sync in {self.sync_task.next_iteration}. Sync completed",
            ephemeral=True,
        )

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.default_permissions(Permissions(administrator=True))
    # TODO: add description
    async def configure_sync(
        self, interaction: Interaction, sync_at: str
    ) -> None:
        # TODO: make Sync_at DateTime object
        # Set the sync time in the database and the sync_task timer to the
        # given value
        pass

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.default_permissions(Permissions(administrator=True))
    async def set_timezone(self, interaction: Interaction) -> None:
        # TODO: Allow the user to set the timezone to a valid option.
        # Maybe use autocomplete to make this easier?
        # Set the timezone and the timezone for the sync_task timer to the
        # given value
        pass


# ----------------------MAIN PROGRAM----------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions().
async def setup(bot: PanternBot) -> None:
    await bot.add_cog(RoleSyncHandler(bot, True))
