from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os
import urllib.parse

app = Flask(__name__)
app.secret_key = 'pregnancy_care_key_2026'

# --- DATABASE CONNECTION ---
def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        return psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    else:
        import mysql.connector
        return mysql.connector.connect(
            host="localhost", user="root", password="", database="pregnancy_db"
        )

# --- EMERGENCY SETUP ROUTE ---
@app.route('/setup-db-task-final')
def setup_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Update this variable to include the user_vaccines table
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
        CREATE TABLE IF NOT EXISTS faq (
            id SERIAL PRIMARY KEY, category VARCHAR(100), 
            question TEXT, answer TEXT
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
        return "<h1>Success! All tables (including Vaccines) are ready.</h1>"
    except Exception as e:
        return f"<h1>Setup Error: {e}</h1>"
    finally:
        cursor.close()
        conn.close()

# --- AUTHENTICATION ROUTES ---
@app.route('/')
def home():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    email = request.form['email'].strip().lower() 
    password = request.form['password']
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
        conn.commit()
        return redirect(url_for('login_page'))
    except Exception as err:
        return f"<h1>Registration Error: {err}</h1>"
    finally:
        cursor.close()
        conn.close()

@app.route('/login_page')
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email'].strip().lower()
    password = request.form['password']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
    user = cursor.fetchone()
    if user:
        session['user_name'] = user['name']
        return redirect(url_for('dashboard'))
    return "<h1>Invalid Login!</h1>"

# --- MAIN PAGES ---
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
        weeks = max(0, days_diff // 7) if days_diff // 7 <= 42 else 0 
        progress = min(int((weeks / 40) * 100), 100)
        due_date = (lmp + timedelta(days=280)).strftime('%B %d, %Y')
        trimester = "1st Trimester" if weeks <= 12 else "2nd Trimester" if weeks <= 26 else "3rd Trimester"

    cursor.close()
    conn.close()
    return render_template('dashboard.html', user_name=user_display_name, start_date=start_date,
                           weeks=weeks, trimester=trimester, due_date=due_date, progress=progress)
# --- [ADD THIS BELOW THE DASHBOARD ROUTE] ---

@app.route('/details/<int:week_num>')
def week_details(week_num):
    if 'user_name' not in session: return redirect(url_for('login_page'))
    user_display_name = session.get('user_name')
    
    # Recommendations based on Trimester
    if week_num <= 12:
        recom, trimester = "Focus on Folic Acid for neural development.", "1st Trimester"
    elif week_num <= 26:
        recom, trimester = "Increase Iron and Calcium intake.", "2nd Trimester"
    else:
        recom, trimester = "Eat smaller, frequent meals.", "3rd Trimester"

    # Baby Growth Data
    baby_growth_details = {
        0: {"size": "Poppy Seed", "desc": "Cells are dividing rapidly."},
        4: {"size": "Poppy Seed", "desc": "The blastocyst has arrived in the uterus."},
        8: {"size": "Raspberry", "desc": "Baby heart is beating strongly!"},
        12: {"size": "Lime", "desc": "Baby is now fully formed!"},
        16: {"size": "Avocado", "desc": "Baby can sense light and is moving fingers."},
        20: {"size": "Banana", "desc": "You can start feeling kicks!"},
        24: {"size": "Corn", "desc": "Baby's lungs are developing surfactant."},
        28: {"size": "Eggplant", "desc": "Baby's eyes are partially open."},
        32: {"size": "Squash", "desc": "Baby is gaining fat and muscle."},
        36: {"size": "Papaya", "desc": "Baby is taking up most of the space."},
        40: {"size": "Watermelon", "desc": "Ready for the world!"}
    }
    current_info = baby_growth_details.get(week_num, {"size": "Growing", "desc": "Developing more every day!"})

    # Vaccine Logic
    vaccine_master_list = [(12, "TT 1", "Tetanus 1"), (16, "TT 2", "Tetanus 2"), (20, "Flu", "Flu Shot"), (28, "Tdap", "Booster")]
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Ensure the user_vaccines table exists or handle the error
    try:
        cursor.execute("SELECT vaccine_name FROM user_vaccines WHERE user_name = %s AND week_at_completion = %s", (user_display_name, week_num))
        done_vaccines = [v['vaccine_name'] for v in cursor.fetchall()]
    except:
        done_vaccines = []
    
    vaccines_status = []
    for v_week, name, desc in vaccine_master_list:
        if v_week == week_num:
            status = "Done" if name in done_vaccines else "Pending"
            vaccines_status.append({'week': v_week, 'name': name, 'desc': desc, 'status': status})

    cursor.close()
    conn.close()
    return render_template('details.html', week=week_num, info=current_info, recom=recom, trimester=trimester, vaccines=vaccines_status)

# --- ADD THIS TO HANDLE THE VACCINE BUTTON CLICK ---
@app.route('/complete_vaccine/<vaccine_name>/<int:week_num>')
def complete_vaccine(vaccine_name, week_num):
    if 'user_name' not in session: return redirect(url_for('login_page'))
    user_name = session.get('user_name')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO user_vaccines (user_name, vaccine_name, status, week_at_completion) VALUES (%s, %s, 'Done', %s)", (user_name, vaccine_name, week_num))
        conn.commit()
    except Exception as e:
        print(f"Vaccine Error: {e}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('week_details', week_num=week_num))
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

@app.route('/faq_page')
def faq_page():
    if 'user_name' not in session: return redirect(url_for('login_page'))
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM faq")
    faqs = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('faq_page.html', faqs=faqs)

# --- ACTION ROUTES ---
@app.route('/predict', methods=['POST'])
def predict():
    systolic = int(request.form.get('systolic', 120))
    sugar = float(request.form.get('sugar', 5.0))
    user_name = session.get('user_name', 'Guest')
    result = "High Risk" if systolic > 140 or sugar > 10.0 else "Mid Risk" if systolic > 120 or sugar > 8.0 else "Low Risk"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO health_checks (user_name, systolic, sugar, risk_result, check_date) VALUES (%s, %s, %s, %s, NOW())", (user_name, systolic, sugar, result))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('predict_page'))

@app.route('/update_lmp', methods=['POST'])
def update_lmp():
    new_lmp = request.form.get('lmp_date')
    user_name = session.get('user_name')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET lmp_date = %s WHERE name = %s", (new_lmp, user_name))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/ask_expert', methods=['POST'])
def ask_expert():
    user_question = request.form.get('question')
    return redirect(f"https://www.google.com/search?q={urllib.parse.quote_plus(user_question)}")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

if __name__ == '__main__':
    app.run(debug=True)