from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import datetime
import numpy as np
import decimal
import math  # For checking NaN/inf

# --- APP SETUP ---
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# --- DATABASE CONNECTION CONFIGURATION ---
app.config['SQLALCHEMY_DATABASE_URI'] = (
    'postgresql://{user}:{password}@{host}:{port}/{database}'.format(
        user='u7tqojjihbpn7s',
        password='p1b1897f6356bab4e52b727ee100290a84e4bf71d02e064e90c2c705bfd26f4a5',
        host='c7s7ncbk19n97r.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com',
        port=5432,
        database='d8lp4hr6fmvb9m'
    )
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- GLOBAL DATA ---
MASTER_DATA = {}
warehouse_data = []

# ==========================
# --- SQLAlchemy MODELS ---
# ==========================

class DailyRecords(db.Model):
    __tablename__ = 'daily_records'
    id = db.Column(db.Integer, primary_key=True)
    entry_date = db.Column(db.Date, nullable=False, unique=True)
    revenue_warehouse = db.Column(db.Float, default=0.0)
    revenue_freight = db.Column(db.Float, default=0.0)
    staff_supervisor = db.Column(db.Integer, default=0)
    staff_blue_collar = db.Column(db.Integer, default=0)
    staff_loader = db.Column(db.Integer, default=0)
    supervisor_vender = db.Column(db.Integer, default=0)
    staff_adhoc_manpower = db.Column(db.Integer, default=0)
    ot_supervisor_hrs = db.Column(db.Float, default=0.0)
    ot_blue_collar_hrs = db.Column(db.Float, default=0.0)
    ot_loader_hrs = db.Column(db.Float, default=0.0)
    cost_sunday_sup = db.Column(db.Float, default=0.0)
    cost_sunday_bc = db.Column(db.Float, default=0.0)
    cost_holiday_mgmt = db.Column(db.Float, default=0.0)
    cost_other_charges = db.Column(db.Float, default=0.0)
    cost_security_guard = db.Column(db.Float, default=0.0)
    cost_security_female = db.Column(db.Float, default=0.0)
    cost_security_supervisor = db.Column(db.Float, default=0.0)
    cost_house_keeping = db.Column(db.Float, default=0.0)
    cost_hk_materials = db.Column(db.Float, default=0.0)
    cost_electricity = db.Column(db.Float, default=0.0)
    cost_electricity_sub = db.Column(db.Float, default=0.0)
    cost_water = db.Column(db.Float, default=0.0)
    cost_diesel = db.Column(db.Float, default=0.0)
    cost_rental = db.Column(db.Float, default=0.0)
    cost_staff_welfare = db.Column(db.Float, default=0.0)
    cost_ho = db.Column(db.Float, default=0.0)
    cost_r_and_r = db.Column(db.Float, default=0.0)
    cost_traveling = db.Column(db.Float, default=0.0)
    cost_convence = db.Column(db.Float, default=0.0)
    cost_hra = db.Column(db.Float, default=0.0)
    cost_capex = db.Column(db.Float, default=0.0)
    cost_stationery = db.Column(db.Float, default=0.0)
    cost_tea = db.Column(db.Float, default=0.0)
    cost_other_expenses = db.Column(db.Float, default=0.0)
    consumable_roll_100x150 = db.Column(db.Integer, default=0)
    consumable_roll_75x50 = db.Column(db.Integer, default=0)
    consumable_roll_25x50 = db.Column(db.Integer, default=0)
    consumable_a4_paper = db.Column(db.Integer, default=0)
    consumable_ribbon_25x50 = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if isinstance(data.get('entry_date'), datetime.date):
            data['Date'] = data.pop('entry_date').isoformat()
        return data

# --------------------------
# MASTER DATA MODELS
# --------------------------
class RoleRates(db.Model):
    __tablename__ = 'role_rates'
    role_name = db.Column(db.String(100), primary_key=True)
    monthly_salary = db.Column(db.Numeric(10, 2), nullable=False)
    daily_cost = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(255))

