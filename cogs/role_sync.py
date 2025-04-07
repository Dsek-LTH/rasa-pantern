# -*- coding: UTF-8 -*-
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
    
    guild: discord.Guild 

    def __init__(self, bot):
        self.bot = bot
        self.guild = bot.get_guild(1348726708202635326) # Hard coded to test server TODO: add to env file.

    def queryPostgres(self, query): 
        return []
    
    def connect(self):
        print("<------connect------->")

        d = {}
        # Connect to the PostgreSQL database server
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

                    if now > start and end > now:
                        if not id in d:
                            d[id] = []
                        d[id].append(mandate)
                        print(mandate)
                        print(start)
                        print(end)
                        print(now)
                        

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

    def translateRoles(self, web_roles, cursor_obj):
        if web_roles == None:
            return {}
        roles = {}
        for web_role in web_roles:
            statement = f'''SELECT discord_role_id FROM connected_discord_roles WHERE position_id =\"{web_role}\"'''

            cursor_obj.execute(statement) 
            output = cursor_obj.fetchall()
            print(output)
            roles = output

             
        return roles

    async def syncAll(self): 
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
        statement = '''SELECT stil_id, user_id FROM connected_accounts'''

        cursor_obj.execute(statement) 
        output = cursor_obj.fetchall() 
        for row in output:
            stil = row[0]
            dcid = row[1]
            print(stil)
            print(dcid)
            try:
                if roles_dict[stil] is not None:
                    print(roles_dict[stil])
                    user = await self.guild.fetch_member(dcid)
                    print(user.display_name)
#                   user.add_roles(self.translateRoles(roles_dict[stil], cursor_obj))
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
    
    
    def get_position_ids(self):
        output = []
        # Connect to the PostgreSQL database server
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
            cur.execute('''SELECT DISTINCT position_id FROM Mandates''')

            temp = cur.fetchall()

            for e in temp:
                output.append(e[0])

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
        
        return set(output)




    # Slash command to setup role assignments
    @app_commands.command(name="roleconfig", description="Configure the relation between roles on the website and server.")
    async def roleConfig(self, interaction: discord.Interaction):
        positions = self.get_position_ids()
        view = discord.ui.View()


        view.add_item(RoleDropdown())
        await interaction.response.send_message("Test:",view=view)

    # Slash command to sync all role assignments
    @app_commands.command(name="syncroles", description="Configure the relation between roles on the website and server.")
    async def syncRoles(self, interaction: discord.Interaction):
        
        self.syncAll()
        
        await interaction.response.send_message(f"Synced all roles!")

class RoleDropdown(discord.ui.RoleSelect):
    
    def __init__(self):
        super().__init__(placeholder="Select an option",max_values=25,min_values=1)

    async def callback(self, interaction):
        await interaction.response.send_message("test complete")





# ----------------------MAIN PROGRAM----------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions().
async def setup(bot: commands.Bot) -> None:
    print("\tcogs.role_sync begin loading")
    rs = RoleSync(bot)
    await bot.add_cog(rs)
