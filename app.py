from flask import Flask, render_template_string, request, redirect, url_for, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import json
import os

app = Flask(__name__)
app.secret_key = 'supersecret'

# Load Excel datasets
fleet_file = 'fleet_50_entries.xlsx'
closure_file = 'Trip_Closure_Sheet_Oct2024_Mar2025.xlsx'

df = pd.read_excel(fleet_file)
df.columns = df.columns.str.strip()
df['Trip Date'] = pd.to_datetime(df['Trip Date'], errors='coerce')
df['Day'] = df['Trip Date'].dt.day

# Load closure data for financial dashboard
closure_df = pd.read_excel(closure_file)
closure_df.columns = closure_df.columns.str.strip()
closure_df['Trip Date'] = pd.to_datetime(closure_df['Trip Date'], errors='coerce')
closure_df['Day'] = closure_df['Trip Date'].dt.day

vehicles = sorted(df['Vehicle ID'].dropna().unique())
routes = sorted(df['Route'].dropna().unique()) if 'Route' in df.columns else []


import os
USER_FILE = os.path.join('/tmp', 'users.json')


# Load users from file if exists
if os.path.exists(USER_FILE):
    with open(USER_FILE, 'r') as f:
        users = json.load(f)
else:
    users = []


TEMPLATES = {
    'signup': '''
    <html><head><title>Sign Up</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-[#0B132B] text-white flex justify-center items-center h-screen">
      <form method="POST" class="bg-[#0E1A36] p-8 rounded-xl space-y-4 w-96">
        <h1 class="text-2xl font-bold text-center">Sign Up</h1>
        <input name="fullname" placeholder="Full Name" class="w-full p-2 rounded bg-[#1C2541]" required>
        <input name="email" type="email" placeholder="Email" class="w-full p-2 rounded bg-[#1C2541]" required>
        <input name="password" type="password" placeholder="Password" class="w-full p-2 rounded bg-[#1C2541]" required>
        <button class="w-full bg-green-500 p-2 rounded" type="submit">Sign Up</button>
        <p class="text-center pt-2">Already have an account? <a href="{{ url_for('login') }}" class="underline">Login</a></p>
      </form>
    </body></html>
    ''',

    'login': '''
    <html><head><title>Login</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-[#0B132B] text-white flex justify-center items-center h-screen">
      <form method="POST" class="bg-[#0E1A36] p-8 rounded-xl space-y-4 w-96">
        <h1 class="text-2xl font-bold text-center">Login</h1>
        <input name="email" type="email" placeholder="Email" class="w-full p-2 rounded bg-[#1C2541]" required>
        <input name="password" type="password" placeholder="Password" class="w-full p-2 rounded bg-[#1C2541]" required>
        <button class="w-full bg-blue-500 p-2 rounded" type="submit">Login</button>
        <p class="text-center pt-2">Don't have an account? <a href="{{ url_for('signup') }}" class="underline">Sign Up</a></p>
      </form>
    </body></html>
    ''',

    'table_page': '''
    <html><head><title>{{ title }}</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-[#0B132B] text-white p-6">
      <h2 class="text-2xl font-bold mb-4">{{ title }}</h2>
      <div class="overflow-x-auto text-sm bg-[#1C2541] p-4 rounded">{{ table|safe }}</div>
      <a href="{{ url_for('dashboard') }}" class="mt-4 inline-block bg-blue-500 px-4 py-2 rounded">Back</a>
    </body></html>
    ''',

    'dashboard': '''
    <html><head><title>Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body class="bg-[#0B132B] text-white p-6 font-sans">
      <h1 class="text-3xl font-bold mb-6">Fleet Owner Dashboard</h1>

      <form method="get" class="flex gap-4 mb-6">
        <select name="vehicle" class="text-black p-2 rounded">
          <option value="">All Vehicles</option>
          {% for v in vehicles %}
            <option value="{{ v }}" {% if v == selected_vehicle %}selected{% endif %}>{{ v }}</option>
          {% endfor %}
        </select>
        <select name="route" class="text-black p-2 rounded">
          <option value="">All Routes</option>
          {% for r in routes %}
            <option value="{{ r }}" {% if r == selected_route %}selected{% endif %}>{{ r }}</option>
          {% endfor %}
        </select>
        <button class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">Apply Filters</button>
      </form>

      <div class="grid grid-cols-3 gap-4 mb-6">
        <div class="bg-[#1C2541] p-4 rounded">
          <p>Total Trips: <b>{{ total_trips }}</b></p>
          <p>Ongoing: <b>{{ ongoing }}</b></p>
          <p>Closed: <b>{{ closed }}</b></p>
          <p>Flags: <b>{{ flags }}</b></p>
          <p>Resolved: <b>{{ resolved }}</b></p>
        </div>
        <div class="bg-[#1C2541] p-4 rounded">
          <p class="font-bold mb-2 text-lg">Financial Summary</p>
          <p>Revenue: ₹{{ rev_m }}M</p>
          <p>Expense: ₹{{ exp_m }}M</p>
          <p>Profit: ₹{{ profit_m }}M</p>
          <p>KMs: {{ kms_k }}K</p>
          <p>Per KM: ₹{{ per_km }}</p>
          <p>Profit %: {{ profit_pct }}%</p>
        </div>
        <div class="bg-[#1C2541] p-4 rounded">
          <p class="font-bold mb-2">AI Report</p>
          <pre class="text-sm text-gray-300">{{ ai_report }}</pre>
          <a href="/download-summary" class="mt-2 inline-block bg-green-600 px-3 py-1 rounded hover:bg-green-700">Download Summary</a>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div class="bg-[#1C2541] p-4 rounded">
          <h2 class="mb-2 font-semibold text-lg">Daily Trips vs Audits</h2>
          <canvas id="auditChart" height="120"></canvas>
        </div>
        <div class="bg-[#1C2541] p-4 rounded">
          <h2 class="mb-2 font-semibold text-lg">Finance Chart</h2>
          <canvas id="financeChart" height="120"></canvas>
        </div>
      </div>

      <div class="mt-6 space-x-4">
        <a href="/trip-generator" class="bg-blue-600 px-4 py-2 rounded">Trip Generator</a>
        <a href="/trip-closure" class="bg-green-600 px-4 py-2 rounded">Trip Closure</a>
        <a href="/trip-auditor" class="bg-yellow-500 px-4 py-2 rounded">Trip Auditor</a>
        <a href="/trip-ongoing" class="bg-purple-600 px-4 py-2 rounded">Ongoing Trips</a>
        <a href="/trip-stats" class="bg-pink-600 px-4 py-2 rounded">Trip Stats</a>
        <a href="/financial-dashboard" class="bg-orange-600 px-4 py-2 rounded">Financial Dashboard</a>
        <a href="/logout" class="bg-red-600 px-4 py-2 rounded">Logout</a>
      </div>

      <script>
        new Chart(document.getElementById('auditChart').getContext('2d'), {
          data: {
            labels: Array.from({length: 31}, (_, i) => i + 1),
            datasets: [
              {type: 'bar', label: 'Closed', data: {{ daily | safe }}, backgroundColor: '#4CAF50'},
              {type: 'bar', label: 'Audited', data: {{ audited | safe }}, backgroundColor: '#2196F3'},
              {type: 'line', label: 'Audit %', data: {{ audit_pct | safe }}, yAxisID: 'y1', borderColor: 'yellow', fill: false}
            ]
          },
          options: {
            responsive: true,
            scales: {
              y: {beginAtZero: true, ticks: {color: 'white'}, grid: {color: '#444'}},
              y1: {beginAtZero: true, position: 'right', ticks: {color: 'white'}, grid: {drawOnChartArea: false}},
              x: {ticks: {color: 'white'}, grid: {color: '#444'}}
            },
            plugins: {legend: {labels: {color: 'white'}}}
          }
        });

        new Chart(document.getElementById('financeChart').getContext('2d'), {
          type: 'bar',
          data: {
            labels: {{ bar_labels | safe }},
            datasets: [{
              label: '₹ in Millions',
              data: {{ bar_values | safe }},
              backgroundColor: ['#FFA500', '#FF4444', '#44FF44']
            }]
          },
          options: {
            plugins: {legend: {labels: {color: 'white'}}},
            scales: {
              y: {beginAtZero: true, ticks: {color: 'white'}},
              x: {ticks: {color: 'white'}}
            }
          }
        });
      </script>
    </body>
    </html>
    '''
}

