import discord
from discord import app_commands
from discord.ext import commands

from main import PanternBot

# Hardcoded list of sodas like in https://link.dsek.se/mauer
sodas = [
    "Cola/Fanta",
    "Pepsi/7up/Zingo",
    "Pepsi",
    "Smakis",
    "Pommac",
    "Ramlösa",
    "Trocadero",
    "Loka Crush",
]

# Dictionary to track who took what soda
soda_tracker = {}


class ChoseDrinkSelector(discord.ui.Select):
    def __init__(self, drink_list: list[str]) -> None:
        options = []
        for drink in drink_list:
            options.append(discord.SelectOption(label=drink, value=drink))
        if drink_list == []:
            options = [
                discord.SelectOption(
                    label="nothing",
                    description="There are no drinks to pick from",
                    default=True,
                )
            ]
        super().__init__(placeholder="Please select your drink", options=options)

    async def callback(self: discord.ui.Select, interaction: discord.Interaction):
        # TODO: Make sure this actually creates a DB entry
        await interaction.response.send_message(
            f"User {interaction.user.name} chose {self.values[0]}",
            ephemeral=True,
        )


class DrinkHandler(commands.Cog):

    def __init__(self, bot: PanternBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="test_drink",
    )
    @app_commands.guild_only()
    async def test_drink(self, interaction: discord.Interaction) -> None:
        if not interaction.guild_id:
            # INFO: If we reach this and don't have a guild id despite this
            # command being set to guild only something is very wrong...
            print("Command cannot find guild_id field")
            return
        drink_list = await self.bot.db.get_drink_list(interaction.guild_id)
        view = discord.ui.View()
        view.add_item(ChoseDrinkSelector(drink_list))
        await interaction.response.send_message("Pick drink:", view=view)

    # Slash command to show soda counts
    @app_commands.command(name="tally", description="See the soda tally count")
    async def tally(self, interaction: discord.Interaction):
        if not soda_tracker:
            await interaction.response.send_message(
                "No one has taken a soda yet.", ephemeral=True
            )
            return

        # Count the selections for each soda
        soda_count = {soda: 0 for soda in sodas}
        for soda in soda_tracker.values():
            if soda in soda_count:
                soda_count[soda] += 1

        # Create a tally string
        tally_list = "\n".join(
            [f"**{soda}**: {count}" for soda, count in soda_count.items() if count > 0]
        )

        await interaction.response.send_message(f"**Soda Tally Count:**\n{tally_list}")

    # Slash command to show detailed soda info
    @app_commands.command(name="tallymore", description="See detailed soda choices")
    async def tallymore(self, interaction: discord.Interaction):
        if not soda_tracker:
            await interaction.response.send_message(
                "No one has taken a soda yet.", ephemeral=True
            )
            return

        detailed_list = "\n".join(
            [f"<@{user_id}> → **{soda}**" for user_id, soda in soda_tracker.items()]
        )

        await interaction.response.send_message(
            f"**Detailed Soda Choices:**\n{detailed_list}"
        )


# ----------------------MAIN PROGRAM----------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions().
async def setup(bot: PanternBot) -> None:
    print("\tcogs.drinks_handler begin loading")
    await bot.add_cog(DrinkHandler(bot))
