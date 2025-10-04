from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
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
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin':
            session['admin'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid Credentials')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
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
    if 'admin' not in session:
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
    if 'admin' not in session:
        return redirect(url_for('login'))
    employees = Employee.query.all()
    return render_template('view_employees.html', employees=employees)

@app.route('/generate-salary', methods=['GET', 'POST'])
def generate_salary():
    if 'admin' not in session:
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
    if 'admin' not in session:
        return redirect(url_for('login'))
    salaries = Salary.query.all()
    return render_template('view_salaries.html', salaries=salaries)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)