def generate_ai_report(filtered_df):
    if filtered_df.empty:
        return "No data available for AI report."
    most_profitable_vehicle = filtered_df.groupby('Vehicle ID')['Net Profit'].sum().idxmax()
    top_routes = ", ".join(filtered_df['Route'].value_counts().head(2).index) if 'Route' in filtered_df.columns else "N/A"
    avg_profit_per_trip = round(filtered_df['Net Profit'].sum() / len(filtered_df), 2)
    rev = filtered_df['Freight Amount'].sum()
    exp = filtered_df['Total Trip Expense'].sum()
    profit = filtered_df['Net Profit'].sum()
    kms = filtered_df['Actual Distance (KM)'].sum()
    profit_pct = round((profit / rev * 100), 1) if rev else 0
    per_km = round(profit / kms, 2) if kms else 0
    return f"""
📊 AI Report Highlights:

Total Trips: {len(filtered_df)}
On-going Trips: {filtered_df[filtered_df['Trip Status'] == 'Pending Closure'].shape[0]}
Completed Trips: {filtered_df[filtered_df['Trip Status'] == 'Completed'].shape[0]}
Profit Percentage: {profit_pct}%

Financials:
- Revenue: ₹{round(rev / 1e6, 2)}M
- Expense: ₹{round(exp / 1e6, 2)}M
- Profit: ₹{round(profit / 1e6, 2)}M
- KMs Travelled: {round(kms / 1e3, 1)}K
- Cost per KM: ₹{per_km}

AI Insights:
- Top Vehicle: {most_profitable_vehicle}
- Average Profit per Trip: ₹{avg_profit_per_trip}
- Top Routes: {top_routes}
"""

