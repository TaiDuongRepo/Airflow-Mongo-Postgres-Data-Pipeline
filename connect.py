import psycopg2

connection = psycopg2.connect(
    host="localhost",     
    port="5432",          
    database="lab8", 
    user="lab8",       
    password="lab8"    
)

cursor = connection.cursor()

# check connection
cursor.execute("SELECT version();")
record = cursor.fetchone()
print("You are connected to - ", record, "\n")

# close connection
cursor.close()
connection.close()
print("PostgreSQL connection is closed")

