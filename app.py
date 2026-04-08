from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os
import urllib.parse

app = Flask(__name__)
app.secret_key = 'pregnancy_care_key_2024'

# --- SMART DATABASE CONNECTION ---
def get_db_connection():
    # Render provides this environment variable
    db_url = os.environ.get('DATABASE_URL')
    
    if db_url:
        # PRODUCTION: Use PostgreSQL on Render
        return psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    else:
        # LOCAL: Use your local MySQL (XAMPP)
        import mysql.connector
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="", 
            database="pregnancy_db"
        )

# --- EMERGENCY SETUP ROUTE (RUN THIS ONCE) ---
@app.route('/setup-db-task-final')
def setup_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql_commands = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, name VARCHAR(100), 
            email VARCHAR(100) UNIQUE, password VARCHAR(100), lmp_date DATE
        );
        CREATE TABLE IF NOT EXISTS health_checks (
            id SERIAL PRIMARY KEY, user_name VARCHAR(100), 
            systolic INT, sugar FLOAT, risk_result VARCHAR(50), 
            check_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_vaccines (
            id SERIAL PRIMARY KEY, user_name VARCHAR(100), 
            vaccine_name VARCHAR(100), status VARCHAR(50), 
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, week_at_completion INT
        );
        CREATE TABLE IF NOT EXISTS faq (
            id SERIAL PRIMARY KEY, category VARCHAR(100), 
            question TEXT, answer TEXT
        );
        INSERT INTO faq (category, question, answer) 
        SELECT 'General', 'Welcome', 'Welcome to your pregnancy tracker.'
        WHERE NOT EXISTS (SELECT 1 FROM faq LIMIT 1);
        """
        cursor.execute(sql_commands)
        conn.commit()
        return "<h1>Success! Tables Created. You can now Register and Login.</h1>"
    except Exception as e:
        return f"<h1>Setup Error: {e}</h1>"
    finally:
        cursor.close()
        conn.close()

@app.route('/')
def home():
    return render_template('register.html')

# --- 1. REGISTRATION ---
@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    # MOBILE FIX: strip spaces and force lowercase
    email = request.form['email'].strip().lower() 
    password = request.form['password']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)"
        cursor.execute(query, (name, email, password))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('login_page'))
    except Exception as err:
        if conn: conn.rollback()
        return f"<h1>Registration Error: {err}</h1>"

# --- 2. LOGIN ---
@app.route('/login_page')
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    # MOBILE FIX: force lowercase and strip spaces
    email = request.form['email'].strip().lower()
    password = request.form['password']
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
    user = cursor.fetchone()
    
    if user:
        session['user_name'] = user['name']
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))
    
    cursor.close()
    conn.close()
    return "<h1>Invalid Login! Check your email/password or try Registering again.</h1>"

# --- 3. DASHBOARD ---
@app.route('/dashboard')
def dashboard():
    if 'user_name' not in session:
        return redirect(url_for('login_page'))

    user_display_name = session.get('user_name')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT lmp_date FROM users WHERE name = %s", (user_display_name,))
        user_data = cursor.fetchone()
        
        weeks, progress, trimester = 0, 0, "Not Started"
        due_date, upcoming_task = "N/A", "Please set your LMP date to begin tracking."

        if user_data and user_data['lmp_date']:
            lmp = user_data['lmp_date']
            if isinstance(lmp, str):
                lmp = datetime.strptime(lmp, '%Y-%m-%d').date()
            
            today = datetime.now().date()
            days_diff = (today - lmp).days
            weeks = days_diff // 7
        if weeks > 42:
            weeks = 0 # Or set a message saying "Pregnancy Completed"
            progress = min(int((weeks / 40) * 100), 100)
            due_date = (lmp + timedelta(days=280)).strftime('%B %d, %Y')
            trimester = "1st Trimester" if weeks <= 12 else "2nd Trimester" if weeks <= 26 else "3rd Trimester"
            upcoming_task = "Visit 'View Details' for medical advice."

        cursor.execute("SELECT * FROM health_checks WHERE user_name = %s ORDER BY check_date DESC LIMIT 5", (user_display_name,))
        history = cursor.fetchall()

        search_query = request.args.get('search', '').strip()
        if search_query:
            cursor.execute("SELECT * FROM faq WHERE question ILIKE %s", ('%' + search_query + '%',))
        else:
            cursor.execute("SELECT * FROM faq LIMIT 4")
        faqs = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('dashboard.html', 
                               user_name=user_display_name, weeks=weeks, 
                               trimester=trimester, due_date=due_date, 
                               progress=progress, upcoming_task=upcoming_task, 
                               history=history, faqs=faqs, search_query=search_query)
    except Exception as e:
        return f"<h1>Dashboard Error: {e}</h1>"

# --- 4. EXPERT Q&A ---
@app.route('/ask_expert', methods=['POST'])
def ask_expert():
    user_question = request.form.get('question')
    encoded_question = urllib.parse.quote_plus(user_question)
    return redirect(f"https://www.google.com/search?q={encoded_question}")

# --- 5. VIEW DETAILS ---
@app.route('/details/<int:week_num>')
def week_details(week_num):
    if 'user_name' not in session: return redirect(url_for('login_page'))
    user_display_name = session.get('user_name')
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if week_num <= 12:
        recom, trimester = "Focus on Folic Acid for neural development.", "1st Trimester"
    elif week_num <= 26:
        recom, trimester = "Increase Iron and Calcium intake.", "2nd Trimester"
    else:
        recom, trimester = "Eat smaller, frequent meals.", "3rd Trimester"

    baby_growth_details = {
        0: {"size": "Poppy Seed", "desc": "Cells are dividing rapidly."},
        8: {"size": "Raspberry", "desc": "Baby heart is beating strongly!"},
        12: {"size": "Lime", "desc": "Baby is now fully formed!"},
        20: {"size": "Banana", "desc": "You can start feeling kicks!"},
        32: {"size": "Squash", "desc": "Baby is gaining fat and muscle."},
        40: {"size": "Watermelon", "desc": "Ready for the world!"}
    }
    current_info = baby_growth_details.get(week_num, {"size": "Growing", "desc": "Developing more every day!"})

    vaccine_master_list = [(12, "TT 1", "Tetanus 1"), (16, "TT 2", "Tetanus 2"), (20, "Flu", "Flu Shot"), (28, "Tdap", "Booster")]
    cursor.execute("SELECT vaccine_name FROM user_vaccines WHERE user_name = %s AND week_at_completion = %s", (user_display_name, week_num))
    done_vaccines = [v['vaccine_name'] for v in cursor.fetchall()]

    vaccines_status = []
    for v_week, name, desc in vaccine_master_list:
        if v_week == week_num:
            status = "Done" if name in done_vaccines else "Pending"
            vaccines_status.append({'week': v_week, 'name': name, 'desc': desc, 'status': status})

    cursor.close()
    conn.close()
    return render_template('details.html', week=week_num, info=current_info, recom=recom, trimester=trimester, vaccines=vaccines_status)

# --- 6. MARK VACCINE DONE ---
@app.route('/complete_vaccine/<vaccine_name>/<int:week_num>')
def complete_vaccine(vaccine_name, week_num):
    if 'user_name' not in session: return redirect(url_for('login_page'))
    user_name = session.get('user_name')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_vaccines (user_name, vaccine_name, status, completed_at, week_at_completion) VALUES (%s, %s, 'Done', NOW(), %s)", (user_name, vaccine_name, week_num))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('week_details', week_num=week_num))

# --- 7. UTILITY ROUTES ---
@app.route('/update_lmp', methods=['POST'])
def update_lmp():
    if 'user_name' not in session: return redirect(url_for('login_page'))
    new_lmp = request.form.get('lmp_date')
    user_name = session.get('user_name')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET lmp_date = %s WHERE name = %s", (new_lmp, user_name))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/predict_page')
def predict_page(): 
    return render_template('predict.html')

@app.route('/predict', methods=['POST'])
def predict():
    systolic = int(request.form.get('systolic', 120))
    sugar = float(request.form.get('sugar', 5.0))
    user_name = session.get('user_name', 'Guest')
    result, color = ("High Risk", "#cf1322") if systolic > 140 or sugar > 10.0 else ("Mid Risk", "#d46b08") if systolic > 120 or sugar > 8.0 else ("Low Risk", "#389e0d")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO health_checks (user_name, systolic, sugar, risk_result, check_date) VALUES (%s, %s, %s, %s, NOW())", (user_name, systolic, sugar, result))
    conn.commit()
    cursor.close()
    conn.close()
    return f"""<div style="text-align:center; padding:50px; background:#fce4ec; height:100vh;"><h1 style='color:{color}'>{result}</h1><a href='/dashboard' style="padding:10px 20px; background:#ff69b4; color:white; text-decoration:none; border-radius:5px;">Return to Dashboard</a></div>"""

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

if __name__ == '__main__':
    app.run(debug=True)