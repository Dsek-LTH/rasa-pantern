import asyncio
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import final, override
from zoneinfo import ZoneInfo

import asyncpg
import discord
from discord import (
    Guild,
    HTTPException,
    Interaction,
    Permissions,
    Role,
    app_commands,
)
from discord.ext import commands, tasks

from helpers import CogSetting
from main import PanternBot

WEBSITE_DB_URL = os.getenv("WEBSITE_DB_URL")


@final
class SyncOutputData:
    def __init__(self):
        self.total_users_to_change: int = 0
        self.failed_users: int = 0
        self.non_changed_users: int = 0
        self.non_syncable_roles: list[int] = []

    @override
    def __repr__(self) -> str:
        return (
            f"Sync for {self.total_users_to_change}, "
            f"changed: {self.get_changed_amount()}, "
            f"didn't change: {self.non_changed_users}, "
            f"failed: {self.failed_users}. "
            f"{len(self.non_syncable_roles)} roles were unsyncable."
        )

    def user_failed(self):
        """
        Increment failed user count.
        """
        self.failed_users += 1

    def user_no_change(self):
        """
        Increment non changed user count.
        """
        self.non_changed_users += 1

    def add_non_syncable_role(self, role_id: int):
        """
        Add a role the bot cannot sync to the list.
        """
        self.non_syncable_roles.append(role_id)

    def get_changed_amount(self) -> int:
        return (
            self.total_users_to_change
            - self.failed_users
            - self.non_changed_users
        )


@dataclass
class SyncInfo:
    run_at: datetime
    guild: discord.Guild
    re_run: bool = False
    re_run_rate: timedelta | None = None


async def get_external_role_list() -> dict[str, list[str]]:
    """
    Gets external role id's from our website database and formats them into
    something that we can use with the bot.

    Returns:
        dict[str, list[str]]: A dict mapping external role id to a list of
                              external groups.
    """

    conn: asyncpg.Connection = await asyncpg.connect(WEBSITE_DB_URL)
    assert isinstance(conn, asyncpg.Connection)
    try:
        # Potentially we could remove anyone who doesn't have an email set.
        # This would get rid of most old users, and stop us from having to
        # worry about them.
        # TODO: CPU core are hard coded in this list. That might not be great..
        rows = await conn.fetch(
            """
                SELECT
                  student_id AS username,
                  COALESCE(
                    jsonb_agg(mandates.position_id)
                      FILTER (WHERE mandates.position_id IS NOT NULL),
                    '[]'::jsonb
                  )
                  ||
                  -- Add board members:
                  CASE
                    WHEN bool_or(positions.board_member)
                      THEN jsonb_build_array('dsek.styr')
                    ELSE '[]'::jsonb
                  END
                  ||
                  -- Add cpu.core (this really shouldn't be hard-coded)
                  CASE
                    WHEN bool_or(positions.id IN (
                        'dsek.cpu.mastare',
                        'dsek.cpu.vice_mastare',
                        'dsek.cpu.dwwwansv',
                        'dsek.cpu.root'
                    ))
                    THEN jsonb_build_array('dsek.cpu.core')
                    ELSE '[]'::jsonb
                  END AS groups
                FROM members
                LEFT JOIN mandates
                  ON members.id = mandates.member_id
                  AND start_date <= CURRENT_DATE
                  AND end_date >= CURRENT_DATE
                LEFT JOIN positions
                  ON mandates.position_id = positions.id
                GROUP BY student_id;
            """
        )
    finally:
        await conn.close()

    user_groups: dict[str, list[str]] = {}
    if rows:
        for row in rows:
            username = str(row["username"])
            groups: list[str] = json.loads(row["groups"])
            user_groups[username] = groups
    else:
        print("Warning, Website database returned no members!")
    return user_groups


