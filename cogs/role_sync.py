import asyncio
import time
import sqlite3 
import psycopg2
import datetime

import discord
from discord import app_commands
from discord.ext import commands
from config import config
from psycopg2.extras import RealDictCursor


class RoleSync(commands.Cog):

    bot: commands.Bot

    def __init__(self, bot):
        self.bot = bot

    def queryPostgres(self, query): 
        return []
    
    def connect(self):
        print("<------connect------->")

        d = {}
        """ Connect to the PostgreSQL database server """
        conn = None
        try:
            # read connection parameters
            params = config()

            # connect to the PostgreSQL server
            print('Connecting to the PostgreSQL database...')
            conn = psycopg2.connect(**params)
            
            # create a cursor
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # execute a statement
            cur.execute('''
                        SELECT 
                            Members.student_id,
                            ARRAY_AGG(Mandates.position_id) AS position_ids,
                            ARRAY_AGG(Mandates.start_date) AS start_dates,
                            ARRAY_AGG(Mandates.end_date) AS end_dates
                        FROM Members
                        LEFT JOIN Mandates ON Members.id = Mandates.member_id
                        GROUP BY Members.id;
                        ''')

            output = cur.fetchall() 

            for row in output:
                id = row["student_id"]
                print("---------------")
                print(id)
                for i in range(len(row["position_ids"])):
                    mandate = row["position_ids"][i]
                    if mandate is None:
                        continue
                    start = row["start_dates"][i]
                    end = row["end_dates"][i]
                    now = datetime.date.today()
                    print(mandate)
                    print(start)
                    print(end)
                    print(now)

                    if now > start and end > now:
                        if not id in d:
                            d[id] = []
                        d[id].append(mandate)

                print("---------------")
                



            print("ullas mandat:")
            print(d["ul3574bl-s"])

            

        # close the communication with the PostgreSQL
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            print("<Error>")
            print(type(error))
            print(error)
            print("</Error>")
        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')

        print("</------connect------->")
        
        return d

    def syncAll(self): 
        print("<------syncAll------->")
        # Get postgresql data
        roles_dict = self.connect()
        # print("=== Roles Dict ===")
        # print(roles_dict)

        # Connecting to sqlite 
        # connection object 
        print('Connecting to the sqlite database...')
        connection_obj = sqlite3.connect('database.db') 

        # cursor object 
        cursor_obj = connection_obj.cursor() 

        # to select all column we will use 
        statement = '''SELECT stil_id FROM connected_accounts'''

        cursor_obj.execute(statement) 
        output = cursor_obj.fetchall() 
        for row in output:
            stil = row[0]
            print(stil)
            try:
                if roles_dict[stil] is None:
                    print("No roles")
                else:
                    print(roles_dict[stil])
            except (KeyError) as key_error:
                print("Error: does not exist in member database")
            

        connection_obj.commit() 

        # Close the connection 
        connection_obj.close()
        print('Database connection closed.')



        print("</------syncAll------->")



    # Slash command to give test role
    @app_commands.command(name="getrole", description="Give yourself test role.")
    async def getRole(self, interaction: discord.Interaction):
        role = discord.utils.get(interaction.guild.roles, name="Test role")
        await interaction.user.add_roles(role)

        await interaction.response.send_message(f"Tried giving you the test role.")

    # Slash command to remove test role
    @app_commands.command(name="loserole", description="Remove test role from yourself.")
    async def loseRole(self, interaction: discord.Interaction):
        role = discord.utils.get(interaction.guild.roles, name="Test role")
        await interaction.user.remove_roles(role)

        await interaction.response.send_message(f"Tried giving you the test role.")



    


# ----------------------MAIN PROGRAM----------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions().
async def setup(bot: commands.Bot) -> None:
    print("\tcogs.role_sync begin loading")
    rs = RoleSync(bot)
    await bot.add_cog(rs)
    rs.syncAll()

        
