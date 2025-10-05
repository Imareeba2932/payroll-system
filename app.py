from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import re
import calendar

app = Flask(__name__)
app.secret_key = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///payroll.db'
db = SQLAlchemy(app)

# inject current year into templates
@app.context_processor
def inject_current_year():
    return { 'current_year': datetime.now().year }

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    department = db.Column(db.String(100))
    role = db.Column(db.String(100))
    joining_date = db.Column(db.String(100))
    basic_salary = db.Column(db.Float)

class Salary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    date = db.Column(db.String(100))
    bonus = db.Column(db.Float)
    deductions = db.Column(db.Float)
    net_salary = db.Column(db.Float)
    employee = db.relationship('Employee')

@app.route('/')
def home():
    return render_template('landing.html')

@app.route('/landing')
def landing():
    return render_template('landing.html')

def _validate_email(email: str) -> bool:
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or '') is not None

def _validate_password_strength(password: str) -> bool:
    if not password or len(password) < 8:
        return False
    has_letter = re.search(r"[A-Za-z]", password) is not None
    has_number = re.search(r"[0-9]", password) is not None
    return has_letter and has_number

@app.route('/register', methods=['GET', 'POST'])
def register():
    errors = []
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        confirm_password = request.form.get('confirm_password') or ''

        if len(username) < 3 or not re.match(r"^[A-Za-z0-9_]+$", username):
            errors.append('Username must be at least 3 characters and alphanumeric with underscores only.')
        if not _validate_email(email):
            errors.append('Enter a valid email address.')
        if not _validate_password_strength(password):
            errors.append('Password must be at least 8 characters and include letters and numbers.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if User.query.filter_by(username=username).first():
            errors.append('Username is already taken.')
        if User.query.filter_by(email=email).first():
            errors.append('Email is already registered.')

        if not errors:
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                is_admin=False
            )
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            return redirect(url_for('dashboard'))

    return render_template('register.html', errors=errors)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid username or password'
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    # compute simple stats for dashboard
    total_employees = Employee.query.count()
    total_payrolls = Salary.query.count()

    # total amount paid
    total_paid = 0.0
    for s in Salary.query.all():
        try:
            total_paid += float(s.net_salary or 0)
        except Exception:
            pass

    # recent employees
    recent_employees = Employee.query.order_by(Employee.id.desc()).limit(5).all()

    # build last 6 months payroll totals
    def last_n_months(n=6):
        now = datetime.now()
        months = []
        y = now.year
        m = now.month
        for _ in range(n):
            months.append((y, m))
            m -= 1
            if m == 0:
                m = 12
                y -= 1
        months.reverse()
        return months

    months = last_n_months(6)
    month_labels = [f"{calendar.month_abbr[m]} {y}" for (y, m) in months]
    month_map = {(y, m): 0.0 for (y, m) in months}
    for s in Salary.query.all():
        try:
            parts = s.date.split('-')
            y = int(parts[0]); m = int(parts[1])
            if (y, m) in month_map:
                month_map[(y, m)] += float(s.net_salary or 0)
        except Exception:
            continue

    month_values = [round(month_map[(y, m)], 2) for (y, m) in months]
    max_month_value = max(month_values) if month_values and max(month_values) > 0 else 1
    # prepare chart data as dicts with preformatted values and height percent to avoid Jinja math
    chart_data = []
    for label, value in zip(month_labels, month_values):
        try:
            h = int((value / max_month_value) * 100) if max_month_value else 0
        except Exception:
            h = 0
        chart_data.append({
            'label': label,
            'value': value,
            'formatted': "${:.2f}".format(value),
            'h': h
        })

    stats = {
        'total_employees': total_employees,
        'total_payrolls': total_payrolls,
        'total_paid': round(total_paid, 2)
    }

    return render_template('dashboard.html', stats=stats, chart_labels=month_labels, chart_values=month_values, chart_data=chart_data, max_month_value=max_month_value, recent_employees=recent_employees)

@app.route('/add-employee', methods=['GET', 'POST'])
def add_employee():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        emp = Employee(
            name=request.form['name'],
            department=request.form['department'],
            role=request.form['role'],
            joining_date=request.form['joining_date'],
            basic_salary=request.form['basic_salary']
        )
        db.session.add(emp)
        db.session.commit()
        return redirect(url_for('view_employees'))
    return render_template('add_employee.html')

@app.route('/employees')
def view_employees():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    employees = Employee.query.all()
    return render_template('view_employees.html', employees=employees)

@app.route('/generate-salary', methods=['GET', 'POST'])
def generate_salary():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    employees = Employee.query.all()
    if request.method == 'POST':
        emp_id = request.form['employee_id']
        employee = Employee.query.get(emp_id)
        bonus = float(request.form['bonus'])
        deductions = float(request.form['deductions'])
        net_salary = employee.basic_salary + bonus - deductions

        salary = Salary(
            employee_id=emp_id,
            date=datetime.now().strftime('%Y-%m-%d'),
            bonus=bonus,
            deductions=deductions,
            net_salary=net_salary
        )
        db.session.add(salary)
        db.session.commit()
        return redirect(url_for('view_salaries'))
    return render_template('generate_salary.html', employees=employees)

@app.route('/salaries')
def view_salaries():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    salaries = Salary.query.all()
    return render_template('view_salaries.html', salaries=salaries)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('is_admin', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)