@final
class RoleSyncHandler(commands.Cog):
    def __init__(self, bot: PanternBot) -> None:
        self.bot = bot
        self.add_time_event = asyncio.Event()
        self.sync_times: list[SyncInfo] = []
        self.sync_timer_task = bot.loop.create_task(self.sync_timer())

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
        _ = self.sync_timer_task.cancel()

    def add_sync_time(self, sync_info: SyncInfo):
        self.sync_times.append(sync_info)
        self.sync_times.sort(key=lambda si: si.run_at)
        self.add_time_event.set()

    async def sync_timer(self) -> None:
        while True:
            if not self.sync_times:
                self.add_time_event.clear()
                _ = await self.add_time_event.wait()
                continue

            sync_info = self.sync_times[0]
            now = datetime.now(timezone.utc)
            wait_time = (sync_info.run_at - now).total_seconds()
            if wait_time > 0:
                try:
                    self.add_time_event.clear()
                    _ = await asyncio.wait_for(
                        self.add_time_event.wait(), timeout=wait_time
                    )
                    # We have added a new time, go back to top of function
                    continue
                except asyncio.TimeoutError:
                    pass

            # Remove the time we just passed
            _ = self.sync_times.pop(0)

            # Schedule a run task so we can continue with our loop
            _ = asyncio.create_task(self.run_timer_sync(sync_info))

    async def run_timer_sync(self, sync_info: SyncInfo):
        output_data = await self._sync(sync_info.guild)
        print(
            (
                f"auto sync run at: {sync_info.run_at} "
                f"in guild {sync_info.guild.name} "
                "has completed"
            )
        )
        print(output_data)
        if len(self.sync_times) > 0:
            print(self.sync_times)
        if sync_info.re_run:
            if sync_info.re_run_rate:
                new_sync_info = sync_info
                new_sync_info.run_at = sync_info.run_at + sync_info.re_run_rate
                self.add_sync_time(new_sync_info)
                print(f"Re-scheduled sync for {new_sync_info.run_at}")
            else:
                print(
                    (
                        "WARN: Event was scheduled to re-run"
                        " but doesn't have the re-run rate set. Ignoring"
                    )
                )
        print()

    async def _sync(self, guild: Guild) -> SyncOutputData:
        # TODO: Consider chunking when getting from our database and doing a
        # certain amount of users / roles at a time in order to avoid running
        # out of ram (not that we probably ever will on our hardware, but it
        # would be nice to keep in mind).
        print("starting sync")
        if bool(
            await self.bot.db.get_setting(
                guild.id, CogSetting.ROLE_SYNC_HANDLER, "dry_run"
            )
        ):
            print("!!!RUNNING IN DRY MODE!!!")

        output_data = SyncOutputData()

        if self.bot.get_guild(guild.id) is None:
            guild = await self.bot.fetch_guild(guild.id)

        # Make sure our users are cached as cheaply as possible:
        if not guild.chunked:
            # WARN: This can be very intensive and may take a long time for
            # very big servers (thankfully ours doesn't count as one).
            _ = await guild.chunk()

        all_roles = guild.roles
        new_roles: dict[int, set[int]] = defaultdict(set)
        old_roles: dict[int, set[int]] = defaultdict(set)
        role_LUT: dict[int, Role] = {}
        roles_to_sync = await self.bot.db.get_guild_role_configs(guild.id)

        # Make a list of all non syncing roles
        for role in all_roles:
            role_LUT[role.id] = role

            if not role.is_assignable():
                print(f"\t no permissions to assign to {role.name}")
                output_data.add_non_syncable_role(role.id)
                for user in role.members:
                    old_roles[user.id].add(role.id)
                    new_roles[user.id].add(role.id)
                continue

            role_is_synced = role.id not in [
                sync_role.discord_role_id for sync_role in roles_to_sync
            ]
            # If we aren't syncing this role, don't add it to the users list of
            # new roles
            for user in role.members:
                old_roles[user.id].add(role.id)
                if role_is_synced:
                    new_roles[user.id].add(role.id)

        external_linked_users: dict[str, list[str]] = (
            await get_external_role_list()
        )

        # Maps discord user id to list of external roles
        linked_users: dict[int, list[str]] = {}

        for user_id in external_linked_users:
            discord_user_id = await self.bot.db.get_discordId_from_externalId(
                user_id
            )
            if discord_user_id:
                linked_users[discord_user_id] = external_linked_users[user_id]
            else:
                # This would spam the logs a tad too much maybe we only check
                # for users with emails or something IDK? It would be nice info
                # to have imo
                # print(
                #     (
                #         f"external user {user_id} "
                #         "did not map to any discord user"
                #     )
                # )
                pass

        # TODO: This might need major refactoring for speedups and general
        # readability, it's a tripple nested for loop for gods sake...
        for user_id in linked_users:
            if linked_users[user_id] != []:
                print(("Syncing roles for: " f"{guild.get_member(user_id)}"))
            for external_role in linked_users[user_id]:
                role = next(
                    (r for r in roles_to_sync if r.role_id == external_role),
                    None,
                )
                if role:
                    if role.discord_role_id in output_data.non_syncable_roles:
                        print(
                            (
                                f"\tCould not add role {role.role_id}"
                                " (discord: "
                                f"{guild.get_role(role.discord_role_id)}) "
                                f"to {guild.get_member(user_id)} "
                                "since role is non syncable"
                            )
                        )
                    else:
                        new_roles[user_id].add(role.discord_role_id)
                        print(
                            (
                                f"\tadding {role.role_id} (discord: "
                                f"{guild.get_role(role.discord_role_id)}) "
                                f"to {guild.get_member(user_id)}"
                            )
                        )

        print()
        output_data.total_users_to_change = len(new_roles)

        for user_id in new_roles:
            if new_roles[user_id] == old_roles[user_id]:
                # We don't need to set the roles for a user if we don't need to
                # change them, and thus we don't need to load them either
                output_data.user_no_change()
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
                    output_data.user_failed()
                    continue

            print(
                (
                    f"settings roles of {member.name} to "
                    f"{[role_LUT[r].name for r in new_roles[user_id]]}"
                )
            )
            try:
                if not bool(
                    await self.bot.db.get_setting(
                        guild.id, CogSetting.ROLE_SYNC_HANDLER, "dry_run"
                    )
                ):
                    _ = await member.edit(
                        roles=[
                            role_LUT[role_id] for role_id in new_roles[user_id]
                        ]
                    )
                pass
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
                        f"Stack is as follows: {e}\n"
                    )
                )
                output_data.user_failed()
            except HTTPException as e:
                print(
                    (
                        "\n ERROR: HTTP Exception, the action failed. "
                        f"Stacktrace is as follows: {e}"
                    )
                )
                output_data.user_failed()

        print("sync done")
        return output_data

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.default_permissions(Permissions(administrator=True))
    async def start_sync(self, interaction: Interaction) -> None:
        """
        Syncs all configured groups from an external source into discord.
        """

        assert interaction.guild
        _ = await interaction.response.defer()

        data = await self._sync(interaction.guild)

        sync_string = (
            (
                "Next automatic sync "
                f"<t:{int(self.sync_times[0].run_at.timestamp())}:R>."
            )
            if len(self.sync_times) > 0
            else "No automatic sync running."
        )
        dry_run = bool(
            await self.bot.db.get_setting(
                interaction.guild.id, CogSetting.ROLE_SYNC_HANDLER, "dry_run"
            )
        )
        dry_mode_string = "# WARNING: RUNNING IN DRY MODE\n" if dry_run else ""
        _ = await interaction.followup.send(
            (
                f"{dry_mode_string}"
                "Sync completed!\n"
                f"Synced {data.total_users_to_change} users.\n"
                f"{sync_string}\n"
                f"{data.get_changed_amount()} succeeded, "
                f"{data.non_changed_users} were unchanged and "
                f"{data.failed_users} failed."
            ),
            ephemeral=True,
        )

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.default_permissions(Permissions(administrator=True))
    @app_commands.describe(
        sync_at="The time at which the bot should sync the roles (HH:MM)",
        re_run=(
            "Whether the sync should automatically "
            "re-run after it's complete."
        ),
        re_run_rate=("How often the sync should re-run (written as DD:HH:MM)"),
    )
    async def autosync(
        self,
        interaction: Interaction,
        sync_at: str = "",
        re_run: bool = False,
        re_run_rate: str | None = None,
    ) -> None:
        """
        Sets the bot to automatically sync at the given time and interval.
        """
        # TODO: Make an autocomplete for the re_run_rate and sync_at
        # syncat: HH:MM
        # re_run_rate: DD:HH:MM or HH:MM
        assert interaction.guild
        assert interaction.guild_id
        timezone = await self.bot.db.get_setting(
            interaction.guild_id, CogSetting.ROLE_SYNC_HANDLER, "timezone"
        )
        if not timezone:
            _ = await interaction.response.send_message(
                (
                    "Timezone is not set for this Guild, "
                    f"please configure it by running /{self.set_timezone.name}"
                ),
                ephemeral=True,
            )
            return
        timezone = ZoneInfo(timezone)

        # TODO: Fix input formatting
        h, m = map(int, sync_at.split(":"))
        sync_time = datetime.now(timezone)
        sync_time = sync_time.replace(hour=h, minute=m, second=0)
        # If the time has already passed, assume the user meant that time
        # tomorrow
        if sync_time < datetime.now(timezone):
            sync_time += timedelta(days=1)

        if re_run:
            if not re_run_rate:
                _ = await interaction.response.send_message(
                    (
                        "If you want the sync to automatically re-run you "
                        "need to configure how often it should do so"
                    ),
                    ephemeral=True,
                )
                return
            else:
                # TODO: Make sure we support both DD:HH:MM and HH:MM
                d, h, m = map(int, re_run_rate.split(":"))
                re_run_obj = timedelta(days=d, hours=h, minutes=m, seconds=0)
        else:
            re_run_obj = None

        sync_info = SyncInfo(sync_time, interaction.guild, re_run, re_run_obj)
        self.add_sync_time(sync_info)
        # TODO: Make this output nicer
        _ = await interaction.response.send_message(
            (
                f"Scheduled sync for {sync_info.run_at} "
                f"with re_run set to {re_run} and a rate of {re_run_obj}"
            )
        )

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.default_permissions(Permissions(administrator=True))
    @app_commands.describe(tz="Olson timezone string (Europe/Stockholm)")
    @app_commands.rename(tz="timezone")
    async def set_timezone(self, interaction: Interaction, tz: str) -> None:
        """
        Sets the timezone of the bot sync to the given value
        """
        assert interaction.guild_id
        # TODO: Do error handling and make sure the timezone is valid
        # Also write an autocomplete handler to make sure this gets passed
        # properly.
        await self.bot.db.set_setting(
            interaction.guild_id, CogSetting.ROLE_SYNC_HANDLER, "timezone", tz
        )
        _ = await interaction.response.send_message(f"Set timezone to {tz}")

    @app_commands.guild_only()
    @app_commands.default_permissions(Permissions(administrator=True))
    @app_commands.describe(enabled="Whether to run in dry_run mode or not")
    async def set_dry_run(
        self, interaction: Interaction, enabled: bool
    ) -> None:
        """
        Configures if the bot should dry run or not
        (i.e. if the bot should refrain from changing any roles or not)
        """
        assert interaction.guild_id
        await self.bot.db.set_setting(
            interaction.guild_id,
            CogSetting.ROLE_SYNC_HANDLER,
            "dry_run",
            str(enabled),
        )


# ----------------------MAIN PROGRAM----------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions().
async def setup(bot: PanternBot) -> None:
    await bot.add_cog(RoleSyncHandler(bot))
