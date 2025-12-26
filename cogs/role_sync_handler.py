from typing import final, override

from discord.ext import commands

from main import PanternBot


@final
class RoleSyncHandler(commands.Cog):
    def __init__(self, bot: PanternBot) -> None:
        self.bot = bot

    @override
    async def cog_unload(self) -> None:
        # TODO: consider
        await super().cog_unload()
        pass


# ----------------------MAIN PROGRAM----------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions().
async def setup(bot: PanternBot) -> None:
    await bot.add_cog(RoleSyncHandler(bot))