@app.route('/')
def home():
    return redirect(url_for('signup'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Check if user already exists
        email = request.form['email']
        if any(u['email'] == email for u in users):
            return render_template_string(TEMPLATES['signup'], error="Email already registered!")

        users.append({
            'name': request.form['fullname'],
            'email': email,
            'password': generate_password_hash(request.form['password']),
            'role': 'Owner'
        })
        # Save to file
        with open(USER_FILE, 'w') as f:
            json.dump(users, f)

        return redirect(url_for('login'))

    return render_template_string(TEMPLATES['signup'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = next((u for u in users if u['email'] == request.form['email']), None)
        if user and check_password_hash(user['password'], request.form['password']):
            session['user'] = user
            return redirect(url_for('dashboard'))
        return 'Invalid credentials. <a href="' + url_for('login') + '">Try again</a>'
    return render_template_string(TEMPLATES['login'])

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    vehicle = request.args.get('vehicle')
    route = request.args.get('route')
    filtered = df.copy()
    if vehicle:
        filtered = filtered[filtered['Vehicle ID'] == vehicle]
    if route:
        filtered = filtered[filtered['Route'] == route]

    total_trips = len(filtered)
    ongoing = filtered[filtered['Trip Status'] == 'Pending Closure'].shape[0]
    closed = filtered[filtered['Trip Status'] == 'Completed'].shape[0]
    flags = filtered[filtered['Trip Status'] == 'Under Audit'].shape[0]
    resolved = filtered[(filtered['Trip Status'] == 'Under Audit') & (filtered['POD Status'] == 'Yes')].shape[0]

    rev = filtered['Freight Amount'].sum()
    exp = filtered['Total Trip Expense'].sum()
    profit = filtered['Net Profit'].sum()
    kms = filtered['Actual Distance (KM)'].sum()

    rev_m = round(rev / 1e6, 2)
    exp_m = round(exp / 1e6, 2)
    profit_m = round(profit / 1e6, 2)
    kms_k = round(kms / 1e3, 1)
    per_km = round(profit / kms, 2) if kms else 0
    profit_pct = round((profit / rev) * 100, 1) if rev else 0

    daily = filtered.groupby('Day')['Trip ID'].count().reindex(range(1, 32), fill_value=0).tolist()
    audited = filtered[filtered['Trip Status'] == 'Under Audit'].groupby('Day')['Trip ID'].count().reindex(range(1, 32), fill_value=0).tolist()
    audit_pct = [round(a / b * 100, 1) if b else 0 for a, b in zip(audited, daily)]

    bar_labels = ['Revenue', 'Expense', 'Profit']
    bar_values = [float(rev_m), float(exp_m), float(profit_m)]
    ai_report = generate_ai_report(filtered)

    return render_template_string(TEMPLATES['dashboard'],
        total_trips=total_trips, ongoing=ongoing, closed=closed,
        flags=flags, resolved=resolved, rev_m=rev_m, exp_m=exp_m,
        profit_m=profit_m, kms_k=kms_k, per_km=per_km, profit_pct=profit_pct,
        ai_report=ai_report, vehicles=vehicles, routes=routes,
        selected_vehicle=vehicle, selected_route=route,
        daily=daily, audited=audited, audit_pct=audit_pct,
        bar_labels=bar_labels, bar_values=bar_values)

@app.route('/trip-generator')
def trip_generator():
    data = df[['Trip ID', 'Vehicle ID', 'Trip Status']]
    return render_template_string(TEMPLATES['table_page'], title="Trip Generator", table=data.to_html(classes='text-white', index=False))

@app.route('/trip-closure')
def trip_closure():
    data = df[df['Trip Status'] == 'Pending Closure'][['Trip ID', 'Vehicle ID', 'Trip Status']]
    return render_template_string(TEMPLATES['table_page'], title="Trip Closure", table=data.to_html(classes='text-white', index=False))

@app.route('/trip-auditor')
def trip_auditor():
    data = df[df['Trip Status'] == 'Under Audit'][['Trip ID', 'Vehicle ID', 'POD Status']]
    return render_template_string(TEMPLATES['table_page'], title="Trip Auditor", table=data.to_html(classes='text-white', index=False))

@app.route('/trip-ongoing')
def trip_ongoing():
    data = df[df['Trip Status'] == 'Pending Closure'][['Trip ID', 'Vehicle ID', 'Trip Status']]
    return render_template_string(TEMPLATES['table_page'], title="Ongoing Trips", table=data.to_html(classes='text-white', index=False))

import json  # make sure you have this import at the top if not already present

@app.route('/trip-stats')
def trip_stats():
    days = list(range(1, 32))
    total = df.groupby('Day')['Trip ID'].count().reindex(days, fill_value=0).tolist()
    ongoing = df[df['Trip Status'] == 'Pending Closure'].groupby('Day')['Trip ID'].count().reindex(days, fill_value=0).tolist()
    closed = df[df['Trip Status'] == 'Completed'].groupby('Day')['Trip ID'].count().reindex(days, fill_value=0).tolist()

    # JSON serialize for safe embedding in JS
    total_json = json.dumps(total)
    ongoing_json = json.dumps(ongoing)
    closed_json = json.dumps(closed)

    # Sum totals to display numeric counts
    total_sum = sum(total)
    ongoing_sum = sum(ongoing)
    closed_sum = sum(closed)

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Trip Count Statistics</title>
      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
      <style>
        body {
          background-color: #0d1b2a;
          color: white;
          padding: 20px;
          font-family: Arial, sans-serif;
        }
        .stats-summary {
          display: flex;
          gap: 40px;
          margin-bottom: 15px;
          font-size: 18px;
          font-weight: bold;
          justify-content: center;
        }
        .legend {
          margin-bottom: 15px;
          text-align: center;
        }
        .legend label {
          margin-right: 20px;
          cursor: pointer;
          font-size: 16px;
        }
        input[type="checkbox"] {
          transform: scale(1.2);
          margin-right: 6px;
          vertical-align: middle;
        }
      </style>
    </head>
    <body>
      <h2>Trip Count Statistics</h2>

      <div class="stats-summary">
        <div>Total Trips: {{ total_sum }}</div>
        <div>On-going Trips: {{ ongoing_sum }}</div>
        <div>Trip Closed: {{ closed_sum }}</div>
      </div>

      <div class="legend">
        <label><input type="checkbox" id="totalCheckbox" checked> Total Trips</label>
        <label><input type="checkbox" id="ongoingCheckbox" checked> On-going Trips</label>
        <label><input type="checkbox" id="closedCheckbox" checked> Trip Closed</label>
      </div>
      <canvas id="tripChart" height="120"></canvas>

      <script>
        const ctx = document.getElementById('tripChart').getContext('2d');
        const labels = Array.from({ length: 31 }, (_, i) => i + 1);

        const datasets = [
          {
            label: 'Total Trips',
            backgroundColor: '#f5c518',
            data: {{ total_data }},
          },
          {
            label: 'On-going Trips',
            backgroundColor: '#00c896',
            data: {{ ongoing_data }},
          },
          {
            label: 'Trip Closed',
            backgroundColor: '#007bff',
            data: {{ closed_data }},
          }
        ];

        const config = {
          type: 'bar',
          data: { labels: labels, datasets: datasets },
          options: {
            responsive: true,
            scales: {
              x: {
                ticks: { color: 'white' },
                grid: { display: false }
              },
              y: {
                ticks: { color: 'white' },
                grid: { color: '#33415c' }
              }
            },
            plugins: {
              legend: { display: true, labels: { color: 'white' } }
            }
          }
        };

        const tripChart = new Chart(ctx, config);

        // Checkbox toggling logic
        document.getElementById('totalCheckbox').addEventListener('change', function () {
          tripChart.data.datasets[0].hidden = !this.checked;
          tripChart.update();
        });

        document.getElementById('ongoingCheckbox').addEventListener('change', function () {
          tripChart.data.datasets[1].hidden = !this.checked;
          tripChart.update();
        });

        document.getElementById('closedCheckbox').addEventListener('change', function () {
          tripChart.data.datasets[2].hidden = !this.checked;
          tripChart.update();
        });
      </script>
    </body>
    </html>
    """,
    total_data=total_json, ongoing_data=ongoing_json, closed_data=closed_json,
    total_sum=total_sum, ongoing_sum=ongoing_sum, closed_sum=closed_sum)



@app.route('/financial-dashboard')
def financial_dashboard():
    # Use closure_df for financial stats
    df_fin = closure_df.copy()

    recent_days = sorted(df_fin['Day'].dropna().unique())[-10:]
    day_labels = [f"Day {int(d)}" for d in recent_days]

    daily = df_fin[df_fin['Day'].isin(recent_days)]

    revenue_data = daily.groupby('Day')['Freight Amount'].sum().reindex(recent_days, fill_value=0).astype(int).tolist()
    expense_data = daily.groupby('Day')['Total Trip Expense'].sum().reindex(recent_days, fill_value=0).astype(int).tolist()
    profit_data = [r - e for r, e in zip(revenue_data, expense_data)]

    total_revenue = round(df_fin['Freight Amount'].sum() / 1e6, 2)
    total_profit = round(df_fin['Net Profit'].sum() / 1e6, 2)
    total_km = round(df_fin['Actual Distance (KM)'].sum() / 1e3, 1)

    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Financial Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body {
      background-color: #0d1b2a;
      font-family: Arial, sans-serif;
      color: white;
      padding: 20px;
    }
    .stats {
      display: flex;
      justify-content: space-around;
      margin-bottom: 20px;
      text-align: center;
    }
    .stat-block h1 {
      font-size: 36px;
      margin: 0;
      color: #f5c518;
    }
    .legend {
      display: flex;
      justify-content: center;
      gap: 30px;
      margin-bottom: 20px;
    }
    .legend label {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 16px;
    }
    input[type="checkbox"] {
      transform: scale(1.2);
    }
    canvas {
      background-color: #0d1b2a;
    }
  </style>
</head>
<body>
  <div class="stats">
    <div class="stat-block">
      <h1>₹{{ total_revenue }} M</h1>
      <div>Total Revenue</div>
    </div>
    <div class="stat-block">
      <h1>₹{{ total_profit }} M</h1>
      <div>Total Profit</div>
    </div>
    <div class="stat-block">
      <h1>{{ total_km }} K</h1>
      <div>Total KM Cost</div>
    </div>
  </div>

  <div class="legend">
    <label><input type="checkbox" id="revenueCheckbox" checked> Total Revenue</label>
    <label><input type="checkbox" id="expenseCheckbox" checked> Total Expense</label>
    <label><input type="checkbox" id="profitCheckbox" checked> Trip Profit</label>
  </div>

  <canvas id="financeChart" height="100"></canvas>

  <script>
    const ctx = document.getElementById('financeChart').getContext('2d');
    const days = {{ days | safe }};
    const revenueData = {{ revenue | safe }};
    const expenseData = {{ expense | safe }};
    const profitData = {{ profit | safe }};

    const chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: days,
        datasets: [
          {
            label: 'Total Revenue',
            backgroundColor: '#f5c518',
            data: revenueData
          },
          {
            label: 'Total Expense',
            backgroundColor: '#007bff',
            data: expenseData
          },
          {
            label: 'Trip Profit',
            backgroundColor: '#00c896',
            data: profitData
          }
        ]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false }
        },
        scales: {
          x: {
            ticks: { color: 'white' },
            grid: { display: false }
          },
          y: {
            ticks: { color: 'white' },
            grid: { color: '#33415c' }
          }
        }
      }
    });

    // Toggle logic
    document.getElementById('revenueCheckbox').addEventListener('change', function () {
      chart.data.datasets[0].hidden = !this.checked;
      chart.update();
    });
    document.getElementById('expenseCheckbox').addEventListener('change', function () {
      chart.data.datasets[1].hidden = !this.checked;
      chart.update();
    });
    document.getElementById('profitCheckbox').addEventListener('change', function () {
      chart.data.datasets[2].hidden = !this.checked;
      chart.update();
    });
  </script>
</body>
</html>
    """, days=day_labels, revenue=revenue_data, expense=expense_data, profit=profit_data,
         total_revenue=total_revenue, total_profit=total_profit, total_km=total_km)


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/download-summary')
def download_summary():
    filtered = df
    report = generate_ai_report(filtered)
    with open("AI_Report_Summary.txt", 'w', encoding='utf-8') as f:
        f.write(report)
    return send_file("AI_Report_Summary.txt", as_attachment=True)
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=7860)