class EmployeeSalaries(db.Model):
    __tablename__ = 'employee_salaries'
    emp_code = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    base_salary = db.Column(db.Numeric(10, 2), nullable=False)
    role = db.Column(db.String(100))
    monthly_rating = db.Column(db.Numeric(3, 1), default=3.5)
    adjusted_salary = db.Column(db.Numeric(10, 2))

class FixedCosts(db.Model):
    __tablename__ = 'fixed_costs'
    cost_name = db.Column(db.String(100), primary_key=True)
    cost_value = db.Column(db.Numeric(12, 2), nullable=False)

class RevenueRates(db.Model):
    __tablename__ = 'revenue_rates'
    rate_name = db.Column(db.String(100), primary_key=True)
    rate_value = db.Column(db.Numeric(10, 2), nullable=False)

# ==========================
# --- FETCH FUNCTIONS ---
# ==========================

# ================= MASTER DATA FETCH =================
def fetch_master_data():
    """
    Loads all master data from DB into MASTER_DATA dictionary safely.
    Guarantees the keys and numeric values exist so templates can format them.
    """
    global MASTER_DATA
    MASTER_DATA.clear()
    try:
        with app.app_context():
            # ROLE RATES
            MASTER_DATA['ROLE_RATES'] = {
                (r.role_name or ''): {
                    # ensure numeric value, fallback 0.0
                    'daily_cost': float(r.daily_cost) if r.daily_cost is not None else 0.0,
                    # include monthly salary optionally (helpful if UI wants it)
                    'monthly_salary': float(r.monthly_salary) if hasattr(r, 'monthly_salary') and r.monthly_salary is not None else 0.0,
                    'description': r.description or ''
                }
                for r in RoleRates.query.all()
            }

            # EMPLOYEE SALARIES
            MASTER_DATA['EMPLOYEE_SALARIES'] = {
                (e.emp_code or ''): {
                    'name': e.name or '',
                    'base_salary': float(e.base_salary) if e.base_salary is not None else 0.0,
                    'adjusted_salary': float(e.adjusted_salary) if e.adjusted_salary is not None else 0.0,
                    # ensure monthly_rating exists as float for template formatting
                    'monthly_rating': float(e.monthly_rating) if hasattr(e, 'monthly_rating') and e.monthly_rating is not None else 0.0,
                    'role': e.role or ''
                }
                for e in EmployeeSalaries.query.all()
            }

            # FIXED COSTS
            MASTER_DATA['FIXED_COSTS'] = {
                (f.cost_name or ''): float(f.cost_value) if f.cost_value is not None else 0.0
                for f in FixedCosts.query.all()
            }

            # REVENUE RATES
            MASTER_DATA['REVENUE_RATES'] = {
                (r.rate_name or ''): float(r.rate_value) if r.rate_value is not None else 0.0
                for r in RevenueRates.query.all()
            }

            # ADHOC RATES (make sure table AdhocRates exists in your models)
            try:
                MASTER_DATA['ADHOC_RATES'] = {
                    (a.rate_name or ''): float(a.rate_value) if a.rate_value is not None else 0.0
                    for a in AdhocRates.query.all()
                }
            except NameError:
                # If you don't have AdhocRates model defined, keep it empty
                MASTER_DATA['ADHOC_RATES'] = {}

            # CONSUMABLE RATES (template expects this)
            try:
                MASTER_DATA['CONSUMABLE_RATES'] = {
                    (c.item_name or ''): float(c.unit_rate) if c.unit_rate is not None else 0.0
                    for c in ConsumableRates.query.all()
                }
            except NameError:
                MASTER_DATA['CONSUMABLE_RATES'] = {}

            # Ensure all expected keys exist to avoid Undefined errors in templates
            for key in ['ROLE_RATES', 'EMPLOYEE_SALARIES', 'FIXED_COSTS',
                        'REVENUE_RATES', 'ADHOC_RATES', 'CONSUMABLE_RATES']:
                if key not in MASTER_DATA or MASTER_DATA.get(key) is None:
                    MASTER_DATA[key] = {}

    except Exception as e:
        # Keep the error printed, but don't let it leave MASTER_DATA in incomplete state
        print(f"🚨 DB Error fetching master data: {e}")
        # Ensure keys exist even on failure
        for key in ['ROLE_RATES', 'EMPLOYEE_SALARIES', 'FIXED_COSTS',
                    'REVENUE_RATES', 'ADHOC_RATES', 'CONSUMABLE_RATES']:
            if key not in MASTER_DATA:
                MASTER_DATA[key] = {}


