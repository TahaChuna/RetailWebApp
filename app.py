from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import pandas as pd
import os
from io import BytesIO
from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.debug = True
app.secret_key = 'supersecretkey'  # Replace with a strong key in production

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Dummy login system
users = {'Taha': '010923', 'Mustafa': 'Musa123'}

# Dummy product data (to be dynamically loaded later)
product_price_dict = {}

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in users and users[username] == password:
            session['user'] = username
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/current_standing', methods=['GET', 'POST'])
def current_standing():
    if 'user' not in session:
        return redirect(url_for('login'))

    upload_success = False
    products = []
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
            for _, row in df.iterrows():
                try:
                    product = {
                        'id': row['Product ID'],
                        'name': row['Product Name'],
                        'qty_sold': row['Quantity Sold'],
                        'qty_remaining': row['Remaining Quantity'],
                        'cost_price': row['Cost Price'],
                        'selling_price': row['Selling Price'],
                        'total_sales': row['Selling Price'] * row['Quantity Sold'],
                        'profit': (row['Selling Price'] - row['Cost Price']) * row['Quantity Sold']
                    }
                    products.append(product)
                except KeyError:
                    flash('Invalid Excel format. Please upload with proper headers.', 'error')
                    break
            upload_success = True
        else:
            flash('Only .xlsx files are supported.', 'error')

    return render_template('current_standing.html', upload_success=upload_success, products=products)

@app.route('/invoice', methods=['GET'])
def invoice():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('invoice.html', product_price_dict=product_price_dict)

@app.route('/generate_invoice', methods=['POST'])
def generate_invoice():
    customer_name = request.form['customer_name']
    customer_number = request.form.get('customer_number', '')
    discount = float(request.form.get('discount', 0))
    payment_type = request.form['payment_type']

    product_ids = request.form.getlist('product_ids[]')
    product_prices = request.form.getlist('product_prices[]')

    # Compute total
    total = 0
    products = []
    for pid, price in zip(product_ids, product_prices):
        p = {
            'id': pid,
            'price': float(price)
        }
        products.append(p)
        total += p['price']

    discounted_total = total - (total * discount / 100)

    # Generate PDF
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(width / 2, y, "DIAMOND KIDS WEAR & ESSENTIALS")

    y -= 30
    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Customer Name: {customer_name}")
    y -= 20
    p.drawString(50, y, f"Customer Phone: {customer_number}")
    y -= 30

    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Products:")
    y -= 20

    p.setFont("Helvetica", 12)
    for prod in products:
        p.drawString(60, y, f"Product ID: {prod['id']} - Price: ₹{prod['price']:.2f}")
        y -= 20

    y -= 10
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, f"Discount: {discount}%")
    y -= 20
    p.drawString(50, y, f"TOTAL: ₹{discounted_total:.2f}")

    y -= 30
    p.drawString(50, y, f"Payment Method: {payment_type}")

    p.showPage()
    p.save()

    buffer.seek(0)

    # Send PDF as download
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Invoice_{customer_name.replace(' ','_')}.pdf",
        mimetype='application/pdf'
    )

    try:
        customer_name = request.form.get('customer_name')
        customer_number = request.form.get('customer_number')
        product_ids = request.form.getlist('product_ids[]')
        prices = request.form.getlist('product_prices[]')
        discount = float(request.form.get('discount', 0))
        payment_type = request.form.get('payment_type')

        if not customer_name or not product_ids or not prices:
            flash('Missing invoice data', 'error')
            return redirect(url_for('invoice'))

        total = sum([float(p) for p in prices if p.strip()])
        final_total = total - (total * discount / 100)

        # You can add logic to save invoices here

        flash(f"Invoice generated successfully! Total: ₹{final_total:.2f}", "success")
        return redirect(url_for('invoice'))

    except Exception as e:
        flash(f"Invoice generation failed: {str(e)}", 'error')
        return redirect(url_for('invoice'))

@app.route('/customer_database')
def customer_database():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Dummy customer data for now
    customer_data = [
        {'name': 'Amit', 'mobile': '9876543210', 'bills': ['INV001', 'INV004']},
        {'name': 'Rita', 'mobile': '9123456780', 'bills': ['INV002']}
    ]
    return render_template('customer_database.html', customer_data=customer_data)

@app.route('/export_customers', methods=['POST'])
def export_customers():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Dummy data
    customer_data = [
        {'Name': 'Amit', 'Mobile': '9876543210', 'Bills': 'INV001, INV004'},
        {'Name': 'Rita', 'Mobile': '9123456780', 'Bills': 'INV002'},
    ]
    df = pd.DataFrame(customer_data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Customers')
    output.seek(0)
    return send_file(output, download_name='customers.xlsx', as_attachment=True)

import logging
logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
    app.run(debug=True)
