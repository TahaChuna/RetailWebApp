from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from werkzeug.utils import secure_filename
import os
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'diamondkidswear_secret_key'
app.permanent_session_lifetime = timedelta(seconds=180)

UPLOAD_FOLDER = 'uploads'
INVOICE_FOLDER = 'invoices'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(INVOICE_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# User database
users = {
    "Taha": "010923",
    "Mustafa": "Musa90"
}

# Global variables
invoice_count = 1
customer_data = []
current_data = pd.DataFrame()

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def do_login():
    username = request.form['username']
    password = request.form['password']
    if username in users and users[username] == password:
        session['username'] = username
        session.permanent = True
        return redirect(url_for('home'))
    else:
        flash("Invalid username or password", "danger")
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template('home.html', time=current_time)

@app.route('/current_standing', methods=['GET', 'POST'])
def current_standing():
    global current_data
    if 'username' not in session:
        return redirect(url_for('login'))

    status = ""
    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            current_data = pd.read_excel(filepath)
            status = "File uploaded successfully!"

    search_id = request.args.get('search_id')
    result = None
    if search_id and not current_data.empty:
        result = current_data[current_data['Product ID'].astype(str) == search_id]

    return render_template('current_standing.html', status=status, data=result)

@app.route('/invoice', methods=['GET', 'POST'])
def generate_invoice():
    if request.method == 'POST':
        # process invoice...
        pass

    # Load product-price mapping (replace with your real logic)
    product_price_dict = {
        'P001': 250,
        'P002': 400,
        'P003': 300
    }

    return render_template('invoice.html', product_price_dict=product_price_dict)

    if request.method == 'POST':
        name = request.form['customer_name']
        number = request.form.get('customer_number', '')
        items = request.form.getlist('product_id')
        discount = float(request.form.get('discount', 0))
        payment_type = request.form.get('payment_type', 'Cash')

        invoice_items = []
        total = 0
        for pid in items:
            row = current_data[current_data['Product ID'].astype(str) == pid]
            if not row.empty:
                price = float(row['Price'].values[0])
                invoice_items.append((pid, price))
                total += price

        discounted_total = total * (1 - discount / 100)
        invoice_number = f"BILL{invoice_count:04d}"
        invoice_count += 1

        filename = os.path.join(INVOICE_FOLDER, f"{invoice_number}.txt")
        with open(filename, 'w') as f:
            f.write("DIAMOND KIDS WEAR\n")
            f.write(f"Bill Number: {invoice_number}\n")
            f.write(f"Customer Name: {name}\n")
            f.write(f"Mobile: {number}\n")
            f.write(f"Payment Type: {payment_type}\n\n")
            for pid, price in invoice_items:
                f.write(f"{pid}: Rs. {price}\n")
            f.write(f"\nTotal after {discount}% discount: Rs. {discounted_total:.2f}\n")
            f.write("\nNote: Product sold has to be exchanged within 3 days from the date of the bill\n")

        # Store in customer_data
        customer_data.append({
            "name": name,
            "mobile": number,
            "bill": invoice_number
        })

        return send_file(filename, as_attachment=True)

    return render_template('invoice.html')

@app.route('/customers')
def customers():
    if 'username' not in session:
        return redirect(url_for('login'))

    grouped = defaultdict(lambda: {"name": "", "mobile": "", "bills": []})
    for entry in customer_data:
        key = (entry['name'], entry['mobile'])
        grouped[key]["name"] = entry['name']
        grouped[key]["mobile"] = entry['mobile']
        grouped[key]["bills"].append(entry['bill'])

    result = list(grouped.values())
    return render_template('customer_database.html', customer_data=result)

@app.route('/export_customers', methods=['POST'])
def export_customers():
    if not customer_data:
        return redirect(url_for('customers'))

    df = pd.DataFrame(customer_data)
    filename = os.path.join(INVOICE_FOLDER, 'customers.xlsx')
    df.to_excel(filename, index=False)
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
