from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import pandas as pd
import os
from flask import request, send_file
from io import BytesIO
from datetime import datetime

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

def get_next_bill_number():
    filename = 'last_bill_number.txt'
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            f.write('1')
        return 1
    with open(filename, 'r') as f:
        number = int(f.read().strip())
    with open(filename, 'w') as f:
        f.write(str(number + 1))
    return number

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

from flask import Flask, render_template, request, send_file
import os

app = Flask(__name__)

# Dummy product price dict to avoid error
product_price_dict = {}

# Bill number generator
def get_next_bill_number():
    filename = 'last_bill_number.txt'
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            f.write('1')
        return 1
    with open(filename, 'r') as f:
        number = int(f.read().strip())
    with open(filename, 'w') as f:
        f.write(str(number + 1))
    return number

# Route to serve invoice form page
@app.route('/invoice', methods=['GET'])
def invoice():
    return render_template("invoice.html", product_price_dict=product_price_dict)

# Route to handle invoice generation
@app.route('/generate_invoice', methods=['POST'])
def generate_invoice():
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle
    from io import BytesIO
    from datetime import datetime

    customer_name = request.form.get('customer_name')
    customer_number = request.form.get('customer_number')
    product_ids = request.form.getlist('product_ids[]')
    product_prices = request.form.getlist('product_prices[]')
    discount_percentage = float(request.form.get('discount') or 0)

    products = []
    for pid, price in zip(product_ids, product_prices):
        products.append({"id": pid, "price": price})

    bill_number = get_next_bill_number()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Header
    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(colors.HexColor("#333333"))
    c.drawString(40, height - 70, "INVOICE")

    c.setFont("Helvetica", 12)
    c.drawString(40, height - 95, "Diamond Kids Wear & Essentials")
    c.drawString(40, height - 110, "123 Main Street, City, Country")
    c.drawString(40, height - 125, "Phone: +91-XXXXXXXXXX")
    c.drawString(40, height - 140, f"Invoice #: {bill_number}")
    c.drawString(40, height - 155, f"Date: {datetime.today().strftime('%d %b %Y')}")

    # Customer details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, height - 95, "Billed To:")
    c.setFont("Helvetica", 12)
    c.drawString(350, height - 110, customer_name)
    if customer_number:
        c.drawString(350, height - 125, f"Mobile: {customer_number}")

    data = [["#", "Description", "Quantity", "Unit Price", "Amount"]]
    subtotal = 0
    for i, prod in enumerate(products, start=1):
        qty = 1
        amount = float(prod["price"])
        subtotal += amount
        data.append([str(i), prod["id"], str(qty), f"₹ {prod['price']}", f"₹ {prod['price']}"])

    discount_amount = subtotal * (discount_percentage / 100)
    total_due = subtotal - discount_amount

    table = Table(data, colWidths=[30, 220, 70, 80, 80])
    style = TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (2,1), (-1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ])
    table.setStyle(style)
    table.wrapOn(c, width, height)
    table.drawOn(c, 40, height - 400)

    y = height - 420 - (20 * len(products))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, y, f"Subtotal: ₹ {subtotal:.2f}")
    y -= 20
    c.drawString(350, y, f"Discount ({discount_percentage}%): ₹ {discount_amount:.2f}")
    y -= 20
    c.drawString(350, y, f"Total Due: ₹ {total_due:.2f}")

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.grey)
    c.drawString(40, 40, "Thank you for shopping with us!")

    c.save()
    buffer.seek(0)

    filename = f"Invoice_{bill_number}.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )
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
