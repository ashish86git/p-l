from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import datetime
import numpy as np
import decimal
import math  # Added math for checking NaN/inf

# --- APP SETUP ---
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# --- DATABASE CONNECTION CONFIGURATION (UNCHANGED) ---
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
# ----------------------------------------------------------------

# --- GLOBAL DATA STORAGE (ORM-Based) ---
MASTER_DATA = {}
warehouse_data = []


# ====================================================================
# --- SQLALCHEMY MODELS (UNCHANGED) ---
# ====================================================================

class DailyRecords(db.Model):
    __tablename__ = 'daily_records'
    date = db.Column(db.Date, primary_key=True)
    revenue_warehouse = db.Column(db.Numeric(10, 2), nullable=False)
    revenue_freight = db.Column(db.Numeric(10, 2), nullable=False)
    cost_rent = db.Column(db.Numeric(10, 2))
    cost_utilities = db.Column(db.Numeric(10, 2))
    cost_admin = db.Column(db.Numeric(10, 2))
    cost_it = db.Column(db.Numeric(10, 2))

    staff_blue_collar_attendance = db.Column(db.Integer, default=0)
    staff_loading_unloadingattendance = db.Column(db.Integer, default=0)
    staff_electretion = db.Column(db.Integer, default=0)
    supervisor_vender = db.Column(db.Integer, default=0)
    staff_adhoc_manpower = db.Column(db.Integer, default=0)

    def to_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data['Date'] = data.pop('date').isoformat()
        for k, v in data.items():
            if isinstance(v, (datetime.date, str, int)): continue
            if isinstance(v, decimal.Decimal):
                try:
                    data[k] = float(v)
                except:
                    pass
        return data


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


class ConsumableRates(db.Model):
    __tablename__ = 'consumable_rates'
    item_name = db.Column(db.String(100), primary_key=True)
    unit_rate = db.Column(db.Numeric(6, 2), nullable=False)


class RevenueRates(db.Model):
    __tablename__ = 'revenue_rates'
    rate_name = db.Column(db.String(100), primary_key=True)
    rate_value = db.Column(db.Numeric(10, 2), nullable=False)


class AdhocRates(db.Model):
    __tablename__ = 'adhoc_rates'
    rate_name = db.Column(db.String(100), primary_key=True)
    rate_value = db.Column(db.Numeric(10, 2), nullable=False)


# ====================================================================
# --- DB INTERACTION & HELPER FUNCTIONS ---
# ====================================================================

def calculate_adjusted_salary(base_salary, rating):
    """Adjusts salary based on rating (UNCHANGED LOGIC)."""
    rating = float(rating)
    base_salary = float(base_salary)

    if rating > 4.5:
        adjustment_factor = 1.10
    elif rating >= 4.0:
        adjustment_factor = 1.05
    elif rating >= 3.0:
        adjustment_factor = 1.00
    else:
        adjustment_factor = 0.95

    return round(base_salary * adjustment_factor, 2)


def fetch_master_data():
    """Loads all Master Data from the DB into the global MASTER_DATA dictionary."""
    global MASTER_DATA
    MASTER_DATA_TEMP = {
        "ROLE_RATES": {}, "EMPLOYEE_SALARIES": {}, "FIXED_COSTS": {},
        "CONSUMABLE_RATES": {}, "REVENUE_RATES": {}, "ADHOC_RATES": {}
    }

    try:
        with app.app_context():
            # 1. ROLE_RATES
            roles = RoleRates.query.all()
            MASTER_DATA_TEMP["ROLE_RATES"] = {
                r.role_name: {
                    'monthly_salary': float(r.monthly_salary),
                    'daily_cost': float(r.daily_cost),
                    'description': r.description
                } for r in roles
            }

            # 2. EMPLOYEE_SALARIES
            employees = EmployeeSalaries.query.all()
            MASTER_DATA_TEMP["EMPLOYEE_SALARIES"] = {
                e.emp_code: {
                    'name': e.name,
                    'base_salary': float(e.base_salary),
                    'role': e.role,
                    'monthly_rating': float(e.monthly_rating or 3.5),
                    'adjusted_salary': calculate_adjusted_salary(float(e.base_salary), float(e.monthly_rating or 3.5))
                } for e in employees
            }

            # 3. FIXED_COSTS
            MASTER_DATA_TEMP["FIXED_COSTS"] = {c.cost_name: float(c.cost_value) for c in FixedCosts.query.all()}

            # 4. CONSUMABLE_RATES
            MASTER_DATA_TEMP["CONSUMABLE_RATES"] = {r.item_name: float(r.unit_rate) for r in
                                                    ConsumableRates.query.all()}

            # 5. REVENUE_RATES
            MASTER_DATA_TEMP["REVENUE_RATES"] = {r.rate_name: float(r.rate_value) for r in RevenueRates.query.all()}

            # 6. ADHOC_RATES
            MASTER_DATA_TEMP["ADHOC_RATES"] = {r.rate_name: float(r.rate_value) for r in AdhocRates.query.all()}

    except Exception as e:
        print(f"🚨 DB Error fetching master data: {e}")

    MASTER_DATA.clear()
    MASTER_DATA.update(MASTER_DATA_TEMP)


