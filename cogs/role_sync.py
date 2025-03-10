import asyncio
import time
import sqlite3 

import discord
from discord import app_commands
from discord.ext import commands

class RoleSync(commands.Cog):

    bot: commands.Bot

    def __init__(self, bot):
        self.bot = bot

    def queryPostgres(self, query): 
        return []
    
    def syncAll(self): 
        print("<------test------->")
        # Connecting to sqlite 
        # connection object 
        connection_obj = sqlite3.connect('database.db') 

        # cursor object 
        cursor_obj = connection_obj.cursor() 

        # to select all column we will use 
        statement = '''SELECT connected_accounts FROM DATABASE'''

        cursor_obj.execute(statement) 

        output = cursor_obj.fetchall() 
        for row in output: 
            print(row)
            

        connection_obj.commit() 

        # Close the connection 
        connection_obj.close()


        print("</------test------->")




    



# ----------------------MAIN PROGRAM----------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions().
async def setup(bot: commands.Bot) -> None:
    print("\tcogs.role_sync begin loading")
    rs = RoleSync(bot)
    await bot.add_cog(rs)
    rs.syncAll()

        
