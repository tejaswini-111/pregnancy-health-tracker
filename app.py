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

# --- 1. THE MAIN DASHBOARD ---
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

# --- 2. THE HEALTH TRACKER PAGE (Modularized) ---
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

# --- 3. THE MEDICAL FAQ PAGE (Modularized) ---
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

# --- 4. DATA PROCESSING ROUTES ---
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

# (Keep your setup-db and register/login routes as they were)