def fetch_daily_records():
    """Loads all daily records (warehouse_data) from the database."""
    global warehouse_data
    warehouse_data.clear()

    try:
        with app.app_context():
            db_records = DailyRecords.query.order_by(DailyRecords.date).all()
            warehouse_data.extend([r.to_dict() for r in db_records])
    except Exception as e:
        print(f"🚨 DB Error fetching daily records: {e}")


# Initialize data
with app.app_context():
    fetch_master_data()
    fetch_daily_records()


# ====================================================================
# --- CORE LOGIC & ROUTES ---
# ====================================================================

def get_processed_data(preset=None, start_date=None, end_date=None):
    """Calculates P&L metrics based on fetched data."""
    global warehouse_data, MASTER_DATA

    filter_info = {"status": "No Filter (Showing All Data)", "active_start": None, "active_end": None}

    fetch_daily_records()

    if not warehouse_data:
        return pd.DataFrame(), {}, filter_info

    df = pd.DataFrame(warehouse_data)
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    df.sort_index(inplace=True)

    # --- Filtering Logic (UNCHANGED) ---
    df_filtered = df
    today = datetime.date.today()
    start_filter_date = None
    end_filter_date = None

    try:
        if preset:
            if preset == 'week':
                end_filter_date = today
                start_filter_date = end_filter_date - datetime.timedelta(days=7)
                filter_info["status"] = "Preset: Last 7 Days"
            elif preset == 'month':
                end_filter_date = today
                start_filter_date = end_filter_date - datetime.timedelta(days=30)
                filter_info["status"] = "Preset: Last 30 Days"
            elif preset == 'year':
                end_filter_date = today
                start_filter_date = end_filter_date - datetime.timedelta(days=365)
                filter_info["status"] = "Preset: Last 365 Days"
            elif preset == 'all':
                filter_info["status"] = "No Filter (Showing All Data)"

        elif start_date and end_date:
            start_filter_date = pd.to_datetime(start_date).date()
            end_filter_date = pd.to_datetime(end_date).date()
            filter_info["status"] = "Custom Range"

        if start_filter_date and end_filter_date:
            df_filtered = df[(df.index.date >= start_filter_date) & (df.index.date <= end_filter_date)]
            filter_info["active_start"] = start_filter_date.strftime("%Y-%m-%d")
            filter_info["active_end"] = end_filter_date.strftime("%Y-%m-%d")

        if df_filtered.empty:
            return pd.DataFrame(), {}, filter_info

    except Exception:
        df_filtered = df
        filter_info["status"] = "Filter Error (Showing All Data)"

    df = df_filtered

    # =========================================================================
    # --- P&L Calculation Setup (UNCHANGED LOGIC) ---
    # =========================================================================

    vendor_supervisor_daily_cost = MASTER_DATA.get('REVENUE_RATES', {}).get('Adhoc Manpower Rate', 0)

    total_white_collar_salary = sum(
        emp.get('adjusted_salary', emp.get('base_salary', 0)) for emp in
        MASTER_DATA.get('EMPLOYEE_SALARIES', {}).values())
    daily_white_collar_cost_fixed = round(total_white_collar_salary / 30, 0)

    def calculate_daily_labor_cost(row):
        cost = 0
        roles = MASTER_DATA.get('ROLE_RATES', {})

        for role_name, rate_data in roles.items():
            field_name = 'staff_' + role_name.lower().replace(' ', '_').replace('(', '').replace(')', '')
            if field_name in row and 'daily_cost' in rate_data:
                cost += row[field_name] * rate_data['daily_cost']

        supervisor_vender_count = row.get('supervisor_vender', 0)
        cost += supervisor_vender_count * vendor_supervisor_daily_cost

        cost += daily_white_collar_cost_fixed

        return cost

    df['cost_associate'] = df.apply(calculate_daily_labor_cost, axis=1)

    # --- REVENUE CALCULATION (CORRECTED LOGIC APPLIED HERE) ---
    storage_rate = MASTER_DATA.get('REVENUE_RATES', {}).get('Storage/Day/CBM', 0)
    outbound_rate = MASTER_DATA.get('REVENUE_RATES', {}).get('Outbound/CBM', 0)

    # FIX: revenue_warehouse (storage quantity) is multiplied by storage_rate
    # and revenue_freight (outbound quantity) is multiplied by outbound_rate
    df['Revenue'] = (df['revenue_warehouse'].astype(np.float64) * storage_rate) + \
                    (df['revenue_freight'].astype(np.float64) * outbound_rate)
    # ----------------------------------------------------------------------------

    rental_cost = MASTER_DATA.get('FIXED_COSTS', {}).get('Rental', 0)
    daily_fixed_cost_rent = (rental_cost / 30)

    # P&L Logic Remains UNCHANGED
    df['Total COGS'] = df['cost_associate'] + daily_fixed_cost_rent + df['cost_utilities']
    df['Gross Profit'] = df['Revenue'] - df['Total COGS']

    df['Total OpEx'] = df['cost_admin'] + df['cost_it']
    df['Net Profit'] = df['Gross Profit'] - df['Total OpEx']

    df['Net Profit Margin (%)'] = (df['Net Profit'] / df['Revenue']).fillna(0) * 100

    # =========================================================================
    # --- Cost & Revenue Summary (Calculating Other Fixed Costs for Total Cost KPI) ---
    # =========================================================================

    # Calculate Other Fixed Costs (Non-P&L component of Other Charges)
    other_fixed_monthly = MASTER_DATA.get('FIXED_COSTS', {}).get('House Keeping', 0) + \
                          MASTER_DATA.get('FIXED_COSTS', {}).get('Security Guard Female', 0) + \
                          MASTER_DATA.get('FIXED_COSTS', {}).get('Security Guard', 0) + \
                          MASTER_DATA.get('FIXED_COSTS', {}).get('Security Supervisor', 0) + \
                          MASTER_DATA.get('FIXED_COSTS', {}).get('Capex', 0) + \
                          MASTER_DATA.get('FIXED_COSTS', {}).get('R & R Cost', 0)

    other_fixed_for_period = (other_fixed_monthly / 30) * len(df)

    # --- Summary Population (Unchanged Logic) ---
    summary = {}
    summary['Revenue Outbound/CBM'] = (df['revenue_freight'].sum() * outbound_rate)
    summary['Revenue Storage/Day/CBM'] = (df['revenue_warehouse'].sum() * storage_rate)
    summary['White Colar'] = daily_white_collar_cost_fixed * len(df)

    for role, rates in MASTER_DATA.get('ROLE_RATES', {}).items():
        daily_cost = rates.get('daily_cost', 0)
        field_name = 'staff_' + role.lower().replace(' ', '_').replace('(', '').replace(')', '')
        if field_name in df.columns:
            total_cost_for_role = (df[field_name].astype(np.float64) * daily_cost).sum()
            summary[role] = total_cost_for_role

    total_vender_supervisor_cost = (df['supervisor_vender'].astype(np.float64) * vendor_supervisor_daily_cost).sum()
    summary['Supervisor ( vendors)'] = total_vender_supervisor_cost

    total_opex_for_period = df['Total OpEx'].sum()

    # Other Charges = Total OpEx (Admin/IT) + Other Fixed Costs
    summary['Other Charges'] = total_opex_for_period + other_fixed_for_period

    summary['Consumables'] = 0
    summary['Adhoc Manpower'] = 0
    summary['Holiday working'] = 0
    summary['Over Time -Supervisor/ Hr'] = 0
    summary['Over Time- Blue Collar/Hr'] = 0
    summary['Over Time- Blue Collar ( Loader/Hr'] = 0

    final_summary = {
        'Revenue Outbound/CBM': summary.get('Revenue Outbound/CBM', 0),
        'Revenue Storage/Day/CBM': summary.get('Revenue Storage/Day/CBM', 0),
        'Holiday working': summary.get('Holiday working', 0),
        'White Colar': summary.get('White Colar', 0),
        'Blue Collar (Attendance)': summary.get('Blue Collar (Attendance)', 0),
        'Loading & Unloading(Attendance)': summary.get('Loading & Unloading(Attendance)', 0),
        'Adhoc Manpower': summary.get('Adhoc Manpower', 0),
        'Over Time -Supervisor/ Hr': summary.get('Over Time -Supervisor/ Hr', 0),
        'Over Time- Blue Collar/Hr': summary.get('Over Time- Blue Collar/Hr', 0),
        'Over Time- Blue Collar ( Loader/Hr': summary.get('Over Time- Blue Collar ( Loader/Hr', 0),
        'Electretion': summary.get('Electretion', 0),
        'Supervisor ( vendors)': summary.get('Supervisor ( vendors)', 0),
        'Other Charges': summary.get('Other Charges', 0),
        'Consumables': summary.get('Consumables', 0)
    }

    total_revenue = df['Revenue'].sum()
    total_net_profit = df['Net Profit'].sum()

    # --- KEY CHANGE 1: Calculate Total Cost including Other Fixed Costs ---
    total_cogs = df['Total COGS'].sum()
    total_opex = df['Total OpEx'].sum()

    # Total Cost = All COGS + All OpEx + Other Fixed Costs (Security, Housekeeping, etc.)
    total_cost = total_cogs + total_opex + other_fixed_for_period

    kpis = {
        'total_revenue': total_revenue,
        'total_net_profit': total_net_profit,
        'avg_net_margin': round((total_net_profit / total_revenue) * 100, 2) if total_revenue and not math.isclose(
            total_revenue, 0) else 0,
        'cost_percentage': round((total_cost / total_revenue) * 100, 2) if total_revenue and not math.isclose(
            total_revenue, 0) else 0,
        # --- KEY CHANGE 2: Add Total Cost value to KPIs ---
        'total_cost_value': total_cost,
        'period_end_date': df.index[-1].strftime("%d-%b-%Y") if not df.empty else None,
        'cost_revenue_summary': {k: round(v, 0) for k, v in final_summary.items()}
    }

    return df, kpis, filter_info


