from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'diamond_secret_key'

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Dummy user for login
users = {
    'Taha': '010923',
    'Mustafa': 'Musa90'
}

# ---------------------- SESSION TIMEOUT HANDLER -----------------------
@app.before_request
def check_session_timeout():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=3)

    now = datetime.utcnow()
    last_active = session.get('last_active')

    if 'username' in session:
        if last_active:
            try:
                last_active = datetime.strptime(last_active, "%Y-%m-%d %H:%M:%S")
                if now - last_active > timedelta(minutes=3):
                    session.clear()
                    return redirect(url_for('login'))
            except ValueError:
                session.clear()
                return redirect(url_for('login'))
        session['last_active'] = now.strftime("%Y-%m-%d %H:%M:%S")
# ----------------------------------------------------------------------

@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('home.html', username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['username'] = username
            session['last_active'] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])

@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session:
        return redirect(url_for('login'))

    file = request.files['file']
    if file and file.filename.endswith('.xlsx'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        session['excel_path'] = filepath
        flash('Excel file uploaded successfully!')
    else:
        flash('Invalid file format. Please upload a .xlsx file.')

    return redirect(url_for('current_standing'))

@app.route('/current-standing')
def current_standing():
    if 'username' not in session:
        return redirect(url_for('login'))

    if 'excel_path' not in session:
        return render_template('current_standing.html', username=session['username'], chart_data=None)

    filepath = session['excel_path']
    df = pd.read_excel(filepath, sheet_name=None)

    try:
        inventory_df = df['Inventory'].fillna('')
        sold_df = df.get('Sold List', pd.DataFrame()).fillna('')

        product_ids = inventory_df['Product ID'].tolist()
        product_names = inventory_df['Product Name'].tolist()
        quantities = inventory_df['Quantity'].tolist()

        sold_counts = sold_df['Product ID'].value_counts().to_dict()

        sold_data = []
        remaining_data = []
        best_seller = {"product_id": None, "quantity_sold": 0}

        for i, pid in enumerate(product_ids):
            sold_qty = sold_counts.get(pid, 0)
            remaining_qty = quantities[i] - sold_qty
            sold_data.append(sold_qty)
            remaining_data.append(remaining_qty)

            if sold_qty > best_seller["quantity_sold"]:
                best_seller["product_id"] = pid
                best_seller["quantity_sold"] = sold_qty

        chart_data = {
            "labels": product_ids,
            "names": product_names,
            "original": quantities,
            "sold": sold_data,
            "remaining": remaining_data,
            "best_seller": best_seller
        }

        return render_template("current_standing.html", username=session['username'], chart_data=chart_data)

    except KeyError:
        flash("Required sheets ('Inventory', 'Sold List') not found in Excel file.")
        return render_template("current_standing.html", username=session['username'], chart_data=None)
    except Exception as e:
        flash(f"An unexpected error occurred: {str(e)}")
        return render_template("current_standing.html", username=session['username'], chart_data=None)

