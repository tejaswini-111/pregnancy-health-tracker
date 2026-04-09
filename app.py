import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
# Professional Tip: Use a real secret key or an environment variable
app.secret_key = os.environ.get('SECRET_KEY', 'maternal_care_secret_2026')

# --- DATABASE CONNECTION ---
def get_db_connection():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# --- INITIAL DATABASE SETUP ---
@app.route('/setup-db-task-final')
def setup_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql_commands = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, 
            name VARCHAR(100), 
            email VARCHAR(100) UNIQUE, 
            password VARCHAR(100), 
            lmp_date DATE
        );
        CREATE TABLE IF NOT EXISTS health_checks (
            id SERIAL PRIMARY KEY, 
            user_name VARCHAR(100), 
            systolic INT, 
            diastolic INT, 
            sugar FLOAT, 
            temp FLOAT, 
            heart_rate INT, 
            age INT,
            risk_result VARCHAR(50), 
            check_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_vaccines (
            id SERIAL PRIMARY KEY, 
            user_name VARCHAR(100), 
            vaccine_name VARCHAR(100), 
            status VARCHAR(50), 
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            week_at_completion INT
        );
        """
        cursor.execute(sql_commands)
        conn.commit()
        return "<h1>Success! Database Tables Updated.</h1>"
    except Exception as e:
        return f"<h1>Setup Error: {e}</h1>"
    finally:
        cursor.close()
        conn.close()

# --- ROUTES ---

@app.route('/')
def home():
    if 'user_name' in session:
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
        conn.commit()
        session['user_name'] = name
        return redirect(url_for('dashboard'))
    except Exception as e:
        return f"Registration Error: {e}"
    finally:
        cursor.close()
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user:
        session['user_name'] = user['name']
        return redirect(url_for('dashboard'))
    return "<h1>Invalid Credentials</h1><a href='/login_page'>Try Again</a>"

@app.route('/dashboard')
def dashboard():
    if 'user_name' not in session: return redirect(url_for('login_page'))
    user_display_name = session.get('user_name')
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT lmp_date FROM users WHERE name = %s", (user_display_name,))
    user_data = cursor.fetchone()
    
    weeks, progress, trimester = 0, 0, "Not Started"
    due_date, start_date = "N/A", "N/A"

    if user_data and user_data['lmp_date']:
        lmp = user_data['lmp_date']
        start_date = lmp.strftime('%B %d, %Y')
        days_diff = (datetime.now().date() - lmp).days
        # Logic: Pregnancy is max 42 weeks
        weeks = max(0, days_diff // 7)
        if weeks > 42: weeks = 0 
        
        progress = min(int((weeks / 40) * 100), 100)
        due_date = (lmp + timedelta(days=280)).strftime('%B %d, %Y')
        trimester = "1st Trimester" if weeks <= 12 else "2nd Trimester" if weeks <= 26 else "3rd Trimester"

    cursor.close()
    conn.close()
    return render_template('dashboard.html', user_name=user_display_name, start_date=start_date,
                           weeks=weeks, trimester=trimester, due_date=due_date, progress=progress)

@app.route('/update_lmp', methods=['POST'])
def update_lmp():
    if 'user_name' not in session: return redirect(url_for('login_page'))
    new_lmp = request.form.get('lmp_date')
    user_name = session.get('user_name')
    
    if new_lmp:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Update database
        cursor.execute("UPDATE users SET lmp_date = %s WHERE name = %s", (new_lmp, user_name))
        conn.commit()
        cursor.close()
        conn.close()
    
    return redirect(url_for('dashboard'))

@app.route('/predict_page')
def predict_page():
    if 'user_name' not in session: return redirect(url_for('login_page'))
    user_name = session.get('user_name')
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM health_checks WHERE user_name = %s ORDER BY check_date DESC", (user_name,))
    history = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('predict.html', history=history)

@app.route('/predict', methods=['POST'])
def predict():
    if 'user_name' not in session: return redirect(url_for('login_page'))
    user_name = session.get('user_name')
    
    systolic = int(request.form.get('systolic', 120))
    diastolic = int(request.form.get('diastolic', 80))
    sugar = float(request.form.get('sugar', 5.0))
    temp = float(request.form.get('temp', 37.0))
    heart_rate = int(request.form.get('heart_rate', 70))
    age = int(request.form.get('age', 25))

    if systolic >= 140 or sugar >= 10.0 or temp >= 38.0:
        result, color = "High Risk", "#cf1322"
        advice = "Urgent: Please contact your doctor. Vitals are outside safe ranges."
    elif systolic >= 130 or sugar >= 8.5 or heart_rate >= 100:
        result, color = "Mid Risk", "#d46b08"
        advice = "Caution: Monitor your vitals closely."
    else:
        result, color = "Low Risk", "#389e0d"
        advice = "Stable: Your vitals are looking good."

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO health_checks (user_name, systolic, diastolic, sugar, temp, heart_rate, age, risk_result) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (user_name, systolic, diastolic, sugar, temp, heart_rate, age, result))
    conn.commit()

    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM health_checks WHERE user_name = %s ORDER BY check_date DESC", (user_name,))
    history = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return render_template('predict.html', history=history, latest_result=result, result_color=color, advice=advice)

@app.route('/details/<int:week_num>')
def week_details(week_num):
    if 'user_name' not in session: return redirect(url_for('login_page'))
    user_name = session.get('user_name')
    
    baby_growth = {
        0: {"size": "Poppy Seed", "desc": "Implantation is occurring."},
        4: {"size": "Poppy Seed", "desc": "Major organs begin to form."},
        8: {"size": "Raspberry", "desc": "Baby heart is beating!"},
        12: {"size": "Lime", "desc": "Baby is fully formed."},
        16: {"size": "Avocado", "desc": "Baby can sense light."},
        20: {"size": "Banana", "desc": "First movements felt."},
        24: {"size": "Corn", "desc": "Lungs are developing."},
        28: {"size": "Eggplant", "desc": "Dreaming begins."},
        32: {"size": "Squash", "desc": "Gaining fat layer."},
        36: {"size": "Papaya", "desc": "Lungs nearly mature."},
        40: {"size": "Watermelon", "desc": "Ready for birth!"}
    }
    # Logic to find the nearest lower key
    sorted_keys = sorted(baby_growth.keys())
    effective_week = 0
    for k in sorted_keys:
        if k <= week_num:
            effective_week = k
            
    info = baby_growth.get(effective_week)
    
    recom = "Maintain a healthy diet and stay active."
    trimester = "1st Trimester" if week_num <= 12 else "2nd Trimester" if week_num <= 26 else "3rd Trimester"

    v_list = [(12, "TT 1", "Tetanus Toxoid 1"), (16, "TT 2", "Tetanus Toxoid 2"), (20, "Flu", "Flu Shot"), (28, "Tdap", "Pertussis Booster")]
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT vaccine_name FROM user_vaccines WHERE user_name = %s", (user_name,))
    done = [v['vaccine_name'] for v in cursor.fetchall()]
    
    vaccines = []
    for w, n, d in v_list:
        vaccines.append({'week': w, 'name': n, 'desc': d, 'status': 'Done' if n in done else 'Pending'})

    cursor.close()
    conn.close()
    return render_template('details.html', week=week_num, info=info, recom=recom, trimester=trimester, vaccines=vaccines)

@app.route('/complete_vaccine/<v_name>/<int:w_num>')
def complete_vaccine(v_name, w_num):
    if 'user_name' not in session: return redirect(url_for('login_page'))
    user_name = session.get('user_name')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_vaccines (user_name, vaccine_name, status, week_at_completion) VALUES (%s, %s, 'Done', %s)", (user_name, v_name, w_num))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('week_details', week_num=w_num))

@app.route('/faq_page')
def faq_page():
    if 'user_name' not in session: return redirect(url_for('login_page'))
    medical_faqs = [
        "Normal blood pressure during pregnancy",
        "Safe exercises for 2nd trimester",
        "Signs of gestational diabetes",
        "Foods to avoid during pregnancy",
        "How much water should a pregnant woman drink",
        "Standard pregnancy vaccination schedule"
    ]
    return render_template('faq.html', questions=medical_faqs)
@app.route('/nutrition_page')
def nutrition_page():
    if 'user_name' not in session: 
        return redirect(url_for('login_page'))
    return render_template('nutrition.html')
@app.route('/medication_reminder')
def medication_reminder():
    if 'user_name' not in session: 
        return redirect(url_for('login_page'))
    
    prescriptions = [
        {"name": "Folic Acid", "dosage": "400mcg", "time": "08:00", "display_time": "08:00 AM", "instruction": "Before breakfast", "days": "Daily"},
        {"name": "Iron Tablet", "dosage": "20mg", "time": "14:00", "display_time": "02:00 PM", "instruction": "Avoid dairy for 2 hours", "days": "Daily"},
        {"name": "Calcium", "dosage": "500mg", "time": "20:00", "display_time": "08:00 PM", "instruction": "After dinner", "days": "Daily"}
    ]
    return render_template('reminders.html', prescriptions=prescriptions)
@app.route('/login_page')
def login_page():
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

if __name__ == '__main__':
    app.run(debug=True)