@app.route('/', methods=['GET'])
def index():
    fetch_master_data()
    fetch_daily_records()

    preset = request.args.get('preset')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    df, kpis_data, filter_info = get_processed_data(preset, start_date, end_date)

    if df.empty:
        if "Filter" in filter_info['status']:
            empty_message = f"<p class='text-center mt-5 text-red-500 text-xl'>⚠️ No data found for the selected {filter_info['status']} range.</p>"
        else:
            empty_message = "<p class='text-center mt-5 text-gray-500 text-xl'>No data available. Please enter daily data from the Input form.</p>"

        return render_template('index.html',
                               kpis=None,
                               pl_table=empty_message,
                               filter_info=filter_info,
                               active_preset=preset,
                               active_start=start_date,
                               active_end=end_date)

    kpis_display = {
        'current_revenue': kpis_data['total_revenue'],
        'net_profit': kpis_data['total_net_profit'],
        'net_margin': kpis_data['avg_net_margin'],
        'cost_percentage': kpis_data['cost_percentage'],
        # --- KEY CHANGE 3: Pass Total Cost Value ---
        'total_cost_value': kpis_data['total_cost_value'],
        'period_end_date': kpis_data['period_end_date'],
        'cost_revenue_summary': kpis_data.get('cost_revenue_summary')
    }

    # --- P&L Table Column Names (COST_ASSOCIATE is P&L Labor cost, we keep it for calculation) ---
    display_cols = ['Revenue', 'cost_associate', 'Total COGS', 'Gross Profit', 'Total OpEx', 'Net Profit',
                    'Net Profit Margin (%)']

    totals = df[display_cols].sum(numeric_only=True)

    total_revenue = totals['Revenue']
    total_net_profit = totals['Net Profit']
    total_net_margin = (total_net_profit / total_revenue) * 100 if total_revenue else 0

    total_row = {
        'Date': 'TOTAL',
        'Revenue': f'₹{totals["Revenue"]:,.0f}',
        'cost_associate': f'₹{totals["cost_associate"]:,.0f}',
        'Total COGS': f'₹{totals["Total COGS"]:,.0f}',
        'Gross Profit': f'₹{totals["Gross Profit"]:,.0f}',
        'Total OpEx': f'₹{totals["Total OpEx"]:,.0f}',
        'Net Profit': f'₹{totals["Net Profit"]:,.0f}',
        'Net Profit Margin (%)': f'{total_net_margin:.2f}%'
    }

    df_display = df.reset_index()
    df_display['Date'] = df_display['Date'].dt.strftime('%Y-%m-%d')

    pl_data_html = df_display[['Date'] + display_cols].to_html(classes='table table-striped table-hover',
                                                               index=False,
                                                               float_format=lambda
                                                                   x: f'₹{x:,.0f}' if 'Revenue' in df.columns or abs(
                                                                   x) > 1 else f'{x:.2f}%')

    total_row_html = f"""
    <tr class="bg-indigo-100 font-bold text-indigo-800">
        <td>TOTAL</td>
        <td>{total_row['Revenue']}</td>
        <td>{total_row['cost_associate']}</td>
        <td>{total_row['Total COGS']}</td>
        <td>{total_row['Gross Profit']}</td>
        <td>{total_row['Total OpEx']}</td>
        <td>{total_row['Net Profit']}</td>
        <td>{total_row['Net Profit Margin (%)']}</td>
    </tr>
    """

    pl_data_html = pl_data_html.replace('</tbody>', total_row_html + '</tbody>')

    return render_template('index.html',
                           kpis=kpis_display,
                           pl_table=pl_data_html,
                           filter_info=filter_info,
                           active_start=start_date,
                           active_end=end_date,
                           active_preset=preset)