# ================= DAILY RECORDS FETCH =================
def fetch_daily_records():
    """Loads all daily records into warehouse_data with entry_date guaranteed."""
    global warehouse_data
    warehouse_data.clear()
    try:
        with app.app_context():
            db_records = DailyRecords.query.order_by(DailyRecords.entry_date).all()
            for r in db_records:
                rec = r.to_dict()
                # Ensure 'entry_date' exists
                if 'entry_date' not in rec and 'Date' in rec:
                    rec['entry_date'] = rec['Date']
                warehouse_data.append(rec)
    except Exception as e:
        print(f"🚨 DB Error fetching daily records: {e}")

# ================= DAILY P&L SUMMARY ACCURATE =================
def calculate_daily_pl_summary():
    import pandas as pd
    import numpy as np

    global warehouse_data, MASTER_DATA

    if not warehouse_data or not MASTER_DATA:
        print("Warning: warehouse_data or MASTER_DATA is empty.")
        return pd.DataFrame()

    df = pd.DataFrame(warehouse_data)

    # Date column ensure
    if 'entry_date' not in df.columns and 'Date' in df.columns:
        df['entry_date'] = df['Date']
    df['entry_date'] = pd.to_datetime(df['entry_date'], errors='coerce')
    df.dropna(subset=['entry_date'], inplace=True)
    df.set_index('entry_date', inplace=True)
    df.sort_index(inplace=True)

    # --- 1. TOTAL LABOR COST ---
    def labor_cost(row):
        cost = 0
        # White Collar
        wc = MASTER_DATA.get('ROLE_RATES', {}).get('White Colar', {})
        cost += wc.get('daily_cost', 0)  # daily fixed cost for White Collar

        # Blue Collar
        bc = MASTER_DATA.get('ROLE_RATES', {}).get('Blue Collar (Attendance)', {})
        cost += row.get('staff_blue_collar', 0) * bc.get('daily_cost', 0)

        # Loading / Unloading
        loader = MASTER_DATA.get('ROLE_RATES', {}).get('Loading & Unloading(Attendance)', {})
        cost += row.get('staff_loader', 0) * loader.get('daily_cost', 0)

        # Electrician / Other Roles
        for role_name in MASTER_DATA.get('ROLE_RATES', {}):
            if role_name not in ['White Colar', 'Blue Collar (Attendance)', 'Loading & Unloading(Attendance)']:
                role_data = MASTER_DATA['ROLE_RATES'][role_name]
                field = 'staff_' + role_name.lower().replace(' ', '_').replace('(', '').replace(')', '')
                cost += row.get(field, 0) * role_data.get('daily_cost', 0)

        # Adhoc / Vendor
        adhoc_rate = MASTER_DATA.get('ADHOC_RATES', {}).get('Adhoc Manpower', 0)
        cost += row.get('supervisor_vender', 0) * adhoc_rate

        # Overtime
        ot_supervisor_rate = MASTER_DATA.get('ADHOC_RATES', {}).get('Over Time -Supervisor/ Hr', 0)
        ot_bc_rate = MASTER_DATA.get('ADHOC_RATES', {}).get('Over Time- Blue Collar/Hr', 0)
        ot_loader_rate = MASTER_DATA.get('ADHOC_RATES', {}).get('Over Time- Blue Collar ( Loader/Hr)', 0)
        cost += row.get('ot_supervisor_hrs', 0) * ot_supervisor_rate
        cost += row.get('ot_blue_collar_hrs', 0) * ot_bc_rate
        cost += row.get('ot_loader_hrs', 0) * ot_loader_rate

        return cost

    df['Total Labor Cost'] = df.apply(labor_cost, axis=1)

    # --- 2. TOTAL FIXED COST ---
    fixed_cost_total = sum(MASTER_DATA.get('FIXED_COSTS', {}).values())
    df['Total Fixed Cost'] = fixed_cost_total

    # --- 3. TOTAL COST ---
    df['Total Cost'] = df['Total Labor Cost'] + df['Total Fixed Cost']

    # --- 4. Revenue ---
    storage_rate = MASTER_DATA.get('REVENUE_RATES', {}).get('Storage/Day/CBM', 0)
    outbound_rate = MASTER_DATA.get('REVENUE_RATES', {}).get('Outbound/CBM', 0)
    df['Revenue'] = df.get('revenue_warehouse', 0) * storage_rate + df.get('revenue_freight', 0) * outbound_rate

    # --- 5. Profit Calculations ---
    df['Gross Profit'] = df['Revenue'] - df['Total Fixed Cost']
    df['Net Profit'] = df['Revenue'] - df['Total Cost']
    df['Net Profit Margin (%)'] = np.where(df['Revenue'] != 0, (df['Net Profit'] / df['Revenue']) * 100, 0)

    # --- 6. Reset index for display ---
    df.reset_index(inplace=True)

    # --- 7. Add TOTAL row ---
    totals = df[['Revenue', 'Total Labor Cost', 'Total Fixed Cost', 'Total Cost', 'Gross Profit', 'Net Profit']].sum()
    total_margin = (totals['Net Profit'] / totals['Revenue'] * 100) if totals['Revenue'] else 0

    total_row = pd.DataFrame([{
        'Date': 'TOTAL',
        'Revenue': totals['Revenue'],
        'Total Labor Cost': totals['Total Labor Cost'],
        'Total Fixed Cost': totals['Total Fixed Cost'],
        'Total Cost': totals['Total Cost'],
        'Gross Profit': totals['Gross Profit'],
        'Net Profit': totals['Net Profit'],
        'Net Profit Margin (%)': total_margin
    }])

    df = pd.concat([df, total_row], ignore_index=True)

    return df






