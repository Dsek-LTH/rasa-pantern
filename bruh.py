import sqlite3


print("<------test------->")
# Connecting to sqlite 
# connection object 
connection_obj = sqlite3.connect('database.db') 

# cursor object 
cursor_obj = connection_obj.cursor() 

# to select all column we will use 
statement = '''PUT   stil_id FROM connected_accounts'''

cursor_obj.execute(statement) 
    

connection_obj.commit() 

# Close the connection 
connection_obj.close()


print("</------test------->")