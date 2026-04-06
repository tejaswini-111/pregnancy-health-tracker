from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'pregnancy_care_key_2024'

# --- SMART DATABASE CONNECTION ---
def get_db_connection():
    # Render automatically provides this "DATABASE_URL" environment variable
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

@app.route('/')
def home():
    return render_template('register.html')

# --- 1. REGISTRATION ---
@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    email = request.form['email']
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
    email = request.form['email']
    password = request.form['password']
    conn = get_db_connection()
    # Using cursor_factory here ensures we get results as a dictionary
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
    return "<h1>Invalid Login!</h1>"

# --- 3. DASHBOARD ---
@app.route('/dashboard')
def dashboard():
    if 'user_name' not in session:
        return redirect(url_for('login_page'))

    user_display_name = session.get('user_name')
    
    try:
        conn = get_db_connection()
        # REMOVED: buffered=True (Not supported in PostgreSQL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Pregnancy Tracking Logic
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
            weeks = max(0, days_diff // 7)
            progress = min(int((weeks / 40) * 100), 100)
            due_date = (lmp + timedelta(days=280)).strftime('%B %d, %Y')
            trimester = "1st Trimester" if weeks <= 12 else "2nd Trimester" if weeks <= 26 else "3rd Trimester"
            upcoming_task = "Visit 'View Details' for medical advice."

        # 2. Health History
        cursor.execute("SELECT * FROM health_checks WHERE user_name = %s ORDER BY check_date DESC LIMIT 5", (user_display_name,))
        history = cursor.fetchall()

        # 3. FAQ Logic
        search_query = request.args.get('search', '').strip()
        if search_query:
            cursor.execute("SELECT * FROM faq WHERE question LIKE %s", ('%' + search_query + '%',))
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

# --- 4. VIEW DETAILS ---
@app.route('/details/<int:week_num>')
def week_details(week_num):
    if 'user_name' not in session:
        return redirect(url_for('login_page'))

    user_display_name = session.get('user_name')
    conn = get_db_connection()
    # REMOVED: buffered=True
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # 1. Trimester Logic
    if week_num <= 12:
        recom = "Focus on Folic Acid (Spinach, Beans) for neural development."
        trimester = "1st Trimester"
    elif week_num <= 26:
        recom = "Increase Iron and Calcium intake for growing bones and blood supply."
        trimester = "2nd Trimester"
    else:
        recom = "Eat smaller, frequent meals as the baby takes up more space."
        trimester = "3rd Trimester"

    # 2. Baby Growth Data
    baby_growth_details = {
        0: {"size": "Poppy Seed", "desc": "Cells are dividing rapidly."},
        8: {"size": "Raspberry", "desc": "Baby's heart is beating strongly!"},
        12: {"size": "Lime", "desc": "Baby is now fully formed!"},
        20: {"size": "Banana", "desc": "You can start feeling kicks!"},
        32: {"size": "Squash", "desc": "Baby is gaining fat and muscle."},
        40: {"size": "Watermelon", "desc": "Ready for the world!"}
    }
    
    current_info = baby_growth_details.get(week_num, {"size": "Growing", "desc": "Developing more every day!"})

    # 3. Vaccination Logic
    vaccine_master_list = [
        (12, "TT 1", "Tetanus Toxoid 1st dose"),
        (16, "TT 2", "Tetanus Toxoid 2nd dose"),
        (20, "Flu Shot", "Seasonal Influenza Protection"),
        (28, "Tdap", "Pertussis & Tetanus Booster")
    ]

    cursor.execute("""
        SELECT vaccine_name FROM user_vaccines 
        WHERE user_name = %s AND week_at_completion = %s
    """, (user_display_name, week_num))
    
    done_vaccines = [v['vaccine_name'] for v in cursor.fetchall()]

    vaccines_status = []
    for v_week, name, desc in vaccine_master_list:
        if v_week == week_num:
            status = "Done" if name in done_vaccines else "Pending"
            vaccines_status.append({'week': v_week, 'name': name, 'desc': desc, 'status': status})

    cursor.close()
    conn.close()

    return render_template('details.html', 
                           week=week_num, 
                           info=current_info, 
                           recom=recom, 
                           trimester=trimester, 
                           vaccines=vaccines_status)

# --- 5. MARK VACCINE DONE ---
@app.route('/complete_vaccine/<vaccine_name>/<int:week_num>')
def complete_vaccine(vaccine_name, week_num):
    if 'user_name' not in session: 
        return redirect(url_for('login_page'))
    
    user_name = session.get('user_name')
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """INSERT INTO user_vaccines 
               (user_name, vaccine_name, status, completed_at, week_at_completion) 
               VALUES (%s, %s, 'Done', NOW(), %s)"""
    
    cursor.execute(query, (user_name, vaccine_name, week_num))
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for('week_details', week_num=week_num))

# --- 6. OTHER ROUTES ---
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
    age = int(request.form.get('age', 25))
    systolic = int(request.form.get('systolic', 120))
    sugar = float(request.form.get('sugar', 5.0))
    user_name = session.get('user_name', 'Guest')
    
    result, color = ("High Risk", "red") if systolic > 140 or sugar > 10.0 else ("Mid Risk", "orange") if systolic > 120 or sugar > 8.0 else ("Low Risk", "green")
    
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