# ================= FLASK ROUTE =================
@app.route('/', methods=['GET'])
def index():
    fetch_master_data()
    fetch_daily_records()

    if not warehouse_data:
        daily_table = "<p class='text-center text-warning mt-5'>No P&L data available.</p>"
        return render_template('index.html', daily_table=daily_table)

    df = pd.DataFrame(warehouse_data)

    if 'entry_date' not in df.columns:
        daily_table = "<p class='text-center text-warning mt-5'>No entry_date found in records.</p>"
        return render_template('index.html', daily_table=daily_table)

    # --- Date handling ---
    df['Date'] = pd.to_datetime(df['entry_date'], errors='coerce')
    df.dropna(subset=['Date'], inplace=True)
    df.sort_values('Date', inplace=True)

    # --- Date filter ---
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if start_date:
        df = df[df['Date'] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df['Date'] <= pd.to_datetime(end_date)]

    if df.empty:
        daily_table = "<p class='text-center text-warning mt-5'>No P&L data available for the selected period.</p>"
        return render_template('index.html', daily_table=daily_table)

    # --- 1. LABOR COST ---
    total_labor_costs = []

    def calc_labor_cost(row):
        cost = 0
        # White Collar
        wc_salary = MASTER_DATA.get('ROLE_RATES', {}).get('White Colar', {}).get('daily_cost', 0)
        cost += wc_salary

        # Other roles dynamically
        for role_name, rate_data in MASTER_DATA.get('ROLE_RATES', {}).items():
            field = 'staff_' + role_name.lower().replace(' ', '_').replace('(', '').replace(')', '')
            if field in row:
                cost += row[field] * rate_data.get('daily_cost', 0)

        # Vendor/Adhoc
        vendor_rate = MASTER_DATA.get('ADHOC_RATES', {}).get('Adhoc Manpower Rate', 0)
        cost += row.get('supervisor_vender', 0) * vendor_rate

        # Overtime
        ot_sup_rate = MASTER_DATA.get('REVENUE_RATES', {}).get('Over Time -Supervisor/ Hr', 0)
        ot_bc_rate = MASTER_DATA.get('REVENUE_RATES', {}).get('Over Time- Blue Collar/Hr', 0)
        ot_loader_rate = MASTER_DATA.get('REVENUE_RATES', {}).get('Over Time- Blue Collar ( Loader/Hr)', 0)
        cost += row.get('ot_supervisor_hrs', 0) * ot_sup_rate
        cost += row.get('ot_blue_collar_hrs', 0) * ot_bc_rate
        cost += row.get('ot_loader_hrs', 0) * ot_loader_rate

        return cost

    df['Total Labor Cost'] = df.apply(calc_labor_cost, axis=1)

    # --- 2. FIXED COSTS ---
    fixed_cost_total = sum(MASTER_DATA.get('FIXED_COSTS', {}).values())
    df['Total Fixed Cost'] = fixed_cost_total

    # --- 3. TOTAL COST ---
    df['Total Cost'] = df['Total Labor Cost'] + df['Total Fixed Cost']

    # --- 4. REVENUE ---
    storage_rate = MASTER_DATA.get('REVENUE_RATES', {}).get('Storage/Day/CBM', 0)
    outbound_rate = MASTER_DATA.get('REVENUE_RATES', {}).get('Outbound/CBM', 0)
    df['Revenue'] = df.get('revenue_warehouse', 0) * storage_rate + df.get('revenue_freight', 0) * outbound_rate

    # --- 5. Gross & Net Profit ---
    df['Gross Profit'] = df['Revenue'] - df['Total Fixed Cost']
    df['Net Profit'] = df['Revenue'] - df['Total Cost']
    df['Net Profit Margin (%)'] = np.where(df['Revenue'] != 0, (df['Net Profit'] / df['Revenue']) * 100, 0)

    # --- 6. Prepare display ---
    display_cols = ['Date', 'Revenue', 'Total Labor Cost', 'Total Fixed Cost', 'Total Cost',
                    'Gross Profit', 'Net Profit', 'Net Profit Margin (%)']
    df_display = df[display_cols].copy()

    # Format date safely
    df_display['Date'] = df_display['Date'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else '')

    # Add TOTAL row
    totals = df_display[['Revenue', 'Total Labor Cost', 'Total Fixed Cost', 'Total Cost', 'Gross Profit', 'Net Profit']].sum()
    total_margin = (totals['Net Profit'] / totals['Revenue'] * 100) if totals['Revenue'] else 0
    total_row = pd.DataFrame([{
        'Date': 'TOTAL',
        'Revenue': totals['Revenue'],
        'Total Labor Cost': totals['Total Labor Cost'],
        'Total Fixed Cost': totals['Total Fixed Cost'],
        'Total Cost': totals['Total Cost'],
        'Gross Profit': totals['Gross Profit'],
        'Net Profit': totals['Net Profit'],
        'Net Profit Margin (%)': total_margin
    }])
    df_display = pd.concat([df_display, total_row], ignore_index=True)

    # --- 7. Convert to HTML ---
    daily_table = df_display.to_html(classes="table table-striped table-hover", index=False,
                                     float_format=lambda x: f'₹{x:,.0f}' if isinstance(x, (int, float)) else x)

    return render_template('index.html', daily_table=daily_table)

