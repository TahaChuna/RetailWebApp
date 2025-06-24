import pandas as pd
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin':
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Please try again.')
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    data = {}
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.xlsx'):
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)

            try:
                xls = pd.ExcelFile(filepath)
                if 'Inventory' in xls.sheet_names:
                    data['inventory'] = xls.parse('Inventory').fillna('').to_dict(orient='records')
                if 'Sales' in xls.sheet_names:
                    data['sales'] = xls.parse('Sales').fillna('').to_dict(orient='records')
                if 'Current Standings' in xls.sheet_names:
                    data['current_standings'] = xls.parse('Current Standings').fillna('').to_dict(orient='records')
            except Exception as e:
                flash(f"Error reading file: {e}")
        else:
            flash("Please upload a valid .xlsx file.")

    return render_template('dashboard.html', data=data, username=session['user'])

@app.route('/current-standing')
def current_standing():
    return "<h2>Current Standing Of The Business (Coming Soon)</h2>"

@app.route('/inventory')
def inventory():
    return "<h2>Current Inventory (Coming Soon)</h2>"

@app.route('/sales')
def sales():
    return "<h2>Today's Sales (Coming Soon)</h2>"

@app.route('/invoice')
def invoice():
    return "<h2>Invoice Generator (Coming Soon)</h2>"

@app.route('/customers')
def customers():
    return "<h2>Customer Database (Coming Soon)</h2>"

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
