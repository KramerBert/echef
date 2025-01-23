import mysql.connector

# Maak verbinding met de database
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="PCstraat100%",
    database="echef"
)

cursor = connection.cursor()



connection.commit()
cursor.close()
connection.close()