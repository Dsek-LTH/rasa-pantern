import sqlite3


print("<------test------->")
# Connecting to sqlite 
# connection object 
connection_obj = sqlite3.connect('database.db') 

# cursor object 
cursor_obj = connection_obj.cursor() 

statement = '''SELECT * FROM connected_accounts'''
res = cursor_obj.execute(statement) 

for row in res:
    print(row)


statement = '''SELECT * FROM authorized_discord_users'''
res = cursor_obj.execute(statement) 

for row in res:
    print(row)


statement = '''SELECT * FROM authorized_dsek_users'''
res = cursor_obj.execute(statement) 

for row in res:
    print(row)
    

connection_obj.commit() 

# Close the connection 
connection_obj.close()


print("</------test------->")