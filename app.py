from flask import Flask, render_template, request, redirect, session, send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import sqlite3

app = Flask(__name__)
app.secret_key = "mysecretkey"

# ================= DATABASE CONNECTION (SQLite) =================
db = sqlite3.connect('expense.db', check_same_thread=False)
db.row_factory = sqlite3.Row
cursor = db.cursor()

# ================= CREATE TABLES (First Time Only) =================
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    category TEXT,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
db.commit()

# ================= HOME =================
@app.route('/')
def home():
    return render_template('login.html')

# ================= REGISTER =================
@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    cursor.execute(
        "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
        (name, email, password)
    )
    db.commit()

    return redirect('/')

# ================= LOGIN =================
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    cursor.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email, password)
    )
    user = cursor.fetchone()

    if user:
        session['user_id'] = user['id']
        return redirect('/dashboard')
    else:
        return "Invalid Email or Password"

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user_id = session['user_id']

        cursor.execute(
            "SELECT * FROM transactions WHERE user_id=?",
            (user_id,)
        )
        expenses = cursor.fetchall()

        cursor.execute(
            "SELECT SUM(amount) AS total FROM transactions WHERE user_id=?",
            (user_id,)
        )
        total_data = cursor.fetchone()
        total = total_data['total'] if total_data['total'] else 0

        cursor.execute("""
            SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE user_id=?
            GROUP BY category
        """, (user_id,))
        category_data = cursor.fetchall()

        categories = [row['category'] for row in category_data]
        amounts = [float(row['total']) for row in category_data]

        return render_template(
            'dashboard.html',
            expenses=expenses,
            total=total,
            categories=categories,
            amounts=amounts
        )
    else:
        return redirect('/')

# ================= ADD EXPENSE =================
@app.route('/add_expense', methods=['POST'])
def add_expense():
    if 'user_id' in session:
        user_id = session['user_id']
        amount = request.form['amount']
        category = request.form['category']

        cursor.execute(
            "INSERT INTO transactions (user_id, amount, category) VALUES (?, ?, ?)",
            (user_id, amount, category)
        )
        db.commit()

        return redirect('/dashboard')
    else:
        return redirect('/')

# ================= DELETE =================
@app.route('/delete/<int:id>')
def delete(id):
    if 'user_id' in session:
        cursor.execute("DELETE FROM transactions WHERE id=?", (id,))
        db.commit()
        return redirect('/dashboard')
    else:
        return redirect('/')

# ================= EDIT =================
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if 'user_id' in session:
        if request.method == 'POST':
            amount = request.form['amount']
            category = request.form['category']

            cursor.execute("""
                UPDATE transactions
                SET amount=?, category=?
                WHERE id=?
            """, (amount, category, id))
            db.commit()

            return redirect('/dashboard')

        cursor.execute("SELECT * FROM transactions WHERE id=?", (id,))
        expense = cursor.fetchone()

        return render_template('edit.html', expense=expense)
    else:
        return redirect('/')

# ================= DOWNLOAD PDF =================
@app.route('/download_pdf')
def download_pdf():
    if 'user_id' in session:
        user_id = session['user_id']

        cursor.execute(
            "SELECT * FROM transactions WHERE user_id=?",
            (user_id,)
        )
        expenses = cursor.fetchall()

        file_path = "expense_report.pdf"
        doc = SimpleDocTemplate(file_path)
        elements = []

        style = getSampleStyleSheet()
        elements.append(Paragraph("Expense Report", style['Title']))
        elements.append(Spacer(1, 12))

        data = [["Amount", "Category"]]

        for expense in expenses:
            data.append([
                str(expense['amount']),
                expense['category']
            ])

        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))

        elements.append(table)
        doc.build(elements)

        return send_file(file_path, as_attachment=True)
    else:
        return redirect('/')

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)