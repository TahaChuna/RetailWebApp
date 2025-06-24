import pandas as pd
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_default_secret')

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

@app.route('/current-standing', methods=['GET', 'POST'])
def current_standing():
    if 'user' not in session:
        return redirect(url_for('login'))

    chart_data = None
    inventory_data = None

    # If a file is uploaded via POST, use that file
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.xlsx'):
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
        else:
            flash("Please upload a valid .xlsx file.")
            return redirect(url_for('current_standing'))
    else:
        # Fallback: Get the latest file uploaded
        uploaded_files = sorted(os.listdir(UPLOAD_FOLDER), reverse=True)
        if not uploaded_files:
            flash("No file uploaded yet.")
            return redirect(url_for('dashboard'))
        filepath = os.path.join(UPLOAD_FOLDER, uploaded_files[0])

    try:
        xls = pd.ExcelFile(filepath)
        inventory_df = xls.parse('Inventory').fillna(0)
        sales_df = xls.parse('Sales').fillna(0)

        inventory_data = inventory_df.to_dict(orient='records')

        # Calculate total sold per product
        sold_summary = sales_df.groupby('Product ID')['Quantity'].sum().reset_index()
        sold_summary.columns = ['Product ID', 'Quantity Sold']

        # Merge with inventory to get remaining stock
        merged_df = pd.merge(inventory_df, sold_summary, on='Product ID', how='left')
        merged_df['Quantity Sold'] = merged_df['Quantity Sold'].fillna(0)
        merged_df['Quantity Remaining'] = merged_df['Quantity'] - merged_df['Quantity Sold']

        # Best-selling product
        best_seller = merged_df.sort_values(by='Quantity Sold', ascending=False).iloc[0]

        # Prepare chart data
        # Prepare chart data
        chart_data = {
            'labels': merged_df['Product ID'].tolist(),
            'names': merged_df['Product Name'].tolist(),
            'original': merged_df['Quantity'].tolist(),
            'sold': merged_df['Quantity Sold'].tolist(),
            'remaining': merged_df['Quantity Remaining'].tolist(),
            'best_seller': {
                'product_id': best_seller['Product ID'],
                'quantity_sold': int(best_seller['Quantity Sold'])
            }
        }
        return render_template(
            'current_standing.html',
            chart_data=chart_data,
            inventory=inventory_data,
            username=session['user']
        )

    except Exception as e:
        flash(f"Error processing data: {e}")
        return redirect(url_for('dashboard'))

# ✅ Only run this locally (Render will ignore it)
if __name__ == '__main__':
    app.run(debug=True)