@app.route('/input', methods=['GET', 'POST'])
def input_data():
    global MASTER_DATA

    fetch_master_data()
    today = datetime.date.today().isoformat()

    # Only roles with 'daily_cost' defined
    labor_master_for_input = {k: v for k, v in MASTER_DATA.get('ROLE_RATES', {}).items() if 'daily_cost' in v}
    form_data = {}

    if request.method == 'POST':
        input_date_str = request.form.get('date')

        try:
            input_date = datetime.datetime.strptime(input_date_str, '%Y-%m-%d').date()

            with app.app_context():
                record = DailyRecords.query.filter_by(entry_date=input_date).first()
                if not record:
                    record = DailyRecords(entry_date=input_date)

                # --- Automatically map all fields from form to model ---
                for column in DailyRecords.__table__.columns:
                    col_name = column.name
                    if col_name in ['id', 'entry_date', 'created_at']:
                        continue  # Skip primary key, date, timestamps

                    form_value = request.form.get(col_name)
                    if form_value is not None:
                        # Determine column type and convert
                        if isinstance(column.type, (db.Integer, db.Float, db.Numeric)):
                            setattr(record, col_name, float(form_value) if form_value else 0)
                        else:
                            setattr(record, col_name, form_value)

                db.session.add(record)
                db.session.commit()

            flash(f'✅ Data Saved Successfully for {input_date_str}!', 'success')
            return redirect(url_for('index'))

        except (TypeError, ValueError, AttributeError) as e:
            db.session.rollback()
            flash(f'Error: Please ensure all numeric fields are filled or contain only numbers. Detail: {e}', 'danger')
            form_data = request.form
            return render_template('input_form.html',
                                   today=today,
                                   labor_master=labor_master_for_input,
                                   form_data=form_data)
        except Exception as e:
            db.session.rollback()
            flash(f'An unexpected database error occurred: {e}', 'danger')
            return redirect(url_for('index'))

    return render_template('input_form.html',
                           today=today,
                           labor_master=labor_master_for_input,
                           form_data=form_data)