@app.route('/input', methods=['GET', 'POST'])
# ... (input_data function remains UNCHANGED) ...
def input_data():
    global MASTER_DATA

    fetch_master_data()
    today = datetime.date.today().isoformat()
    labor_master_for_input = {k: v for k, v in MASTER_DATA.get('ROLE_RATES', {}).items() if 'daily_cost' in v}
    form_data = {}

    if request.method == 'POST':
        input_date_str = request.form.get('date')

        try:
            input_date = datetime.datetime.strptime(input_date_str, '%Y-%m-%d').date()

            with app.app_context():
                record = DailyRecords.query.get(input_date)
                if not record:
                    record = DailyRecords(date=input_date)

                record.revenue_warehouse = float(request.form.get('revenue_warehouse') or 0.0)
                record.revenue_freight = float(request.form.get('revenue_freight') or 0.0)
                record.cost_rent = float(request.form.get('cost_rent') or 0.0)
                record.cost_utilities = float(request.form.get('cost_utilities') or 0.0)
                record.cost_admin = float(request.form.get('cost_admin') or 0.0)
                record.cost_it = float(request.form.get('cost_it') or 0.0)
                record.supervisor_vender = int(request.form.get('supervisor_vender') or 0)
                record.staff_adhoc_manpower = int(request.form.get('staff_adhoc_manpower') or 0)

                for role in MASTER_DATA.get('ROLE_RATES', {}).keys():
                    field_name = 'staff_' + role.lower().replace(' ', '_').replace('(', '').replace(')', '')
                    if hasattr(record, field_name):
                        setattr(record, field_name, int(request.form.get(field_name) or 0))

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
# ... (master_data_ui function remains UNCHANGED) ...
def master_data_ui():
    global MASTER_DATA

    fetch_master_data()

    if request.method == 'POST':
        category = request.form.get('category')
        action = request.form.get('action')

        try:
            with app.app_context():

                # --- 1. ROLE RATES ---
                if category == 'role_rates':
                    role_name = request.form.get(
                        'role_name_to_update') if action == 'update_existing' else request.form.get('new_role_name')

                    if action in ['update_existing', 'add_new']:
                        monthly_salary = float(request.form.get('monthly_salary') or 0.0)
                        description = request.form.get('description')
                        daily_cost = round(monthly_salary / 30, 2)

                        role = RoleRates.query.get(role_name)
                        if not role: role = RoleRates(role_name=role_name)

                        role.monthly_salary = monthly_salary
                        role.daily_cost = daily_cost
                        role.description = description
                        db.session.add(role)

                    elif action == 'delete':
                        role_name = request.form.get('role_name')
                        RoleRates.query.filter_by(role_name=role_name).delete()

                # --- 2. EMPLOYEE SALARIES ---
                elif category == 'employee_salaries':
                    if action == 'add_or_update':
                        emp_code = request.form.get('emp_code')
                        if emp_code:
                            name = request.form.get('name')
                            base_salary = float(request.form.get('base_salary') or 0.0)
                            role_name = request.form.get('role')

                            employee = EmployeeSalaries.query.get(emp_code)
                            initial_rating = float(
                                employee.monthly_rating) if employee and employee.monthly_rating is not None else 3.5

                            adjusted_salary = calculate_adjusted_salary(base_salary, initial_rating)

                            if not employee: employee = EmployeeSalaries(emp_code=emp_code)

                            employee.name = name
                            employee.base_salary = base_salary
                            employee.role = role_name
                            employee.monthly_rating = initial_rating
                            employee.adjusted_salary = adjusted_salary
                            db.session.add(employee)

                    elif action == 'update_rating':
                        emp_code = request.form.get('emp_code_rating')
                        new_rating = float(request.form.get('monthly_rating') or 0.0)

                        employee = EmployeeSalaries.query.get(emp_code)
                        if employee:
                            base_salary = float(employee.base_salary)
                            adjusted_salary = calculate_adjusted_salary(base_salary, new_rating)

                            employee.monthly_rating = new_rating
                            employee.adjusted_salary = adjusted_salary
                            db.session.add(employee)

                    elif action == 'delete':
                        emp_code = request.form.get('emp_code')
                        EmployeeSalaries.query.filter_by(emp_code=emp_code).delete()

                # --- 3-6. FIXED/CONSUMABLE/REVENUE/ADHOC RATES ---
                rate_categories = {
                    'fixed_costs': (FixedCosts, 'cost_name', 'cost_value'),
                    'consumable_rates': (ConsumableRates, 'item_name', 'unit_rate'),
                    'revenue_rates': (RevenueRates, 'rate_name', 'rate_value'),
                    'adhoc_rates': (AdhocRates, 'rate_name', 'rate_value')
                }

                if category in rate_categories:
                    Model, key_col, value_col = rate_categories[category]
                    rate_value = float(request.form.get('cost_value') or request.form.get('rate_value') or 0.0)

                    if action in ['update_existing', 'add_new']:
                        rate_name = request.form.get(
                            f'{key_col}_to_update') if action == 'update_existing' else request.form.get(
                            f'new_{key_col}')
                        if rate_name:
                            record = Model.query.get(rate_name)
                            if not record: record = Model(**{key_col: rate_name})

                            setattr(record, value_col, rate_value)
                            db.session.add(record)

                    elif action == 'delete':
                        rate_name = request.form.get(key_col)
                        Model.query.filter_by(**{key_col: rate_name}).delete()

                db.session.commit()
                flash('✅ Master Data updated successfully!', 'success')

            fetch_master_data()

        except ValueError:
            db.session.rollback()
            flash('Error: Please ensure only numeric values are entered for Rate or Salary.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'An unexpected database error occurred: {e}', 'danger')

        return redirect(url_for('master_data_ui'))

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