from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
from werkzeug.utils import secure_filename
import os
from collections import defaultdict

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


@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    data = {}
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.xlsx'):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            df = pd.read_excel(filepath, sheet_name=None)

            # Store in session temporarily
            session['excel_path'] = filepath

            # Parse inventory sheet
            inventory = df.get('Inventory', pd.DataFrame()).fillna('')
            data['inventory'] = inventory.to_dict(orient='records')

    elif 'excel_path' in session:
        filepath = session['excel_path']
        df = pd.read_excel(filepath, sheet_name=None)
        inventory = df.get('Inventory', pd.DataFrame()).fillna('')
        data['inventory'] = inventory.to_dict(orient='records')

    return render_template('dashboard.html', username=session['username'], data=data)

@app.route('/current-standing')
def current_standing():
    if 'username' not in session or 'excel_path' not in session:
        return redirect(url_for('dashboard'))

    filepath = session['excel_path']
    df = pd.read_excel(filepath, sheet_name=None)

    try:
        inventory_df = df['Inventory'].fillna('')
        sold_df = df.get('Sold List', pd.DataFrame()).fillna('')
    except KeyError:
        return "Required sheets ('Inventory', 'Sold List') not found in Excel file."

    # Preparing data
    product_data = defaultdict(lambda: {
        'product_id': '',
        'product_name': '',
        'original_quantity': 0,
        'quantity_sold': 0,
        'quantity_remaining': 0
    })

    for _, row in inventory_df.iterrows():
        pid = str(row.get('Product ID', '')).strip()
        pname = str(row.get('Product Name', '')).strip()
        qty = int(row.get('Quantity Available', 0))
        product_data[pid].update({
            'product_id': pid,
            'product_name': pname,
            'original_quantity': qty,
            'quantity_remaining': qty
        })

    for _, row in sold_df.iterrows():
        pid = str(row.get('Product ID', '')).strip()
        qty_sold = int(row.get('Quantity Sold', 0))
        if pid in product_data:
            product_data[pid]['quantity_sold'] += qty_sold
            product_data[pid]['quantity_remaining'] -= qty_sold
        else:
            product_data[pid] = {
                'product_id': pid,
                'product_name': '',
                'original_quantity': 0,
                'quantity_sold': qty_sold,
                'quantity_remaining': -qty_sold
            }

    products = list(product_data.values())

    # Find best seller
    best_seller = max(products, key=lambda x: x['quantity_sold'], default={
        'product_id': 'N/A', 'quantity_sold': 0
    })

    chart_data = {
        'labels': [p['product_id'] for p in products],
        'names': [p['product_name'] for p in products],
        'original': [p['original_quantity'] for p in products],
        'sold': [p['quantity_sold'] for p in products],
        'remaining': [p['quantity_remaining'] for p in products],
        'best_seller': best_seller
    }

    return render_template('current_standing.html', username=session['username'], chart_data=chart_data)

if __name__ == '__main__':
    app.run(debug=True)
