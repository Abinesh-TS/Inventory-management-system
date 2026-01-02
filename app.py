from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import webbrowser
import threading
import re
from flask import make_response
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime  
import io

app = Flask(__name__)
app.secret_key = '444'

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="coconut"
)
cursor = db.cursor(buffered=True, dictionary=True)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=["GET", "POST"])
def login():
    invalid = False
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        cursor.execute("SELECT * FROM login WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        if user:
            session['username'] = username
            return redirect(url_for('dash'))
        else:
            invalid = True
    return render_template("login.html", invalid=invalid)

@app.route('/dash')
def dash():
    if 'username' in session:
        cursor.execute("SELECT IFNULL(SUM(total), 0) AS total_purchases FROM purchase")
        total_purchases = cursor.fetchone()['total_purchases']

        cursor.execute("SELECT IFNULL(SUM(total), 0) AS total_sales FROM sales")
        total_sales = cursor.fetchone()['total_sales']

        cursor.execute("SELECT IFNULL(SUM(amount), 0) AS total_expenses FROM expense")
        total_expenses = cursor.fetchone()['total_expenses']

        total_costs = total_purchases + total_expenses
        net_profit_loss = total_sales - total_costs

        chart_labels = ["Purchases", "Sales"]
        chart_values = [total_purchases, total_sales]

        return render_template(
            "dashboard.html",
            username=session['username'],
            total_purchases=total_purchases,
            total_sales=total_sales,
            net_profit_loss=net_profit_loss,
            chart_labels=chart_labels,
            chart_values=chart_values
        )
    else:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

def extract_number(text):
    match = re.search(r'\d+(\.\d+)?', str(text))
    return float(match.group()) if match else 0.0

@app.route('/purchase', methods=["GET", "POST"])
def purchase():
    if 'username' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    if request.method == "POST":
        purchase_date = request.form.get('purchase_date')
        product_name = request.form.get('product_name')
        supplier_name = request.form.get('supplier_name')
        payment_status = request.form.get("payment_status")
        quantity_with_unit_str = request.form.get('quantity_with_unit') or ""
        try:
            unit_rate = float(request.form.get('unit_rate') or 0)
        except ValueError:
            unit_rate = 0.0

        quantity = extract_number(quantity_with_unit_str)
        total = unit_rate * quantity

        cursor.execute("""
            INSERT INTO purchase (purchase_date, product_name, supplier_name, quantity_with_unit, unit_rate, total,payment_status)
            VALUES (%s, %s, %s, %s, %s, %s,%s)
        """, (purchase_date, product_name, supplier_name, quantity_with_unit_str, unit_rate, total,payment_status))
        db.commit()
        flash("Purchase added.", "success")
        return redirect(url_for('purchase'))

    cursor.execute("SELECT * FROM purchase")
    purchase_data = cursor.fetchall()
    return render_template('purchase.html', purchase=purchase_data)

@app.route('/purchase/edit/<int:purchase_id>', methods=["GET", "POST"])
def edit_purchase(purchase_id):
    if 'username' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    if request.method == "POST":
        purchase_date = request.form.get('purchase_date')
        product_name = request.form.get('product_name')
        supplier_name = request.form.get('supplier_name')
        payment_status = request.form.get("payment_status")
        quantity_with_unit_str = request.form.get('quantity_with_unit') or ""
        try:
            unit_rate = float(request.form.get('unit_rate') or 0)
        except ValueError:
            unit_rate = 0.0
        quantity = extract_number(quantity_with_unit_str)
        total = unit_rate * quantity

        cursor.execute("""
            UPDATE purchase 
            SET purchase_date=%s, product_name=%s, supplier_name=%s, quantity_with_unit=%s, unit_rate=%s, total=%s, payment_status=%s
            WHERE id=%s
        """, (purchase_date, product_name, supplier_name, quantity_with_unit_str, unit_rate, total,payment_status, purchase_id))
        db.commit()
        flash("Purchase updated successfully!", "success")
        return redirect(url_for('purchase'))

    cursor.execute("SELECT * FROM purchase WHERE id=%s", (purchase_id,))
    purchase_item = cursor.fetchone()
    if not purchase_item:
        flash("Purchase not found.", "danger")
        return redirect(url_for('purchase'))
    return render_template('edit_purchase.html', purchase=purchase_item)

@app.route('/purchase/delete/<int:purchase_id>', methods=["POST", "GET"])
def delete_purchase(purchase_id):
    if 'username' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    cursor.execute("DELETE FROM purchase WHERE id=%s", (purchase_id,))
    db.commit()
    flash("Purchase deleted successfully!", "success")
    return redirect(url_for('purchase'))

@app.route('/sales', methods=["GET", "POST"])
def sales():
    if 'username' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    cursor.execute("SELECT DISTINCT product_name FROM purchase")
    products = cursor.fetchall() 

    if request.method == "POST":
        sale_date = request.form['sale_date']
        product_name = request.form['product_name']
        customer_name = request.form['customer_name']
        payment_status = request.form['payment_status']
        quantity_with_unit_str = request.form['quantity_with_unit']
        try:
            unit_rate = float(request.form['unit_rate'])
        except ValueError:
            unit_rate = 0.0

        quantity = extract_number(quantity_with_unit_str)

        cursor.execute("SELECT quantity_with_unit FROM purchase WHERE product_name=%s", (product_name,))
        purchase_rows = cursor.fetchall()
        total_purchased = sum([extract_number(p['quantity_with_unit']) for p in purchase_rows])

        cursor.execute("SELECT quantity_with_unit FROM sales WHERE product_name=%s", (product_name,))
        sales_rows = cursor.fetchall()
        total_sold = sum([extract_number(s['quantity_with_unit']) for s in sales_rows])

        available_stock = total_purchased - total_sold

        if quantity > available_stock:
            flash(f"Not enough stock for '{product_name}'. Available: {available_stock} units.", "danger")
        else:
            total = unit_rate * quantity
            cursor.execute("""
                INSERT INTO sales (sale_date, product_name, customer_name, quantity_with_unit, unit_rate, total, payment_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (sale_date, product_name, customer_name, quantity_with_unit_str, unit_rate, total, payment_status))
            db.commit()
            flash("Sale added successfully!", "success")

    cursor.execute("SELECT * FROM sales")
    sales_data = cursor.fetchall()
    return render_template('sales.html', sales=sales_data, products=products)




@app.route('/sales/edit/<int:sales_id>', methods=["GET", "POST"])
def edit_sales(sales_id):
    if 'username' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    if request.method == "POST":
        sale_date = request.form['sale_date']
        product_name = request.form['product_name']
        customer_name = request.form['customer_name']
        payment_status = request.form['payment_status']
        quantity_with_unit_str = request.form['quantity_with_unit']
        try:
            unit_rate = float(request.form['unit_rate'])
        except ValueError:
            unit_rate = 0.0
        quantity = extract_number(quantity_with_unit_str)
        total = unit_rate * quantity

        cursor.execute("""
            UPDATE sales 
            SET sale_date=%s, product_name=%s, customer_name=%s, quantity_with_unit=%s, unit_rate=%s, total=%s, payment_status=%s
            WHERE id=%s
        """, (sale_date, product_name, customer_name, quantity_with_unit_str, unit_rate, total, payment_status, sales_id))
        db.commit()
        flash("Sales record updated successfully!", "success")
        return redirect(url_for('sales'))

    cursor.execute("SELECT * FROM sales WHERE id=%s", (sales_id,))
    sales_item = cursor.fetchone()
    return render_template('edit_sales.html', sales=sales_item)

@app.route('/sales/delete/<int:sales_id>', methods=["POST", "GET"])
def delete_sales(sales_id):
    if 'username' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    cursor.execute("DELETE FROM sales WHERE id=%s", (sales_id,))
    db.commit()
    flash("Sales record deleted successfully!", "success")
    return redirect(url_for('sales'))

@app.route('/expense', methods=["GET", "POST"])
def expense():
    if 'username' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    if request.method == "POST":
        expense_date = request.form['expense_date']
        expense_description = request.form['expense_description']
        try:
            amount = float(request.form['amount'])
        except ValueError:
            amount = 0.0
        cursor.execute("""
            INSERT INTO expense (expense_date, expense_description, amount)
            VALUES (%s, %s, %s)
        """, (expense_date, expense_description, amount))
        db.commit()
        return redirect(url_for('expense'))

    cursor.execute("SELECT * FROM expense")
    expense_data = cursor.fetchall()
    return render_template('expense.html', expense=expense_data)

@app.route('/expense/edit/<int:expense_id>', methods=["GET", "POST"])
def edit_expense(expense_id):
    if 'username' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    if request.method == "POST":
        expense_date = request.form['expense_date']
        expense_description = request.form['expense_description']
        try:
            amount = float(request.form['amount'])
        except ValueError:
            amount = 0.0

        cursor.execute("""
            UPDATE expense 
            SET expense_date=%s, expense_description=%s, amount=%s
            WHERE id=%s
        """, (expense_date, expense_description, amount, expense_id))
        db.commit()
        flash("Expense updated successfully!", "success")
        return redirect(url_for('expense'))

    cursor.execute("SELECT * FROM expense WHERE id=%s", (expense_id,))
    expense_item = cursor.fetchone()
    return render_template('edit_expense.html', expense=expense_item)

@app.route('/expense/delete/<int:expense_id>', methods=["POST", "GET"])
def delete_expense(expense_id):
    if 'username' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    cursor.execute("DELETE FROM expense WHERE id=%s", (expense_id,))
    db.commit()
    flash("Expense deleted successfully!", "success")
    return redirect(url_for('expense'))

@app.route('/manage', methods=["GET", "POST"])
def manage():
    if 'username' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))
    
    cursor.execute("SELECT DISTINCT product_name FROM purchase")
    products = cursor.fetchall() 

    if request.method == "POST":
        product_name = request.form.get('product_name')
        manage_date = request.form.get('manage_date')

        cursor.execute("SELECT quantity_with_unit FROM purchase WHERE product_name=%s", (product_name,))
        purchase_rows = cursor.fetchall()
        total_purchased = sum([extract_number(p['quantity_with_unit']) for p in purchase_rows])

        cursor.execute("SELECT quantity_with_unit FROM sales WHERE product_name=%s", (product_name,))
        sales_rows = cursor.fetchall()
        total_sold = sum([extract_number(s['quantity_with_unit']) for s in sales_rows])

        stock_balance = total_purchased - total_sold

        cursor.execute("""
            INSERT INTO manage (manage_date, product_name, stock_in, stock_out, total_stock)
            VALUES (%s, %s, %s, %s, %s)
        """, (manage_date, product_name, total_purchased, total_sold, stock_balance))
        db.commit()

        flash("Stock updated successfully.", "success")
        return redirect(url_for('manage'))

    cursor.execute("SELECT * FROM manage")
    manage_data = cursor.fetchall()
    return render_template('manage.html', manage=manage_data,products=products)

@app.route('/manage/edit/<int:manage_id>', methods=["GET", "POST"])
def edit_manage(manage_id):
    if 'username' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    if request.method == "POST":
        manage_date = request.form.get('manage_date')
        product_name = request.form.get('product_name')
 
        cursor.execute("SELECT quantity_with_unit FROM purchase WHERE product_name=%s", (product_name,))
        purchase_rows = cursor.fetchall()
        total_purchased = sum([extract_number(p['quantity_with_unit']) for p in purchase_rows])

        cursor.execute("SELECT quantity_with_unit FROM sales WHERE product_name=%s", (product_name,))
        sales_rows = cursor.fetchall()
        total_sold = sum([extract_number(s['quantity_with_unit']) for s in sales_rows])

        stock_balance = total_purchased - total_sold

        cursor.execute("""
            UPDATE manage
            SET manage_date=%s, product_name=%s, stock_in=%s, stock_out=%s, total_stock=%s
            WHERE id=%s
        """, (manage_date, product_name, total_purchased, total_sold, stock_balance, manage_id))
        db.commit()

        flash("Stock record updated successfully!", "success")
        return redirect(url_for('manage'))

    cursor.execute("SELECT * FROM manage WHERE id=%s", (manage_id,))
    manage_item = cursor.fetchone()
    if not manage_item:
        flash("Stock record not found.", "danger")
        return redirect(url_for('manage'))

    return render_template('edit_manage.html', manage=manage_item)


@app.route('/manage/delete/<int:manage_id>', methods=["POST", "GET"])
def delete_manage(manage_id):
    if 'username' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    cursor.execute("DELETE FROM manage WHERE id=%s", (manage_id,))
    db.commit()

    flash("Stock record deleted successfully!", "success")
    return redirect(url_for('manage'))

@app.route('/profitloss')
def profitloss():
    if 'username' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    cursor.execute("SELECT IFNULL(SUM(total), 0) AS total_sales FROM sales")
    total_sales = cursor.fetchone()['total_sales']

    cursor.execute("SELECT IFNULL(SUM(total), 0) AS total_purchases FROM purchase")
    total_purchases = cursor.fetchone()['total_purchases']

    cursor.execute("SELECT IFNULL(SUM(amount), 0) AS total_expenses FROM expense")
    total_expenses = cursor.fetchone()['total_expenses']

    total_costs = total_purchases + total_expenses

    net_profit_loss = total_sales - total_costs

    cursor.execute("""
        SELECT 
            p.product_name,
            IFNULL(SUM(p.total), 0) AS total_purchased,
            IFNULL((SELECT SUM(s.total) FROM sales s WHERE s.product_name = p.product_name), 0) AS total_sold,
            (IFNULL((SELECT SUM(s.total) FROM sales s WHERE s.product_name = p.product_name), 0) - IFNULL(SUM(p.total), 0)) AS profit_loss
        FROM purchase p
        GROUP BY p.product_name
    """)
    product_summary = cursor.fetchall()

    return render_template(
        "profit_loss.html",
        username=session['username'],
        total_sales=total_sales,
        total_costs=total_costs,
        net_profit_loss=net_profit_loss,
        product_summary=product_summary
    )

@app.route('/cashflow', methods=["GET", "POST"])
def cashflow():
    if 'username' not in session:
        flash("Please login first", "warning")
        return redirect(url_for('login'))

    data = []
    source = None
    status = None

    if request.method == "POST":
        source = request.form.get("source")     
        status = request.form.get("status")    
        if source == "purchase":
            cursor.execute("SELECT * FROM purchase WHERE payment_status=%s", (status,))
            data = cursor.fetchall()
        elif source == "sales":
            cursor.execute("SELECT * FROM sales WHERE payment_status=%s", (status,))
            data = cursor.fetchall()

    return render_template("cashflow.html", 
                           username=session['username'], 
                           data=data, 
                           source=source, 
                           status=status)


@app.route("/reports", methods=["GET", "POST"])
def reports():
    if "username" not in session:
        flash("Please login first", "warning")
        return redirect(url_for("login"))

    report_data = []
    report_title = ""

    if request.method == "POST":
        report_type = request.form.get("report_type")
        from_date = request.form.get("from_date")
        to_date = request.form.get("to_date")

        if report_type == "purchase":
            cursor.execute("SELECT * FROM purchase WHERE purchase_date BETWEEN %s AND %s", (from_date, to_date))
            report_data = cursor.fetchall()
            report_title = "Purchase Report"

        elif report_type == "sales":
            cursor.execute("SELECT * FROM sales WHERE sale_date BETWEEN %s AND %s", (from_date, to_date))
            report_data = cursor.fetchall()
            report_title = "Sales Report"

        elif report_type == "expense":
            cursor.execute("SELECT * FROM expense WHERE expense_date BETWEEN %s AND %s", (from_date, to_date))
            report_data = cursor.fetchall()
            report_title = "Expense Report"

        elif report_type == "stock":
            cursor.execute("SELECT * FROM manage WHERE manage_date BETWEEN %s AND %s", (from_date, to_date))
            report_data = cursor.fetchall()
            report_title = "Stock Report"

        elif report_type == "purchase_paid":
            cursor.execute("""
                SELECT id,  purchase_date AS date,  product_name, supplier_name, quantity_with_unit, unit_rate, total AS amount, payment_status
                FROM purchase 
                WHERE payment_status='paid' AND purchase_date BETWEEN %s AND %s
            """, (from_date, to_date))
            report_data = cursor.fetchall()
            report_title = "Purchase - Paid Records"
        
        elif report_type == "purchase_unpaid":
            cursor.execute("""
                SELECT id,  purchase_date AS date,  product_name, supplier_name, quantity_with_unit, unit_rate, total AS amount, payment_status 
                FROM purchase 
                WHERE payment_status='unpaid' AND purchase_date BETWEEN %s AND %s
            """, (from_date, to_date))
            report_data = cursor.fetchall()
            report_title = "Purchase - Unpaid Records"
        
        elif report_type == "sales_paid":
            cursor.execute("""
                SELECT id, sale_date AS date, product_name, customer_name, quantity_with_unit, unit_rate, total AS amount, payment_status
                FROM sales 
                WHERE payment_status='paid' AND sale_date BETWEEN %s AND %s
            """, (from_date, to_date))
            report_data = cursor.fetchall()
            report_title = "Sales - Paid Records"
     
        elif report_type == "sales_unpaid":
            cursor.execute("""
                SELECT id, sale_date AS date, product_name, customer_name, quantity_with_unit, unit_rate, total AS amount, payment_status 
                FROM sales 
                WHERE payment_status='unpaid' AND sale_date BETWEEN %s AND %s
            """, (from_date, to_date))
            report_data = cursor.fetchall()
            report_title = "Sales - Unpaid Records"

    return render_template("report.html", report_data=report_data, report_title=report_title)

@app.route("/download_pdf", methods=["GET"])
def download_pdf():
    if "username" not in session:
        flash("Please login first", "warning")
        return redirect(url_for("login"))

    report_type = request.args.get("report_type")
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")

    if not report_type or not from_date or not to_date:
        flash("Please select report type and date range.", "warning")
        return redirect(url_for("reports"))

    if report_type == "purchase":
        cursor.execute("SELECT * FROM purchase WHERE purchase_date BETWEEN %s AND %s", (from_date, to_date))
        title = f"Purchase Report ({from_date} to {to_date})"

    elif report_type == "sales":
        cursor.execute("SELECT * FROM sales WHERE sale_date BETWEEN %s AND %s", (from_date, to_date))
        title = f"Sales Report ({from_date} to {to_date})"

    elif report_type == "expense":
        cursor.execute("SELECT * FROM expense WHERE expense_date BETWEEN %s AND %s", (from_date, to_date))
        title = f"Expense Report ({from_date} to {to_date})"

    elif report_type == "stock":
        cursor.execute("SELECT * FROM manage WHERE manage_date BETWEEN %s AND %s", (from_date, to_date))
        title = f"Stock Report ({from_date} to {to_date})"

    elif report_type == "purchase_paid":
        cursor.execute("""
            SELECT id,  purchase_date AS date,  product_name, supplier_name, quantity_with_unit, unit_rate, total AS amount, payment_status
            FROM purchase
            WHERE payment_status='paid' AND purchase_date BETWEEN %s AND %s
        """, (from_date, to_date))
        title = f"Purchase - Paid Records ({from_date} to {to_date})"

    elif report_type == "purchase_unpaid":
        cursor.execute("""
            SELECT id,  purchase_date AS date,  product_name, supplier_name, quantity_with_unit, unit_rate, total AS amount, payment_status
            FROM purchase
            WHERE payment_status='unpaid' AND purchase_date BETWEEN %s AND %s
        """, (from_date, to_date))
        title = f"Purchase - Unpaid Records ({from_date} to {to_date})"

    elif report_type == "sales_paid":
        cursor.execute("""
            SELECT id, sale_date AS date, product_name, customer_name, quantity_with_unit, unit_rate, total AS amount, payment_status
            FROM sales
            WHERE payment_status='paid' AND sale_date BETWEEN %s AND %s
        """, (from_date, to_date))
        title = f"Sales - Paid Records ({from_date} to {to_date})"

    elif report_type == "sales_unpaid":
        cursor.execute("""
            SELECT id, sale_date AS date, product_name, customer_name, quantity_with_unit, unit_rate, total AS amount, payment_status
            FROM sales
            WHERE payment_status='unpaid' AND sale_date BETWEEN %s AND %s
        """, (from_date, to_date))
        title = f"Sales - Unpaid Records ({from_date} to {to_date})"

    else:
        flash("Invalid report type.", "danger")
        return redirect(url_for("reports"))

    rows = cursor.fetchall()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []

    styles = getSampleStyleSheet()
    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), styles["Normal"]))

    if rows:
        headers = list(rows[0].keys())
        data = [headers] + [list(r.values()) for r in rows]

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#635bff")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("No records found for the selected filters.", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)

    response = make_response(buffer.read())
    response.headers["Content-Type"] = "application/pdf"
    filename = f"{report_type}_report_{from_date}_to_{to_date}.pdf".replace(" ", "_")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == "__main__":
    threading.Timer(1.0, open_browser).start()
    app.run(debug=True, use_reloader=False)