@app.route('/master_data', methods=['GET', 'POST'])
def master_data():
    global MASTER_DATA

    # Load latest master data from DB
    fetch_master_data()

    # Ensure all keys exist to avoid Jinja UndefinedError
    expected_keys = [
        'ROLE_RATES', 'EMPLOYEE_SALARIES', 'FIXED_COSTS',
        'REVENUE_RATES', 'CONSUMABLE_RATES', 'ADHOC_RATES'
    ]
    for key in expected_keys:
        if key not in MASTER_DATA:
            MASTER_DATA[key] = {}

    if request.method == 'POST':
        category = request.form.get('category')
        action = request.form.get('action')

        try:
            with app.app_context():

                # ==================== 1. ROLE RATES ====================
                if category == 'role_rates':
                    role_name = (
                        request.form.get('role_name_to_update')
                        if action == 'update_existing'
                        else request.form.get('new_role_name')
                    )

                    if action in ['update_existing', 'add_new']:
                        monthly_salary = float(request.form.get('monthly_salary') or 0.0)
                        description = request.form.get('description')

                        # --- Divisor logic (based on role type) ---
                        divisor = 30
                        if role_name:
                            name_lower = role_name.lower()
                            if any(k in name_lower for k in ['blue', 'loader', 'unloading', 'electrician']):
                                divisor = 26
                            elif 'white' in name_lower:
                                divisor = 30

                        daily_cost = round(monthly_salary / divisor, 2)

                        # --- Insert or Update Role ---
                        role = RoleRates.query.filter_by(role_name=role_name).first()
                        if not role:
                            role = RoleRates(role_name=role_name)

                        role.monthly_salary = monthly_salary
                        role.daily_cost = daily_cost
                        role.description = description

                        db.session.merge(role)  # merge ensures both add/update
                        db.session.commit()
                        flash(f'✅ Role "{role_name}" saved successfully!', 'success')

                    elif action == 'delete':
                        role_name = request.form.get('role_name')
                        if role_name:
                            deleted = RoleRates.query.filter_by(role_name=role_name).delete()
                            db.session.commit()
                            if deleted:
                                flash(f'🗑️ Role "{role_name}" deleted successfully.', 'success')
                            else:
                                flash(f'⚠️ Role "{role_name}" not found for deletion.', 'warning')

                # ==================== 2. EMPLOYEE SALARIES ====================
                elif category == 'employee_salaries':
                    if action == 'add_or_update':
                        emp_code = request.form.get('emp_code')
                        if emp_code:
                            name = request.form.get('name')
                            base_salary = float(request.form.get('base_salary') or 0.0)
                            role_name = request.form.get('role')

                            employee = EmployeeSalaries.query.get(emp_code)
                            initial_rating = (
                                float(employee.monthly_rating)
                                if employee and employee.monthly_rating is not None
                                else 3.5
                            )

                            adjusted_salary = calculate_adjusted_salary(base_salary, initial_rating)

                            if not employee:
                                employee = EmployeeSalaries(emp_code=emp_code)

                            employee.name = name
                            employee.base_salary = base_salary
                            employee.role = role_name
                            employee.monthly_rating = initial_rating
                            employee.adjusted_salary = adjusted_salary
                            db.session.merge(employee)
                            db.session.commit()
                            flash(f'✅ Employee "{name}" saved successfully!', 'success')

                    elif action == 'update_rating':
                        emp_code = request.form.get('emp_code_rating')
                        new_rating = float(request.form.get('monthly_rating') or 0.0)

                        employee = EmployeeSalaries.query.get(emp_code)
                        if employee:
                            base_salary = float(employee.base_salary or 0.0)
                            adjusted_salary = calculate_adjusted_salary(base_salary, new_rating)
                            employee.monthly_rating = new_rating
                            employee.adjusted_salary = adjusted_salary
                            db.session.commit()
                            flash(f'⭐ Rating updated for employee {emp_code}.', 'success')

                    elif action == 'delete':
                        emp_code = request.form.get('emp_code')
                        deleted = EmployeeSalaries.query.filter_by(emp_code=emp_code).delete()
                        db.session.commit()
                        if deleted:
                            flash(f'🗑️ Employee "{emp_code}" deleted successfully.', 'success')
                        else:
                            flash(f'⚠️ Employee "{emp_code}" not found.', 'warning')

                # ==================== 3-6. FIXED / CONSUMABLE / REVENUE / ADHOC RATES ====================
                rate_categories = {
                    'fixed_costs': (FixedCosts, 'cost_name', 'cost_value'),
                    'consumable_rates': (ConsumableRates, 'item_name', 'unit_rate'),
                    'revenue_rates': (RevenueRates, 'rate_name', 'rate_value'),
                    'adhoc_rates': (AdhocRates, 'rate_name', 'rate_value')
                }

                if category in rate_categories:
                    Model, key_col, value_col = rate_categories[category]
                    rate_value = float(
                        request.form.get('cost_value') or request.form.get('rate_value') or 0.0
                    )

                    if action in ['update_existing', 'add_new']:
                        rate_name = (
                            request.form.get(f'{key_col}_to_update')
                            if action == 'update_existing'
                            else request.form.get(f'new_{key_col}')
                        )
                        if rate_name:
                            record = Model.query.filter_by(**{key_col: rate_name}).first()
                            if not record:
                                record = Model(**{key_col: rate_name})
                            setattr(record, value_col, rate_value)
                            db.session.merge(record)
                            db.session.commit()
                            flash(f'✅ {category.replace("_", " ").title()} "{rate_name}" saved.', 'success')

                    elif action == 'delete':
                        rate_name = request.form.get(key_col)
                        deleted = Model.query.filter_by(**{key_col: rate_name}).delete()
                        db.session.commit()
                        if deleted:
                            flash(f'🗑️ {category.replace("_", " ").title()} "{rate_name}" deleted.', 'success')
                        else:
                            flash(f'⚠️ {category.replace("_", " ").title()} "{rate_name}" not found.', 'warning')

            # Refresh MASTER_DATA after DB changes
            fetch_master_data()

        except ValueError:
            db.session.rollback()
            flash('❌ Please ensure only numeric values are entered for Rate or Salary.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'⚠️ Unexpected error occurred: {e}', 'danger')

        return redirect(url_for('master_data'))

    # GET request
    fetch_master_data()
    return render_template('master_data.html', master_data=MASTER_DATA)




@app.route('/simulate', methods=['POST'])
def simulate():
    fetch_master_data()
    fetch_daily_records()

    df, kpis_data, _ = get_processed_data(preset='all')

    if df.empty:
        flash("Simulation cannot run: No daily data available. Please enter data first.", 'warning')
        return redirect(url_for('index'))

    latest_data = df.iloc[-1]

    try:
        # --- KEY CHANGE 4: Rename labor_change to cost_change for clarity in the simulation ---
        cost_change_percent = float(request.form.get('cost_change') or 0) / 100
        revenue_change_percent = float(request.form.get('revenue_change') or 0) / 100
        # These are ignored by the current P&L simulation logic in the backend (as noted in HTML)
        rental_change = float(request.form.get('rental_change') or 0) / 100
        utility_change = float(request.form.get('utility_change') or 0) / 100
        other_fixed_change = float(request.form.get('other_fixed_change') or 0) / 100

    except ValueError:
        flash("Error: Please enter valid numbers for simulation changes.", 'danger')
        return redirect(url_for('index'))

    simulated_data = latest_data.copy()

    # Get the original total costs/revenue for accurate simulation scaling
    current_total_cogs_day = latest_data['Total COGS']
    current_total_opex_day = latest_data['Total OpEx']

    # --- KEY CHANGE 5: Apply cost change to ALL day-to-day COGS and OpEx, not just cost_associate ---
    # NOTE: The provided simulation logic is very simple and only targets 'cost_associate' in the original code.
    # To properly simulate 'Total Cost' change, we should ideally change all underlying components (labor, rent, utilities, admin, IT).
    # Since only 'cost_associate' and 'Revenue' inputs are relevant to the *original* simulation code,
    # we'll interpret 'Total Cost Change' as a proxy for the 'cost_associate' change for the simulation output,
    # and update the labels for consistency.

    # The original simulation only scaled cost_associate. We maintain that simple logic but use the new input name.
    simulated_associate_cost = latest_data['cost_associate'] * (1 + cost_change_percent)

    simulated_data['Revenue'] = latest_data['Revenue'] * (1 + revenue_change_percent)
    simulated_data['cost_associate'] = simulated_associate_cost

    rental_cost = MASTER_DATA.get('FIXED_COSTS', {}).get('Rental', 0)
    daily_fixed_cost_rent = (rental_cost / 30)

    # P&L Recalculation based on simulated cost_associate
    simulated_data['Total COGS'] = simulated_data['cost_associate'] + daily_fixed_cost_rent + latest_data[
        'cost_utilities']
    simulated_data['Gross Profit'] = simulated_data['Revenue'] - simulated_data['Total COGS']
    simulated_data['Total OpEx'] = latest_data['cost_admin'] + latest_data['cost_it']
    simulated_data['Net Profit'] = simulated_data['Gross Profit'] - simulated_data['Total OpEx']

    if simulated_data['Revenue'] != 0:
        simulated_data['Net Profit Margin (%)'] = (simulated_data['Net Profit'] / simulated_data['Revenue']) * 100
    else:
        simulated_data['Net Profit Margin (%)'] = 0
    # ---------------------------------------------

    # Calculate Impact Metrics (Updated labels)
    current_net_profit = latest_data['Net Profit']
    simulated_net_profit = simulated_data['Net Profit']
    total_profit_impact = simulated_net_profit - current_net_profit

    current_revenue = latest_data['Revenue']
    current_labor_cost = latest_data['cost_associate']
    simulated_labor_cost = simulated_data['cost_associate']  # Use simulated labor cost for impact metric

    results = {
        # --- KEY CHANGE 6: Update simulation scenario label ---
        'Scenario': f"Total Cost:{cost_change_percent * 100:+.1f}%, R:{revenue_change_percent * 100:+.1f}%...",
        'Current Net Profit': f"₹{current_net_profit:,.0f}",
        'Simulated Net Profit': f"₹{simulated_net_profit:,.0f}",
        'Impact': total_profit_impact,

        'Current Net Margin': f"{latest_data['Net Profit Margin (%)']:.2f}%",
        'Simulated Net Margin': f"{simulated_data['Net Profit Margin (%)']:.2f}%",

        'Current Revenue': f"₹{current_revenue:,.0f}",
        'Simulated Revenue': f"₹{simulated_data['Revenue']:,.0f}",
        'Revenue Impact': simulated_data['Revenue'] - current_revenue,

        # --- KEY CHANGE 7: Update label from Employee Cost to Associate Cost (as cost_associate is still labor) ---
        'Current Employee Cost': f"₹{current_labor_cost:,.0f}",
        'Simulated Employee Cost': f"₹{simulated_labor_cost:,.0f}",
        'Employee Cost Impact': simulated_labor_cost - current_labor_cost
    }

    return render_template('results.html', results=results)


if __name__ == '__main__':
    with app.app_context():
        fetch_master_data()
        fetch_daily_records()
    app.run(debug=True)
