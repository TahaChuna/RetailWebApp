from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import pandas as pd
import os
import json
from io import BytesIO
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.debug = True
app.secret_key = 'supersecretkey'  # Replace with a strong key in production

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///invoices.db'
db = SQLAlchemy(app)

# Invoice Model
class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    bill_number = db.Column(db.Integer, unique=True, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    customer_name = db.Column(db.String, nullable=False)
    customer_number = db.Column(db.String, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    discount_percentage = db.Column(db.Float, nullable=False)
    total_due = db.Column(db.Float, nullable=False)
    items_json = db.Column(db.Text, nullable=False)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Dummy login credentials
users = {'Taha': '010923', 'Mustafa': 'Musa123'}

# Dummy product data
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

@app.route('/generate_invoice', methods=['POST'])
def generate_invoice():
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
        products.append([pid, qty, "Rs. {:.2f}".format(price), "Rs. {:.2f}".format(amount)])

    discount_amount = subtotal * (discount_percentage / 100)
    total_due = subtotal - discount_amount

    # Create PDF buffer
    buffer = BytesIO()
    PAGE_WIDTH = 400
    PAGE_HEIGHT = 500
    c = canvas.Canvas(buffer, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    y = PAGE_HEIGHT - 30

    # Header Box
    c.setFillColor(colors.HexColor("#FFB6C1"))
    c.roundRect(10, y - 60, PAGE_WIDTH - 20, 60, 10, fill=1)
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.darkblue)
    c.drawCentredString(PAGE_WIDTH / 2, y - 20, "🌟 DIAMOND KIDS WEAR & ESSENTIALS 🌟")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.black)
    c.drawCentredString(PAGE_WIDTH / 2, y - 35, "Shiv Shree APT, Shop No 4, K-Villa, Rabodi, 400601")
    c.drawCentredString(PAGE_WIDTH / 2, y - 47, "Mobile: 9920752179")
    y -= 75

    # Invoice Info
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.black)
    bill_number = get_next_bill_number()
    c.drawString(20, y, f"Invoice No: {bill_number}")
    c.drawRightString(PAGE_WIDTH - 20, y, f"Date: {datetime.today().strftime('%d-%b-%Y')}")
    y -= 20

    # Customer Info Box
    c.setFillColor(colors.HexColor("#FFFACD"))
    c.roundRect(10, y - 30, PAGE_WIDTH - 20, 30, 5, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(20, y - 10, f"Customer Name: {customer_name}")
    c.drawString(20, y - 22, f"Mobile No: {customer_number}")
    y -= 50

    # Table Data
    data = [["S.No", "Description", "Qty", "Unit Price", "Amount"]]
    for i, row in enumerate(products, 1):
        data.append([str(i), row[0], str(row[1]), row[2], row[3]])
    data.append(["", "", "", "Subtotal", "Rs. {:.2f}".format(subtotal)])
    data.append(["", "", "", f"Discount ({discount_percentage}%)", "-Rs. {:.2f}".format(discount_amount)])
    data.append(["", "", "", "TOTAL DUE", "Rs. {:.2f}".format(total_due)])

    table = Table(data, colWidths=[30, 140, 30, 70, 70])
    style = TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#ADD8E6")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.black),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("ALIGN", (2,1), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
        ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
        ("TEXTCOLOR", (-1,-3), (-1,-1), colors.darkred),
        ("FONTNAME", (-1,-1), (-1,-1), "Helvetica-Bold"),
    ])
    table.setStyle(style)

    table.wrapOn(c, PAGE_WIDTH, PAGE_HEIGHT)
    table_height = 18 * len(data)
    table.drawOn(c, 10, y - table_height)

    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor("#FFA07A"))
    c.drawCentredString(PAGE_WIDTH/2, 25, "🎈 Thank you for shopping with us! 🎈")
    c.save()
    buffer.seek(0)

    # Save to DB
    invoice = Invoice(
        bill_number=bill_number,
        date=datetime.now(),
        customer_name=customer_name,
        customer_number=customer_number,
        subtotal=subtotal,
        discount_percentage=discount_percentage,
        total_due=total_due,
        items_json=json.dumps(products)
    )
    db.session.add(invoice)
    db.session.commit()

    filename = f"Invoice_{bill_number}.pdf"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )

@app.route('/invoice')
def invoice():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template("invoice.html", product_price_dict=product_price_dict)

@app.route('/invoices')
def invoices():
    if 'user' not in session:
        return redirect(url_for('login'))
    page = request.args.get('page', 1, type=int)
    pagination = Invoice.query.order_by(Invoice.date.desc()).paginate(page=page, per_page=10)
    return render_template('invoice_list.html', pagination=pagination)

@app.route('/delete_invoice/<int:invoice_id>', methods=['POST'])
def delete_invoice(invoice_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    invoice = Invoice.query.get_or_404(invoice_id)
    db.session.delete(invoice)
    db.session.commit()
    flash("Invoice deleted successfully.", "success")
    return redirect(url_for('invoices'))

@app.route('/export_invoices')
def export_invoices():
    if 'user' not in session:
        return redirect(url_for('login'))
    invoices = Invoice.query.order_by(Invoice.date.desc()).all()
    data = []
    for inv in invoices:
        data.append({
            "Invoice No": inv.bill_number,
            "Date": inv.date.strftime('%Y-%m-%d %H:%M') if isinstance(inv.date, datetime) else str(inv.date),
            "Customer Name": inv.customer_name,
            "Mobile": inv.customer_number,
            "Subtotal": inv.subtotal,
            "Discount %": inv.discount_percentage,
            "Total Due": inv.total_due
        })
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Invoices')
    output.seek(0)
    return send_file(output, download_name='invoices.xlsx', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
