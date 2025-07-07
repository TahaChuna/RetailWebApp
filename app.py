from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import pandas as pd
import os
from io import BytesIO
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

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
    return render_template("invoice.html", product_price_dict=product_price_dict)

@app.route('/generate_invoice', methods=['POST'])
def generate_invoice():
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle, Paragraph, SimpleDocTemplate
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from io import BytesIO
    from datetime import datetime

    # Get form data
    customer_name = request.form.get('customer_name')
    customer_number = request.form.get('customer_number')
    product_ids = request.form.getlist('product_ids[]')
    product_prices = request.form.getlist('product_prices[]')
    discount_percentage = float(request.form.get('discount') or 0)

    # Build product data
    products = []
    subtotal = 0
    for pid, price in zip(product_ids, product_prices):
        qty = 1
        amount = float(price)
        subtotal += amount
        products.append([pid, qty, f"₹ {price}", f"₹ {price}"])

    discount_amount = subtotal * (discount_percentage / 100)
    total_due = subtotal - discount_amount

    # Create PDF buffer
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # ===== HEADER =====
    c.setFont("Helvetica-Bold", 40)
    c.setFillColor(colors.HexColor("#000000"))
    c.drawString(40, height - 60, "INVOICE")

    # Customer name below INVOICE
    c.setFont("Helvetica", 14)
    c.setFillColor(colors.black)
    c.drawString(40, height - 90, f"Customer: {customer_name} | Mobile: {customer_number}")

    # Issued By on right
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - 40, height - 60, "ISSUED BY:")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 40, height - 75, "DIAMOND KIDS WEAR AND ESSENTIALS")
    c.drawRightString(width - 40, height - 90, "THANE - 400601")
    c.drawRightString(width - 40, height - 105, "Mobile No: 9920752179")

    # Invoice details
    bill_number = get_next_bill_number()
    c.setFont("Helvetica", 10)
    c.drawString(40, height - 120, f"Invoice No: {bill_number}")
    c.drawString(200, height - 120, f"Date: {datetime.today().strftime('%d %b %Y')}")

    # ===== TABLE =====
    data = [["POS", "DESCRIPTION", "QTY", "PRICE", "AMOUNT"]]
    for i, row in enumerate(products, 1):
        data.append([str(i), row[0], str(row[1]), row[2], row[3]])

    table = Table(data, colWidths=[30, 200, 50, 80, 80])
    style = TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (2,1), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
    ])
    table.setStyle(style)

    table.wrapOn(c, width, height)
    table_height = 20 * len(data)
    table.drawOn(c, 40, height - 150 - table_height)

    # ===== TOTALS =====
    y = height - 160 - table_height - 10
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - 40, y, f"Subtotal: ₹ {subtotal:.2f}")
    y -= 15
    c.drawRightString(width - 40, y, f"Discount ({discount_percentage}%): ₹ {discount_amount:.2f}")
    y -= 15
    c.drawRightString(width - 40, y, f"Total Amount to be Paid: ₹ {total_due:.2f}")

    # ===== WATERMARK =====
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.lightgrey)
    c.drawCentredString(width/2, 60, "Thank you for shopping with DIAMOND KIDS WEAR! Adios!")

    # Finish PDF
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

    customer_data = [
        {'name': 'Amit', 'mobile': '9876543210', 'bills': ['INV001', 'INV004']},
        {'name': 'Rita', 'mobile': '9123456780', 'bills': ['INV002']}
    ]
    return render_template('customer_database.html', customer_data=customer_data)

@app.route('/export_customers', methods=['POST'])
def export_customers():
    if 'user' not in session:
        return redirect(url_for('login'))

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
