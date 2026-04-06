import mysql.connector

try:
    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        password="", 
        database="pregnancy_db"
    )

    if mydb.is_connected():
        print("✅ Success! Your database is ready.")
        cursor = mydb.cursor()
        cursor.execute("SHOW TABLES")
        for table in cursor:
            print(f"- {table[0]}")

except Exception as e:
    print(f"❌ Error: {e}")