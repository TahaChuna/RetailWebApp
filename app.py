from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import pandas as pd
import os
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

@app.route('/invoice', methods=['GET'])
def invoice():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('invoice.html', product_price_dict=product_price_dict)

@app.route('/generate_invoice', methods=['POST'])
def generate_invoice():
    customer_name = request.form.get('customer_name')
    customer_number = request.form.get('customer_number')
    product_ids = request.form.getlist('product_ids[]')
    product_prices = request.form.getlist('product_prices[]')
    discount_percentage = float(request.form.get('discount') or 0)

    bill_number = get_next_bill_number()

    # Calculate totals
    prices = [float(p) for p in product_prices]
    subtotal = sum(prices)
    discount_amount = subtotal * discount_percentage / 100
    total = subtotal - discount_amount

    # Create PDF
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Logo (if you have a logo.png in your project)
    # pdf.drawImage("logo.png", 40, height - 100, width=100, preserveAspectRatio=True, mask='auto')

    # Store name
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawCentredString(width / 2, height - 60, "DIAMOND KIDS WEAR & ESSENTIALS")

    # Invoice details
    pdf.setFont("Helvetica", 12)
    pdf.drawString(40, height - 90, f"Invoice #: {bill_number}")
    pdf.drawString(300, height - 90, f"Date: {datetime.now().strftime('%d-%m-%Y')}")

    # Customer info
    pdf.drawString(40, height - 120, f"Customer: {customer_name}")
    if customer_number:
        pdf.drawString(300, height - 120, f"Phone: {customer_number}")

    # Table headers and data
    data = [["Sr", "Product ID", "Price (₹)"]]
    for i, (pid, price) in enumerate(zip(product_ids, product_prices), start=1):
        data.append([str(i), pid, price])

    table = Table(data, colWidths=[40, 250, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('BACKGROUND',(0,1),(-1,-1),colors.beige),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
    ]))
    table.wrapOn(pdf, width, height)
    table_height = 200 + 20 * len(data)
    table.drawOn(pdf, 40, height - table_height)

    # Summary
    summary_y = height - table_height - 40
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(300, summary_y, f"Subtotal: ₹{subtotal:.2f}")
    pdf.drawString(300, summary_y - 20, f"Discount ({discount_percentage}%): -₹{discount_amount:.2f}")
    pdf.drawString(300, summary_y - 40, f"Total Amount: ₹{total:.2f}")

    # Footer
    pdf.setFont("Helvetica-Oblique", 10)
    pdf.drawCentredString(width / 2, 30, "Thank you for shopping with us!")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    filename = f"Invoice_{bill_number}.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
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
