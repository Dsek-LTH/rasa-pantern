import discord
import os
from discord.ext import commands
from dotenv import load_dotenv

# Load the .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Hardcoded list of sodas like in https://link.dsek.se/mauer
sodas = ["Cola/Fanta","Pepsi/7up/Zingo", "Pepsi", "Smakis", "Pommac", "Ramlösa", "Trocadero", "Loka Crush"]

# Dictionary to track who took what soda
soda_tracker = {}

# Bot setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# Slash command to show soda list
@bot.tree.command(name="drink", description="Choose a soda to drink")
async def drink(interaction: discord.Interaction):
    class SodaButtons(discord.ui.View):
        def __init__(self):
            super().__init__()
            for soda in sodas:
                self.add_item(SodaButton(soda))
            self.add_item(discord.ui.Button(label="Add Custom Soda", style=discord.ButtonStyle.secondary, custom_id="add_custom"))

    class SodaButton(discord.ui.Button):
        def __init__(self, soda_name: str):
            super().__init__(label=soda_name, style=discord.ButtonStyle.primary)
            self.soda_name = soda_name

        async def callback(self, interaction: discord.Interaction):
            user = interaction.user
            soda_tracker[user.id] = self.soda_name
            await interaction.response.send_message(f"{user.mention} chose **{self.soda_name}**!", ephemeral=True)

    # Handle the custom soda button interaction
    async def add_custom(interaction: discord.Interaction):
        await interaction.response.send_message(f"{interaction.user.mention}, please type the name of the custom soda you'd like to add:", ephemeral=True)

        def check(msg):
            return msg.author == interaction.user and msg.channel == interaction.channel

        try:
            # Wait for a message from the user with the custom soda name
            msg = await bot.wait_for("message", check=check, timeout=30)
            custom_soda = msg.content
            soda_tracker[interaction.user.id] = custom_soda  # Add the custom soda to the tracker
            sodas.append(custom_soda)  # Optionally add it to the soda list
            await interaction.channel.send(f"{interaction.user.mention} added **{custom_soda}** to the list and chose it!", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.channel.send(f"{interaction.user.mention}, you took too long to respond. Please try again.", ephemeral=True)

    # Create the initial message with the clickable buttons
    await interaction.response.send_message("Choose your drink:", view=SodaButtons())

    # Override the button's callback method to add custom soda
    for item in SodaButtons().children:
        if item.custom_id == "add_custom":
            item.callback = add_custom

# Slash command to show soda counts
@bot.tree.command(name="tally", description="See the soda tally count")
async def tally(interaction: discord.Interaction):
    if not soda_tracker:
        await interaction.response.send_message("No one has taken a soda yet.", ephemeral=True)
        return

    # Count the selections for each soda
    soda_count = {soda: 0 for soda in sodas}
    for soda in soda_tracker.values():
        if soda in soda_count:
            soda_count[soda] += 1

    # Create a tally string
    tally_list = "\n".join([f"**{soda}**: {count}" for soda, count in soda_count.items() if count > 0])
    
    await interaction.response.send_message(f"**Soda Tally Count:**\n{tally_list}")

# Slash command to show detailed soda info
@bot.tree.command(name="tallymore", description="See detailed soda choices")
async def tallymore(interaction: discord.Interaction):
    if not soda_tracker:
        await interaction.response.send_message("No one has taken a soda yet.", ephemeral=True)
        return

    detailed_list = "\n".join([f"<@{user_id}> → **{soda}**" for user_id, soda in soda_tracker.items()])
    
    await interaction.response.send_message(f"**Detailed Soda Choices:**\n{detailed_list}")

# Run the bot
bot.run(TOKEN)