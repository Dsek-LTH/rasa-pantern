from collections import defaultdict
from typing import final, override

import discord
from discord import (
    Guild,
    Interaction,
    NotFound,
    Permissions,
    Role,
    app_commands,
)
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
        # TODO: plan of action:
        # 1. go through all roles in server and store those that aren't set to
        #    sync in our database
        # 2. go through all these roles and store which users have them.
        #    Dict[Guild_id : Dict[role_id : List[user]]]
        # 3. get users from openidC provicer and put in dict mapping id to list
        #    of roles. Dict[user : List[role]]
        # 4. Get discord id mapping to other id from Janus:
        #    Dict[openid_id : discord_id]
        # 5. Go user by user and:
        #    b) get all openid role names
        #    c) get all discord roles mapped to the openid roles
        #    d) combine the two lists into one list of role objects
        #    e) set the users roles in the server to this list
        all_roles = guild.roles
        # print(f"all_roles: {all_roles}")
        new_roles: dict[int, list[int]] = defaultdict(list)
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
                    new_roles[user.id].append(role.id)
                continue

            if role.id not in map(lambda r: r.discord_role_id, roles_to_sync):
                for user in role.members:
                    # print(
                    #     f"\t adding role: {role.name} to {user.name}'s list of new roles"
                    # )
                    new_roles[user.id].append(role.id)

        # # WARN: This is debug output please remove
        # for user in new_roles:
        #     print(f"\t user: {guild.get_member(user)}")
        #     for role in new_roles[user]:
        #         print(f"\t\t{role_LUT[role]}")
        # # WARN: This is debug output please remove

        # get linked users and their external roles:
        # (discord_user_id: [external_role_1, external_role_2])
        linked_users: dict[int, list[str]] = {}

        # append syncing roles
        # TODO: This needs a major refactoring for speedups and general
        # readability
        for user_id in linked_users:
            print(f"\nprocessing {guild.get_member(user_id)}")
            for external_role in linked_users[user_id]:
                role = list(
                    filter(lambda r: r.role_id == external_role, roles_to_sync)
                )
                if role != []:
                    new_roles[user_id].append(role[0].discord_role_id)
                    print(
                        f"adding {role[0].role_id} (discord: {guild.get_role(role[0].discord_role_id)}) to {guild.get_member(user_id)}"
                    )

        print()

        for user_id in new_roles:
            # print(f"start setting roles for {guild.get_member(user_id)}")
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
                print(
                    (
                        "\n ERROR: "
                        f"a role for user {user_id} "
                        "is too high to assign trying to skip and continue. "
                        f"It could be any of the following: "
                        f"{[role_LUT[role_id].name for role_id in new_roles[user_id]]}"
                        " or a role the user already has. "
                        f"Stack is as follows {e}\n"
                    )
                )

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
