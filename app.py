from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///payroll.db'
db = SQLAlchemy(app)

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
    return render_template('dashboard.html')

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