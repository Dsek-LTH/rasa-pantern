import asyncio
import time
import sqlite3 
import psycopg2

import discord
from discord import app_commands
from discord.ext import commands
from config import config


class RoleSync(commands.Cog):

    bot: commands.Bot

    def __init__(self, bot):
        self.bot = bot

    def queryPostgres(self, query): 
        return []
    
    def connect(self):
        """ Connect to the PostgreSQL database server """
        conn = None
        try:
            # read connection parameters
            params = config()

            # connect to the PostgreSQL server
            print('Connecting to the PostgreSQL database...')
            conn = psycopg2.connect(**params)
            
            # create a cursor
            cur = conn.cursor()
            
        # execute a statement
            print('------members--------:')
            cur.execute('SELECT studentId AND mandates FROM Member')

            # display the PostgreSQL database server version

            output = cur.fetchall() 
            for row in output: 
                print(row)
        
        # close the communication with the PostgreSQL
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')

    def syncAll(self): 
        print("<------test------->")
        # Connecting to sqlite 
        # connection object 
        connection_obj = sqlite3.connect('database.db') 

        # cursor object 
        cursor_obj = connection_obj.cursor() 

        # to select all column we will use 
        statement = '''SELECT stil_id FROM connected_accounts'''

        cursor_obj.execute(statement) 

        output = cursor_obj.fetchall() 
        for row in output: 
            print(row)
            

        connection_obj.commit() 

        # Close the connection 
        connection_obj.close()

        self.connect()

        print("</------test------->")


    







    



# ----------------------MAIN PROGRAM----------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions().
async def setup(bot: commands.Bot) -> None:
    print("\tcogs.role_sync begin loading")
    rs = RoleSync(bot)
    await bot.add_cog(rs)
    rs.syncAll()

        
