import psycopg2

# PASTE YOUR EXTERNAL DATABASE URL FROM RENDER BELOW
DB_URL = os.environ.get('DATABASE_URL')
def setup_database():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # Tables for your Smart Care & Vaccination project
        commands = [
            "CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name VARCHAR(255), email VARCHAR(255) UNIQUE, password VARCHAR(255), lmp_date DATE);",
            "CREATE TABLE IF NOT EXISTS health_checks (id SERIAL PRIMARY KEY, user_name VARCHAR(255), systolic INT, sugar DECIMAL(10,2), risk_result VARCHAR(50), check_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS faq (id SERIAL PRIMARY KEY, category VARCHAR(100), question TEXT, answer TEXT);",
            "INSERT INTO faq (category, question, answer) VALUES ('General', 'Setup Status', 'Database tables created for Tejaswini thesis!');"
        ]
        
        for command in commands:
            cur.execute(command)
            
        conn.commit()
        print("✅ SUCCESS: Your Render database tables are now created!")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    setup_database()