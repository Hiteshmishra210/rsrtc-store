import sqlite3

DB_PATH = "store.db"

def db():
    con = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL;")
    return con
def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS purchase_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        po_no TEXT,
        po_date TEXT,
        last_date TEXT,
        firm TEXT,
        category TEXT,
        code TEXT,
        name TEXT,
        qty TEXT,
        total TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS delivery_schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        firm TEXT,
        po_no TEXT,
        code TEXT,
        name TEXT,
        from_date TEXT,
        to_date TEXT,
        qty REAL,
        delivered INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS grs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grs_no TEXT,
        grs_date TEXT,
        firm TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS grs_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grs_id INTEGER,
        category TEXT,
        code TEXT,
        name TEXT,
        qty REAL,
        price REAL,
        total REAL
    )
    """)

    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS opening_stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        code TEXT,
        name TEXT,
        qty REAL,
        entry_date TEXT
        
    )
    """)

    # Current stock
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        code TEXT,
        name TEXT,
        qty REAL DEFAULT 0,
        entry_date TEXT
    )
    """)

    # Stock ledger (date-wise history)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stock_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date TEXT,
        category TEXT,
        code TEXT,
        name TEXT,
        qty REAL,
        source TEXT   -- 'OPENING' or 'GRS'
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS challan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challan_no TEXT,
        challan_date TEXT,
        depot TEXT,          -- TO depot
        from_depot TEXT,      -- FROM depot (jisne banaya)
        status TEXT DEFAULT 'draft',   -- draft | sent | approved | rejected
        sent_on TEXT,
        approved_on TEXT,
        grs_no TEXT,
        grs_date TEXT
   

    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS challan_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challan_id INTEGER,
        category TEXT,
        code TEXT,
        name TEXT,
        qty REAL,
        price REAL,
        total REAL


    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_opening_stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        category TEXT,
        code TEXT,
        name TEXT,
        qty REAL,
        entry_date TEXT
        
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_grs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        grs_no TEXT,
        grs_date TEXT,
        firm TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_grs_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grs_id INTEGER,
        category TEXT,
        code TEXT,
        name TEXT,
        qty REAL,
        price REAL,
        total REAL
    )
    """)
  
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        category TEXT,
        code TEXT,
        name TEXT,
        qty REAL DEFAULT 0,
        entry_date TEXT
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_indent (
    	id INTEGER PRIMARY KEY AUTOINCREMENT,
    	user TEXT,
    	indent_no TEXT,
    	indent_date TEXT,
    	vehicle_no TEXT
     )
     """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_indent_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
   	indent_id INTEGER,
        category TEXT,
   	code TEXT,
    	name TEXT,
        qty REAL
     )
     """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_stock_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        entry_date TEXT,
        category TEXT,
        code TEXT,
        name TEXT,
        qty REAL,
        source TEXT   -- OPENING, GRS, ISSUE        
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS demand_letter (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        letter_no TEXT,
        letter_date TEXT,
        status TEXT DEFAULT 'draft',   -- draft | sent | received
        is_final INTEGER DEFAULT 0
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS demand_letter_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        letter_id INTEGER,
        category TEXT,
        code TEXT,
        name TEXT,
        demand_qty REAL,
        stock_at_time REAL,
        last_3m_consumption REAL,
        issue_1st TEXT,
        issue_2nd TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_pinned_items (
        user TEXT,
        category TEXT,
        code TEXT,
        PRIMARY KEY (user, category, code)
    )
    """)





    con.commit()
    con.close()



 

 

from flask import Flask, request, render_template_string, redirect, session, make_response

app = Flask(__name__)
app.secret_key = "rsrtc_secret_key"

import os, pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ITEM_FILE = os.path.join(BASE_DIR, "items.xlsx")

def get_items():
    df = pd.read_excel(ITEM_FILE, dtype=str)
    df.columns = df.columns.str.strip().str.lower()   # 👈 headers clean
    return df.fillna("").astype(str)



@app.route("/api/item_lookup")
def item_lookup():
    by = request.args.get("by")
    q = request.args.get("q", "").strip().lower()
    cat = request.args.get("cat", "").strip().lower()   # ⭐ ADD THIS

    df = get_items()

    df["category"] = df["category"].str.strip().str.lower()
    df["code"] = df["code"].str.strip().str.lower()
    df["name"] = df["name"].str.strip().str.lower()

    if not q:
        return {"ok": False, "results": []}

    # 🔍 SEARCH FILTER
    if by == "code":
        r = df[df["code"].str.contains(q)]
    elif by == "name":
        r = df[df["name"].str.contains(q)]
    elif by == "category":
        r = df[df["category"].str.contains(q)]
    else:
        return {"ok": False, "results": []}

    # 🔒 CATEGORY LOCK (ONLY IF PASSED)
    if cat:
        r = r[r["category"] == cat]

    out = r.head(15).to_dict(orient="records")
    return {"ok": True, "results": out}




# ---------------- USERS ----------------
# ---------------- USERS ----------------
USERS = {"admin": "1234"}

# ---------------- USERS ----------------
USERS = {"admin": "1234"}

DEPOTS = [
    "ABU ROAD","AJAYMERU","AJMER","ALWAR","ANOOPGARH","BANSWARA","BARAN",
    "BARMER","BEAWAR","BHARATPUR","BHILWARA","BIKANER","BUNDI","CHITTORGARH",
    "CHURU","DAUSA","DELUXE","DHOLPUR","DIDWANA","DUNGARPUR","FALNA",
    "GANGANAGAR","HANUMANGARH","HINDAUN","JAIPUR","JAISALMER","JALORE",
    "JHALAWAR","JHUNJHUNU","JODHPUR","KAROLI","KHETRI","KOTA","KOTPUTLI",
    "LOHAGARH","MATSAYA NAGAR","NAGAUR","PALI","PHALODI","PRATAPGARH",
    "RAJSAMAND","SARDAR SHAHAR","SAWAIMADHOPUR","SHAHPURA","SHRIMADHOPUR",
    "SIKAR","SIROHI","TIJARA","TONK","UDAIPUR","VAISHALI NAGAR",
    "VIDYADHAR NAGAR","CWS AJMER","CWS JAIPUR","CWS JODHPUR"
]

# Depot users: ID = CAPITAL, Password = small without spaces
for depot in DEPOTS:
    USERS[depot] = depot.lower().replace(" ", "")

# Extra users (optional)
for i in range(56, 66):
    USERS[f"user{i}"] = f"user{i}".lower()




# ---------------- GLOBAL NO-CACHE ----------------
@app.after_request
def add_no_cache_headers(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


# ---------------- HOME ----------------
@app.route("/")
def home():
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>RSRTC Store</title>
    <meta name="color-scheme" content="light">
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
<div class="box">
    <h2>RSRTC Store Management System</h2>
    <p>by Hitesh mishra<p>
    <p><a href="/login" class="login-link">Login Here</a></p>
</div>
</body>
</html>
"""
    return make_response(html)


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    msg = session.pop("login_msg", "")

    if request.method == "POST":
        u = request.form.get("userid")
        p = request.form.get("password")

        if u in USERS and USERS[u] == p:
            session["user"] = u
            return redirect("/admin" if u == "admin" else "/user")
        else:
            session["login_msg"] = "❌ Invalid ID or Password"
            return redirect("/login")

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Login</title>
    <meta name="color-scheme" content="light">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
<div class="box">
    <h2>Login</h2>

    <form method="post" autocomplete="off">
        <input name="userid" placeholder="User ID" autocomplete="off" required><br><br>
        <input type="password" name="password" placeholder="Password"
               autocomplete="new-password" required><br><br>
        <button type="submit">Login</button>
    </form>

    <p style="color:red;">{msg}</p>
</div>
</body>
</html>
"""
    return make_response(html)



# ---------------- USER PAGE ----------------
@app.route("/user")
def user_page():
    user = session.get("user")
    if not user or user == "admin":
        return redirect("/login")

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>User Panel</title>
    <meta name="color-scheme" content="light">
    <link rel="stylesheet" href="/static/style.css">

    <style>
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            padding: 30px;
        }}
        .card {{
            background: #006060;
            color: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 0 8px #999;
        }}
        .card h3 {{
            margin-top: 0;
            border-bottom: 1px solid #ccc;
            padding-bottom: 8px;
        }}
        .card a {{
            display: block;
            color: white;
            text-decoration: none;
            margin: 6px 0;
            padding: 6px;
            border-radius: 4px;
            background: rgba(255,255,255,0.15);
        }}
        .card a:hover {{
            background: rgba(255,255,255,0.3);
        }}
        .topbar {{
            position: absolute;
            top: 15px;
            right: 20px;
        }}
        .topbar a {{
            margin-left: 15px;
            font-weight: bold;
            color: #006060;
            text-decoration: none;
        }}
    </style>
</head>
<body>

<div class="topbar">
    <a href="/change_password">Change Password</a>
    <a href="/logout">Logout</a>
</div>

<h2 style="padding:20px;">Welcome User: <b>{user}</b></h2>

<div class="grid">

    <div class="card">
        <h3>📊 Opening Stock</h3>
        <a href="/user/opening/pg">PG</a>
        <a href="/user/opening/gs">GS</a>
        <a href="/user/opening/tata">Tata</a>
        <a href="/user/opening/leyland">Leyland</a>
        <a href="/user/opening/eicher">Eicher</a>
        <a href="/user/opening/sl">SL</a>
        <a href="/user/opening/rc assembly">Rc Assembly</a>
        <a href="/user/opening/others">Others</a>
    </div>

    <div class="card">
        <h3>📑 GRS</h3>
        <a href="/user/grs/new">➕ Generate New GRS</a>
            <a href="/user/grs/detail">➕ GRS Detail</a>
    </div>

    <div class="card">
        <h3>🚚 Issue Items</h3>
        <a href="/user/issue/own">➕ Own Depot Issue Indent</a>
        <a href="/user/issue/own/detail">📄 Own Depot Indent Detail</a>

        <a href="/user/issue/other">➕ Generate Other Depot Challan</a>
        <a href="/user/issue/other/detail">📄 Other Depot Challan Detail</a>
        <a href="/user/challan/inbox">📥 Received Challan</a>
    </div>


    <div class="card">
        <h3>📦 Inventory</h3>
        <a href="/user/inv/own">Own Depot</a>
        <a href="/user/inv/other">Other Depot</a>
        <a href="/user/inv/central">Central Store</a>
    </div>

    <div class="card">
        <h3>📝 Central Store demand letter</h3>
        <a href="/user/demand_letter">Create / View</a>
        <a href="/user/demand_letter_detail">📄 Demand Detail</a>
    </div>
    <div class="card">
        <h3>Others</h3>
        <a href="/user/others/dead-stock">Dead Stock</a>
        <a href="/user/others/mis">MIS</a>
        <a href="/user/others/ai">AI</a>
    </div>

</div>
</body>
</html>
"""
    return make_response(html)

@app.route("/user/challan/inbox")
def user_challan_inbox():
    user = session.get("user")
    if not user:
        return redirect("/login")

    con = db()
    cur = con.cursor()

    rows = cur.execute("""
        SELECT * FROM challan
        WHERE depot=? AND status='sent'
        ORDER BY id DESC
    """, (user,)).fetchall()

    con.close()

    cards = ""
    for c in rows:
        cards += f"""
        <div class="card">
            <b>Challan No:</b> {c['challan_no']}<br>
            <b>Date:</b> {c['challan_date']}<br>
            <b>From Depot:</b> {c['from_depot']}<br><br>
            <a class="btn" href="/user/challan/view/{c['id']}">Open & Approve</a>
        </div>
        """

    if not cards:
        cards = "<p>No new challan received.</p>"

    return f"""
<!DOCTYPE html>
<html>
<head>
<title>Received Challan</title>
<style>
body {{ font-family: Arial; background:#f4f6f9; padding:20px; }}
.card {{
  background:white; padding:15px; margin-bottom:15px;
  border-radius:6px; box-shadow:0 0 6px #bbb;
}}
.btn {{
  display:inline-block; padding:8px 12px;
  background:#006060; color:white;
  text-decoration:none; border-radius:4px;
}}
.btn:hover {{ background:#004d4d; }}
</style>
</head>
<body>

<h2>📥 Received Challans</h2>
{cards}
<br>
<a href="/user">⬅ Back</a>

</body>
</html>
"""
@app.route("/user/challan/view/<int:id>")
def user_challan_view(id):
    user = session.get("user")
    if not user:
        return redirect("/login")

    con = db()
    cur = con.cursor()

    challan = cur.execute("""
        SELECT * FROM challan
        WHERE id=? AND depot=? AND status='sent'
    """, (id, user)).fetchone()

    if not challan:
        con.close()
        return "Invalid challan"

    items = cur.execute("""
        SELECT * FROM challan_items WHERE challan_id=?
    """, (id,)).fetchall()

    con.close()

    trs = ""
    for i, it in enumerate(items, 1):
        trs += f"""
        <tr>
          <td>{i}</td>
          <td>{it['category']}</td>
          <td>{it['code']}</td>
          <td>{it['name']}</td>
          <td>{it['qty']}</td>
        </tr>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
<title>View Challan</title>
<style>
body {{ font-family: Arial; background:#f4f6f9; padding:20px; }}
table {{ width:100%; border-collapse:collapse; background:white; }}
th,td {{ border:1px solid #ccc; padding:8px; text-align:center; }}
th {{ background:#006060; color:white; }}
.actions a {{
  display:inline-block; margin-right:10px;
  padding:8px 12px; background:#006060;
  color:white; text-decoration:none; border-radius:4px;
}}
</style>
</head>
<body>

<h2>Challan No: {challan['challan_no']}</h2>
<p>Date: {challan['challan_date']} | From: {challan['from_depot']}</p>

<table>
<tr>
  <th>#</th><th>Category</th><th>Code</th><th>Name</th><th>Qty</th>
</tr>
{trs}
</table>

<br>
<div class="actions">
  <a href="/user/challan/approve/{id}">Approve Challan</a>
  <a href="/user/challan/inbox">⬅ Back</a>
</div>

</body>
</html>
"""
@app.route("/user/challan/approve/<int:id>", methods=["GET", "POST"])
def user_challan_approve(id):
    user = session.get("user")
    if not user:
        return redirect("/login")

    con = db()
    cur = con.cursor()

    challan = cur.execute("""
        SELECT * FROM challan
        WHERE id=? AND depot=? AND status='sent'
    """, (id, user)).fetchone()

    items = cur.execute("""
        SELECT * FROM challan_items WHERE challan_id=?
    """, (id,)).fetchall()

    if request.method == "POST":
        grs_no = request.form["grs_no"]
        grs_date = request.form["grs_date"]

        cur.execute("""
            INSERT INTO user_grs (user, grs_no, grs_date, firm)
            VALUES (?,?,?,?)
        """, (user, grs_no, grs_date, challan["from_depot"]))
        grs_id = cur.lastrowid

        for it in items:
            cur.execute("""
                INSERT INTO user_grs_items
                (grs_id, category, code, name, qty, price, total)
                VALUES (?,?,?,?,?,?,?)
            """, (
                grs_id,
                it["category"], it["code"], it["name"],
                it["qty"], it["price"], it["total"]
            ))

            row = cur.execute("""
                SELECT id FROM user_inventory
                WHERE user=? AND category=? AND code=?
            """, (user, it["category"], it["code"])).fetchone()

            if row:
                cur.execute("""
                    UPDATE user_inventory SET qty = qty + ?
                    WHERE id=?
                """, (it["qty"], row["id"]))
            else:
                cur.execute("""
                    INSERT INTO user_inventory
                    (user, category, code, name, qty)
                    VALUES (?,?,?,?,?)
                """, (user, it["category"], it["code"], it["name"], it["qty"]))

        cur.execute("""
            UPDATE challan
            SET status='approved',
                grs_no=?,
                grs_date=?
            WHERE id=?
        """, (grs_no, grs_date, id))

        con.commit()
        con.close()
        return redirect("/user/grs/detail")

    con.close()

    return f"""
<!DOCTYPE html>
<html>
<head>
<title>Approve Challan</title>
<style>
body {{ font-family: Arial; background:#f4f6f9; padding:20px; }}
.form {{
  background:white; padding:20px;
  border-radius:6px; width:300px;
  box-shadow:0 0 6px #bbb;
}}
input,button {{
  width:100%; padding:8px;
  margin-top:10px;
}}
button {{
  background:#006060; color:white;
  border:none; border-radius:4px;
}}
</style>
</head>
<body>

<h2>Approve Challan: {challan['challan_no']}</h2>

<div class="form">
<form method="post">
    <label>GRS No</label>
    <input name="grs_no" required>

    <label>GRS Date</label>
    <input type="date" name="grs_date" required>

    <button type="submit">Approve & Add Stock</button>
</form>
</div>

<br>
<a href="/user/challan/view/{id}">⬅ Back</a>

</body>
</html>
"""


# ---------------- ADMIN PAGE ----------------
@app.route("/admin")
def admin_page():
    if session.get("user") != "admin":
        return redirect("/login")

    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Panel</title>
    <meta name="color-scheme" content="light">
    <link rel="stylesheet" href="/static/style.css">

    <script>
        history.pushState(null, null, location.href);
        window.onpopstate = function () {
            history.go(1);
        };
    </script>

    <style>
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            padding: 30px;
        }
        .card {
            background: #003d80;
            color: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 0 8px #999;
        }
        .card h3 {
            margin-top: 0;
            border-bottom: 1px solid #ccc;
            padding-bottom: 8px;
        }
        .card a {
            display: block;
            color: white;
            text-decoration: none;
            margin: 6px 0;
            padding: 6px;
            border-radius: 4px;
            background: rgba(255,255,255,0.15);
        }
        .card a:hover {
            background: rgba(255,255,255,0.3);
        }
        .topbar {
            position: absolute;
            top: 15px;
            right: 20px;
        }
        .topbar a {
            margin-left: 15px;
            font-weight: bold;
            color: #003d80;
            text-decoration: none;
        }
    </style>
</head>
<body>

<div class="topbar">
    <a href="/change_password" class="login-link">Change Password</a>
    <a href="/admin/download_db" class="top-btn">⬇️ Download DB</a>
    <a href="/logout" class="login-link">Logout</a>
    
</div>

<h2 style="padding:20px;">Welcome Central Store</h2>

<div class="grid">

    <div class="card">
        <h3>📦 Receiving Stock</h3>
        <a href="/admin/po">Purchase Order</a>
        <a href="/admin/delivery">Delivery Schedule</a>

        <div class="submenu">
            <span>GRS</span>
            <a href="/admin/grs/new">➕ Generate New GRS</a>
            <a href="/admin/grs/detail">➕ GRS Detail</a>
        </div>
    </div>
    <div class="card">
        <h3>Opening Stock</h3>
        <a href="/admin/opening/pg">PG</a>
        <a href="/admin/opening/gs">GS</a>
        <a href="/admin/opening/tata">Tata</a>
        <a href="/admin/opening/leyland">Leyland</a>
        <a href="/admin/opening/eicher">Eicher</a>
        <a href="/admin/opening/sl">SL</a>
        <a href="/admin/opening/others">Others</a>
    </div>

    <div class="card">
        <h3>🚚 Issue Stock</h3>
        <a href="/admin/challan">➕ Generate Challan</a>
        <a href="/admin/challan/detail">📄 Challan Detail</a>
        <a href="/admin/demand_receive">📥 Receive Demand</a>
    </div>

    <div class="card">
        <h3>📊 Inventory</h3>
        <a href="/admin/inv/pg">PG</a>
        <a href="/admin/inv/gs">GS</a>
        <a href="/admin/inv/tata">Tata</a>
        <a href="/admin/inv/leyland">Leyland</a>
        <a href="/admin/inv/eicher">Eicher</a>
        <a href="/admin/inv/sl">SL</a>
        <a href="/admin/inv/others">Others</a>
    </div>

    <div class="card">
        <h3>🏭 Depot Wise Inventory</h3>
        <a href="/admin/depot_inventory">Open</a>
    </div>
    <div class="card">
        <h3>Others</h3>
        <a href="/admin/others/dead-stock">Dead Stock</a>
        <a href="/admin/others/mis">MIS</a>
        <a href="/admin/others/ai">AI</a>
    </div>

</div>

</body>
</html>
"""
    return make_response(html)




# ---------------- CHANGE PASSWORD (ADMIN + USER) ----------------
@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    user = session.get("user")
    if not user:
        return redirect("/login")

    msg = ""
    if request.method == "POST":
        old = request.form.get("old")
        new = request.form.get("new")

        if USERS.get(user) == old:
            USERS[user] = new
            msg = "✅ Password changed successfully"
        else:
            msg = "❌ Old password incorrect"

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Change Password</title>
    <meta name="color-scheme" content="light">
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
<div class="box">
    <h2>Change Password</h2>

    <form method="post">
        <input type="password" name="old" placeholder="Old Password" required><br><br>
        <input type="password" name="new" placeholder="New Password" required><br><br>
        <button type="submit">Change</button>
    </form>

    <p>{msg}</p>
    <br>
    <a href="/{'admin' if user=='admin' else 'user'}" class="login-link">Back</a>
</div>
</body>
</html>
"""
    return make_response(html)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
from flask import send_file
import os

@app.route("/admin/download_db")
def admin_download_db():
    if session.get("user") != "admin":
        return redirect("/login")

    db_path = os.path.join(os.getcwd(), "store.db")  # same folder as app.py

    if not os.path.exists(db_path):
        return "Database file not found", 404

    return send_file(db_path, as_attachment=True)


from datetime import date

@app.route("/admin/po", methods=["GET", "POST"])
def purchase_order():
    if session.get("user") != "admin":
        return redirect("/login")

    msg = ""
    con = db()
    cur = con.cursor()

    # -------- Save PO (MULTIPLE ITEMS) --------
    if request.method == "POST":
        po_no = request.form.get("po_no").strip()
        po_date = request.form.get("po_date")
        last_date = request.form.get("last_date")
        firm = request.form.get("firm").strip()

        cats = request.form.getlist("category[]")
        codes = request.form.getlist("code[]")
        names = request.form.getlist("name[]")
        qtys = request.form.getlist("qty[]")
        totals = request.form.getlist("total[]")

        if po_no and po_date and last_date and firm and names:
            for i in range(len(names)):
                if names[i].strip():
                    cur.execute("""
                        INSERT INTO purchase_orders
                        (po_no, po_date, last_date, firm, category, code, name, qty, total)
                        VALUES (?,?,?,?,?,?,?,?,?)
                    """, (
                        po_no, po_date, last_date, firm,
                        cats[i].strip(), codes[i].strip(), names[i].strip(),
                        qtys[i].strip(), totals[i].strip()
                    ))
            con.commit()
            msg = "✅ Purchase Order saved"

    # -------- Read all PO --------
    rows = cur.execute("SELECT * FROM purchase_orders ORDER BY firm").fetchall()
    con.close()

    # Group firm-wise
    firms = {}
    for r in rows:
        firms.setdefault(r["firm"], []).append(r)

    today = date.today().isoformat()

    firm_html = ""
    for firm, items in firms.items():
        firm_id = firm.replace(" ", "_")

        firm_html += f"""
<div id="{firm_id}">
  <div class="firm-head">
    <span class="firm-name">{firm}</span>
    <button class="print-btn" onclick="printSection('{firm_id}')" title="Print">🖨️</button>
  </div>

<table class="po-table">
<tr>
  <th>PO No</th><th>PO Date</th><th>Last Date</th>
  <th>Cat</th><th>Code</th><th class="wide">Item Name</th>
  <th>Qty</th><th>Total</th><th>Action</th>
</tr>
"""
        for r in items:
            is_late = r["last_date"] and r["last_date"] < today
            style = "style='background:#ffcccc;'" if is_late else ""

            firm_html += f"""
<tr {style}>
  <td>{r['po_no']}</td>
  <td>{r['po_date']}</td>
  <td>{r['last_date']}</td>
  <td>{r['category']}</td>
  <td>{r['code']}</td>
  <td class="wide">{r['name']}</td>
  <td>{r['qty']}</td>
  <td>{r['total']}</td>
  <td>
    <a href="/admin/po/delete/{r['id']}"
       onclick="return confirm('Delete this entry?')"
       style="color:red;text-decoration:none;">❌</a>
  </td>
</tr>
"""
        firm_html += "</table><br></div>"

    html = f"""
<!DOCTYPE html>
<html>
<head>
<title>Purchase Order</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/style.css">

<style>
.po-form {{
  display:grid;
  grid-template-columns: 1.2fr 1.3fr 1.3fr 1.6fr;
  gap:6px;
  margin-bottom:12px;
}}
.po-form input {{ padding:6px;font-size:13px; }}

.po-table {{
  width:100%;
  border-collapse:collapse;
  table-layout:fixed;
  font-size:13px;
}}
.po-table th, .po-table td {{
  border:1px solid #ccc;
  padding:5px;
  text-align:center;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}}
.po-table .wide {{ width:32%;text-align:left; }}

.firm-head {{
  position: relative;
  display:flex;
  justify-content:space-between;
  align-items:center;
  padding:4px 0;
}}
.firm-name {{ font-weight:bold;color:#003d80; }}

.print-btn {{
  background: transparent;
  color: #003d80;
  border: none;
  padding: 2px 4px;
  font-size: 14px;
  cursor: pointer;
}}
.print-btn:hover {{ color: #0055aa; }}

.top-print .print-btn {{
  position: fixed;
  top: 15px;
  right: 10px;
  z-index: 999;
}}
.firm-head .print-btn {{
  position: absolute;
  top: 0;
  right: 0;
}}
</style>
</head>
<body>

<div style="padding:15px;">
<h2>📦 Purchase Order</h2>

<form method="post">
<div class="po-form">
  <input name="po_no" placeholder="PO No" required>
  <input type="date" name="po_date" required>
  <input type="date" name="last_date" required>
  <input name="firm" placeholder="Firm" required>
</div>

<table class="po-table">
<tr>
  <th>Cat</th><th>Code</th><th class="wide">Item Name</th>
  <th>Qty</th><th>Total</th>
</tr>
<tbody id="items">
<tr>
  <td><input name="category[]" placeholder="Cat" required></td>
  <td><input name="code[]" placeholder="Code" required></td>
  <td><input name="name[]" placeholder="Item Name" required></td>
  <td><input name="qty[]" placeholder="Qty" required></td>
  <td><input name="total[]" placeholder="Total (including GST)" required></td>
</tr>
</tbody>
</table>

<button type="button" onclick="addRow()">➕ Add Item</button><br><br>
<button type="submit">Save Purchase Order</button>

<p>{msg}</p>
</form>

<hr>

<div class="top-print">
  <button class="print-btn" onclick="printAll()" title="Print All">🖨️</button>
</div>

<h3>Firm Wise Purchase Orders</h3>

<div id="all-sections">
{firm_html}
</div>

<br>
<a href="/admin" class="login-link">⬅ Back to Admin</a>
</div>

<script>
function addRow(){{
  let r = document.querySelector("#items tr").cloneNode(true);
  r.querySelectorAll("input").forEach(i=>i.value="");
  document.getElementById("items").appendChild(r);
}}

function headerBlock(title, info){{
  var now = new Date().toLocaleString();
  return `
    <div style="text-align:center;margin-bottom:8px;">
      <h2 style="margin:0;">RAJASTHAN STATE ROAD TRANSPORT CORPORATION</h2>
      <div style="font-size:14px;"><b>${{title}}</b></div>
      <div style="font-size:12px;">${{info}}</div>
      <div style="font-size:11px;">Printed on: ${{now}}</div>
      <hr>
    </div>
  `;
}}

function footerBlock(){{
  return `
    <br><br>
    <div style="width:100%;text-align:right;margin-top:40px;">
      ___________________________<br>
      <b>Signature of Incharge</b>
    </div>
  `;
}}

function printSection(id) {{
    var content = document.getElementById(id).innerHTML;
    var w = window.open('', '', 'height=600,width=900');
    w.document.write('<html><head><title>Print</title>');
    w.document.write('<style>' +
        'table{{width:100%;border-collapse:collapse;font-size:11px;table-layout:fixed;}}' +
        'th,td{{border:1px solid #000;padding:3px;text-align:center;white-space:nowrap;}}' +
        'td.wide{{white-space:normal;text-align:left;}}' +
        '</style>');
    w.document.write('</head><body>');

    var header = headerBlock(
        "PURCHASE ORDER (PO)",
        "Depot/Admin: {session.get('user')}"
    );

    w.document.write(header + content + footerBlock());

    w.document.write('</body></html>');
    w.document.close();
    w.print();
}}

function printAll() {{
    var content = document.getElementById('all-sections').innerHTML;
    var w = window.open('', '', 'height=600,width=900');
    w.document.write('<html><head><title>Print All</title>');
    w.document.write('<style>' +
        'table{{width:100%;border-collapse:collapse;font-size:11px;table-layout:fixed;}}' +
        'th,td{{border:1px solid #000;padding:3px;text-align:center;white-space:nowrap;}}' +
        'td.wide{{white-space:normal;text-align:left;}}' +
        '</style>');
    w.document.write('</head><body>');

    var header = headerBlock(
        "PURCHASE ORDER (ALL)",
        "Depot/Admin: {session.get('user')}"
    );

    w.document.write(header + content + footerBlock());

    w.document.write('</body></html>');
    w.document.close();
    w.print();
}}
</script>


<script src="/static/item_autofill.js"></script>

</body>
</html>
"""
    return make_response(html)
@app.route("/admin/po/delete/<int:id>")
def delete_po(id):
    if session.get("user") != "admin":
        return redirect("/login")

    con = db()
    con.execute("DELETE FROM purchase_orders WHERE id=?", (id,))
    con.commit()
    con.close()

    return redirect("/admin/po")






from datetime import date

@app.route("/admin/delivery", methods=["GET", "POST"])
def delivery_schedule():
    if session.get("user") != "admin":
        return redirect("/login")

    msg = ""
    con = db()
    cur = con.cursor()

    # ---------- PO list ----------
    pos = cur.execute("SELECT * FROM purchase_orders ORDER BY firm").fetchall()

    # ---------- Save schedule (ITEM-WISE) ----------
    if request.method == "POST":
        po_id = request.form.get("po_id")
        from_d = request.form.get("from_date")
        to_d = request.form.get("to_date")
        qty_raw = request.form.get("qty", "").strip()

        if not qty_raw:
            msg = "❌ Quantity required"
        else:
            try:
                qty = float(qty_raw)
            except:
                qty = None
                msg = "❌ Invalid quantity"

        po = cur.execute(
            "SELECT * FROM purchase_orders WHERE id=?",
            (po_id,)
        ).fetchone()

        if po and qty is not None:
            po_qty = float(po["qty"])

            row = cur.execute(
                "SELECT IFNULL(SUM(qty),0) s FROM delivery_schedule WHERE po_no=? AND code=?",
                (po["po_no"], po["code"])
            ).fetchone()
            remaining = po_qty - float(row["s"])

            if from_d < po["po_date"] or to_d > po["last_date"]:
                msg = f"❌ Date must be between {po['po_date']} and {po['last_date']}"
            elif from_d > to_d:
                msg = "❌ From-date cannot be after To-date"
            elif qty > remaining:
                msg = f"❌ Only {remaining} qty remaining"
            else:
                cur.execute("""
                    INSERT INTO delivery_schedule
                    (firm, po_no, code, name, from_date, to_date, qty)
                    VALUES (?,?,?,?,?,?,?)
                """, (
                    po["firm"], po["po_no"], po["code"], po["name"],
                    from_d, to_d, qty
                ))
                con.commit()
                msg = "✅ Delivery schedule saved"

    # ---------- Delivered tick ----------
    if request.args.get("tick"):
        did = request.args.get("tick")
        cur.execute("UPDATE delivery_schedule SET delivered=1 WHERE id=?", (did,))
        con.commit()
        return redirect("/admin/delivery")

    # ---------- Read schedules ----------
    rows = cur.execute("SELECT * FROM delivery_schedule ORDER BY firm").fetchall()
    con.close()

    today = date.today().isoformat()

    # ---------- Firm-wise grouping ----------
    firms = {}
    for r in rows:
        firms.setdefault(r["firm"], []).append(r)

    firm_html = ""
    for firm, items in firms.items():
        fid = firm.replace(" ", "_")

        firm_html += f"""
<div id="{fid}">
<div class="firm-head">
  <span class="firm-name">{firm}</span>
  <button class="print-btn" onclick="printSection('{fid}')">🖨️</button>
</div>

<table class="po-table">
<tr>
<th>PO</th><th>Code</th><th class="wide">Item</th>
<th>From</th><th>To</th><th>Qty</th>
<th>✔</th><th>Status</th><th>❌</th>
</tr>
"""
        for r in items:
            penalty = ""
            if not r["delivered"] and r["to_date"] < today:
                penalty = "<span style='color:red;font-weight:bold;'>Penalty</span>"

            firm_html += f"""
<tr>
<td>{r['po_no']}</td>
<td>{r['code']}</td>
<td class="wide">{r['name']}</td>
<td>{r['from_date']}</td>
<td>{r['to_date']}</td>
<td>{r['qty']}</td>
<td>
  {"✔️" if r["delivered"] else f"<a href='/admin/delivery?tick={r['id']}'>☐</a>"}
</td>
<td>{penalty}</td>
<td>
  <a href="/admin/delivery/delete/{r['id']}"
     onclick="return confirm('Delete this schedule?')"
     style="color:red;">❌</a>
</td>
</tr>
"""
        firm_html += "</table><br></div>"

    po_opts = ""
    for p in pos:
        po_opts += f"<option value='{p['id']}'>{p['firm']} | {p['po_no']} | {p['name']} (Qty {p['qty']})</option>"

    html = f"""
<!DOCTYPE html>
<html>
<head>
<title>Delivery Schedule</title>
<link rel="stylesheet" href="/static/style.css">
<style>
.po-form {{
  display:grid;
  grid-template-columns: 3fr 1.3fr 1.3fr 1fr;
  gap:8px;
}}
.po-form select,.po-form input {{ padding:6px;font-size:13px; }}
.po-form button {{
  grid-column: span 4;
  padding:8px;
  background:#003d80;color:white;
  border:none;border-radius:5px;
}}

.po-table {{
  width:100%;
  border-collapse:collapse;
  table-layout:fixed;
  font-size:13px;
}}
.po-table th,.po-table td {{
  border:1px solid #ccc;
  padding:6px;
  text-align:center;
  white-space:nowrap;
}}
.po-table .wide {{
  width:40%;
  text-align:left;
}}

.firm-head {{
  display:flex;
  justify-content:space-between;
  align-items:center;
  padding:4px 0;
}}
.firm-name {{ font-weight:bold;color:#003d80; }}

.print-btn {{
  background:transparent;
  color:#003d80;
  border:none;
  font-size:14px;
  cursor:pointer;
}}

.top-print .print-btn {{
  position: fixed;
  top: 15px;
  right: 10px;
  z-index: 999;
}}
</style>
</head>
<body>

<div style="padding:15px;">
<h2>🚚 Delivery Schedule</h2>

<form method="post" class="po-form">
  <select name="po_id" required>
    <option value="">-- Select PO --</option>
    {po_opts}
  </select>
  <input type="date" name="from_date" required>
  <input type="date" name="to_date" required>
  <input name="qty" placeholder="Qty" required>
  <button type="submit">Save Schedule</button>
</form>

<p>{msg}</p>
<hr>

<div class="top-print">
  <button class="print-btn" onclick="printAll()">🖨️</button>
</div>

<h3>Firm Wise Delivery Schedule</h3>
<div id="all-sections">
{firm_html}
</div>

<br>
<a href="/admin">⬅ Back</a>
</div>

<script>
function printSection(id) {{
 var c=document.getElementById(id).innerHTML;
 var w=window.open('','','width=900,height=600');
 w.document.write('<html><head><title>Print</title>');
 w.document.write('<style>table{{width:100%;border-collapse:collapse;font-size:11px}} th,td{{border:1px solid #000;padding:4px;text-align:center}} .wide{{white-space:normal;text-align:left}}</style>');
 w.document.write('</head><body>'+c+'</body></html>');
 w.document.close(); w.print();
}}
function printAll() {{
 var c=document.getElementById('all-sections').innerHTML;
 var w=window.open('','','width=900,height=600');
 w.document.write('<html><head><title>Print All</title>');
 w.document.write('<style>table{{width:100%;border-collapse:collapse;font-size:11px}} th,td{{border:1px solid #000;padding:4px;text-align:center}} .wide{{white-space:normal;text-align:left}}</style>');
 w.document.write('</head><body>'+c+'</body></html>');
 w.document.close(); w.print();
}}
</script>
<script src="/static/item_autofill.js"></script>

</body>
</html>
"""
    return make_response(html)


@app.route("/admin/delivery/delete/<int:id>")
def delete_delivery(id):
    if session.get("user") != "admin":
        return redirect("/login")

    con = db()
    con.execute("DELETE FROM delivery_schedule WHERE id=?", (id,))
    con.commit()
    con.close()
    return redirect("/admin/delivery")




@app.route("/admin/grs/new", methods=["GET", "POST"])
def grs_new():
    if session.get("user") != "admin":
        return redirect("/login")

    msg = ""

    if request.method == "POST":
        grs_no = request.form.get("grs_no")
        grs_date = request.form.get("grs_date")
        firm = request.form.get("firm")

        cats = request.form.getlist("category[]")
        codes = request.form.getlist("code[]")
        names = request.form.getlist("name[]")
        qtys = request.form.getlist("qty[]")
        prices = request.form.getlist("price[]")
        totals = request.form.getlist("total[]")

        if grs_no and grs_date and firm and names:
            con = db()
            cur = con.cursor()

            # ----- GRS master -----
            cur.execute(
                "INSERT INTO grs (grs_no, grs_date, firm) VALUES (?,?,?)",
                (grs_no, grs_date, firm)
            )
            gid = cur.lastrowid

            # ----- items -----
            for i in range(len(names)):
                if names[i].strip():
                    cat = cats[i].upper().strip()
                    code = codes[i].strip()
                    name = names[i].strip()
                    qty = float(qtys[i] or 0)
                    price = float(prices[i] or 0)

                    # ✅ safety: server-side calculation
                    total = qty * price

                    cur.execute("""
                        INSERT INTO grs_items
                        (grs_id, category, code, name, qty, price, total)
                        VALUES (?,?,?,?,?,?,?)
                    """, (gid, cat, code, name, qty, price, total))

                    # inventory update
                    row = cur.execute("""
                        SELECT id FROM inventory
                        WHERE category=? AND code=?
                    """, (cat, code)).fetchone()

                    if row:
                        cur.execute(
                            "UPDATE inventory SET qty = qty + ? WHERE id=?",
                            (qty, row["id"])
                        )
                    else:
                        cur.execute(
                            "INSERT INTO inventory (category, code, name, qty) VALUES (?,?,?,?)",
                            (cat, code, name, qty)
                        )

                    # ledger
                    cur.execute("""
                        INSERT INTO stock_ledger
                        (entry_date, category, code, name, qty, source)
                        VALUES (?,?,?,?,?,?)
                    """, (grs_date, cat, code, name, qty, "GRS"))

            con.commit()
            con.close()
            return redirect("/admin/grs/detail")
        else:
            msg = "❌ Please fill all required fields"

    html = """
<!DOCTYPE html>
<html>
<head>
<title>Generate GRS</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/style.css">
<style>
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{border:1px solid #ccc;padding:5px;text-align:center}
input{width:100%;padding:5px;font-size:13px}
.add-btn{padding:6px 10px;margin:6px 0}
.top{display:grid;grid-template-columns:1fr 1fr 2fr;gap:8px}
</style>
</head>
<body>

<div style="padding:15px;">
<h2>📑 Generate New GRS</h2>

<form method="post">
<div class="top">
  <input name="grs_no" placeholder="GRS No" required>
  <input type="date" name="grs_date" required>
  <input name="firm" placeholder="Firm Name" required>
</div><br>

<table>
<tr>
<th>Category</th>
<th>Code</th>
<th>Name</th>
<th>Qty</th>
<th>Price</th>
<th>Total</th>
</tr>

<tbody id="items">
<tr>
<td><input name="category[]"></td>
<td><input name="code[]"></td>
<td><input name="name[]" required></td>
<td><input name="qty[]" class="qty" required></td>
<td><input name="price[]" class="price" required></td>
<td><input name="total[]" class="total" readonly></td>
</tr>
</tbody>
</table>

<button type="button" class="add-btn" onclick="addRow()">➕ Add Item</button><br>
<button type="submit">💾 Save GRS</button>
<a href="/admin/grs/detail">⬅ Back</a>

<p style="color:red;">""" + msg + """</p>
</form>
</div>

<script>
function calculateRowTotal(row){
    let qty = parseFloat(row.querySelector(".qty").value) || 0;
    let price = parseFloat(row.querySelector(".price").value) || 0;
    row.querySelector(".total").value = (qty * price).toFixed(2);
}

document.addEventListener("input", function(e){
    if(e.target.classList.contains("qty") ||
       e.target.classList.contains("price")){
        let row = e.target.closest("tr");
        calculateRowTotal(row);
    }
});

function addRow(){
    let r = document.querySelector("#items tr").cloneNode(true);
    r.querySelectorAll("input").forEach(i => i.value = "");
    document.getElementById("items").appendChild(r);
}
</script>

<script src="/static/item_autofill.js"></script>

</body>
</html>
"""
    return make_response(html)

@app.route("/admin/grs/detail")
def grs_detail():
    if session.get("user") != "admin":
        return redirect("/login")

    con = db()
    cur = con.cursor()

    grs_rows = cur.execute("SELECT * FROM grs ORDER BY id DESC").fetchall()

    sections = ""
    for g in grs_rows:
        items = cur.execute(
            "SELECT * FROM grs_items WHERE grs_id=?",
            (g["id"],)
        ).fetchall()

        gid = f"grs_{g['id']}"

        rows = ""
        for i, it in enumerate(items, 1):
            rows += f"""
<tr>
<td>{i}</td>
<td>{it['category']}</td>
<td>{it['code']}</td>
<td style="text-align:left;">{it['name']}</td>
<td>{it['qty']}</td>
<td>{it['price']}</td>
<td>{it['total']}</td>
</tr>
"""

        sections += f"""
<div id="{gid}" style="margin-bottom:25px;">
<div style="display:flex;justify-content:space-between;align-items:center;">
  <h3>GRS No: {g['grs_no']} | Date: {g['grs_date']} | Firm: {g['firm']}</h3>
  <button onclick="printSection('{gid}')" class="print-btn">🖨️</button>
  <a href="/admin/grs/delete/{g['id']}"
     onclick="return confirm('Delete this GRS?')"
     style="color:red;text-decoration:none;">❌</a>
</div>

<table class="po-table">
<tr>
<th>S.No</th><th>Category</th><th>Code</th>
<th class="wide">Item Name</th><th>Qty</th><th>Price</th><th>Total</th>
</tr>
{rows}
</table>
</div>
<hr>
"""

    con.close()

    html = f"""
<!DOCTYPE html>
<html>
<head>
<title>GRS Detail</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/style.css">
<style>
.po-table {{
  width:100%;border-collapse:collapse;font-size:13px;table-layout:fixed;
}}
.po-table th,.po-table td {{
  border:1px solid #ccc;padding:5px;text-align:center;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}}
.po-table .wide {{ width:35%;text-align:left; }}

.print-btn {{
  background:transparent;color:#003d80;border:none;
  font-size:16px;cursor:pointer;
}}
</style>
</head>
<body>

<div style="padding:15px;">
<h2>📄 GRS Detail</h2>

{sections}

<a href="/admin/grs/new">➕ Generate New GRS</a> |
<a href="/admin">⬅ Back</a>
</div>

<script>
function printSection(id) {{
 var c=document.getElementById(id).innerHTML;
 var w=window.open('','','width=900,height=600');
 w.document.write('<html><head><title>Print</title>');
 w.document.write('<style>'+
 'table{{width:100%;border-collapse:collapse;font-size:11px;}}'+
 'th,td{{border:1px solid #000;padding:4px;text-align:center;}}'+
 '.wide{{white-space:normal;text-align:left;}}'+
 '</style>');
 w.document.write('</head><body>'+c+'</body></html>');
 w.document.close(); w.print();
}}
</script>

</body>
</html>
"""
    return make_response(html)


@app.route("/admin/grs/delete/<int:id>")
def delete_grs(id):
    if session.get("user") != "admin":
        return redirect("/login")

    con = db()
    cur = con.cursor()
    cur.execute("DELETE FROM grs_items WHERE grs_id=?", (id,))
    cur.execute("DELETE FROM grs WHERE id=?", (id,))
    con.commit()
    con.close()

    return redirect("/admin/grs/detail")





   
from datetime import date

@app.route("/admin/opening/<cat>", methods=["GET", "POST"])
def admin_opening_stock(cat):
    if session.get("user") != "admin":
        return redirect("/login")

    msg = ""
    cat_u = cat.upper()

    con = db()
    cur = con.cursor()

    # ===================== SAVE OPENING =====================
    if request.method == "POST":
        entry_date = request.form.get("entry_date")
        code = request.form.get("code", "").strip().upper()
        name = request.form.get("name", "").strip()
        qty_raw = request.form.get("qty", "").strip()

        try:
            qty = float(qty_raw)
        except:
            qty = 0

        # 🔒 Excel master category validation
        df = get_items()
        df["category"] = df["category"].str.strip().str.upper()
        df["code"] = df["code"].str.strip().str.upper()

        valid = df[(df["code"] == code) & (df["category"] == cat_u)]

        if valid.empty:
            msg = "❌ Ye item is category ka nahi hai"

        else:
            # 🔒 one-time opening check
            exists = cur.execute("""
                SELECT id FROM opening_stock
                WHERE category=? AND code=?
            """, (cat_u, code)).fetchone()

            if exists:
                msg = "⚠️ Is item ka opening stock pehle hi set ho chuka hai"

            else:
                # 1️⃣ opening_stock (record)
                cur.execute("""
                    INSERT INTO opening_stock
                    (category, code, name, qty, entry_date)
                    VALUES (?,?,?,?,?)
                """, (cat_u, code, name, qty, entry_date))

                # 2️⃣ inventory (current stock)
                inv = cur.execute("""
                    SELECT qty FROM inventory
                    WHERE category=? AND code=?
                """, (cat_u, code)).fetchone()

                if inv:
                    cur.execute("""
                        UPDATE inventory
                        SET qty = qty + ?
                        WHERE category=? AND code=?
                    """, (qty, cat_u, code))
                else:
                    cur.execute("""
                        INSERT INTO inventory
                        (category, code, name, qty, entry_date)
                        VALUES (?,?,?,?,?)
                    """, (cat_u, code, name, qty, entry_date))

                # 3️⃣ stock ledger (history)
                cur.execute("""
                    INSERT INTO stock_ledger
                    (entry_date, category, code, name, qty, source)
                    VALUES (?,?,?,?,?,?)
                """, (entry_date, cat_u, code, name, qty, "OPENING"))

                con.commit()
                msg = "✅ Admin opening stock saved successfully"

    # ===================== SHOW DATA =====================
    rows = cur.execute("""
        SELECT code, name, qty, entry_date
        FROM opening_stock
        WHERE category=?
        ORDER BY name
    """, (cat_u,)).fetchall()

    con.close()

    trs = ""
    total = 0
    for r in rows:
        q = float(r["qty"] or 0)
        total += q
        trs += f"""
<tr>
  <td>{r['entry_date'] or ''}</td>
  <td>{r['code']}</td>
  <td style="text-align:left;">{r['name']}</td>
  <td>{q}</td>
</tr>
"""

    # ===================== HTML =====================
    return make_response(f"""
<!DOCTYPE html>
<html>
<head>
<title>Admin Opening Stock - {cat_u}</title>
<link rel="stylesheet" href="/static/style.css">
<style>
table {{width:100%;border-collapse:collapse;font-size:14px}}
th,td {{border:1px solid #ccc;padding:6px;text-align:center}}
th {{background:#003d80;color:white}}
.total-row td {{font-weight:bold;background:#f0f0f0}}
</style>
</head>
<body>
<div style="padding:15px;">
<h2>📊 Admin Opening Stock - {cat_u}</h2>

<p style="color:#b00;">
⚠️ You can fill only one time.
</p>

<form method="post"
 style="display:grid;grid-template-columns:1fr 1.5fr 2fr 1fr;gap:8px;max-width:700px;">
  <input type="hidden" id="pageCategory" value="{cat_u}">
  <input type="date" name="entry_date" required>
  <input name="code" placeholder="Item Code" required>
  <input name="name" placeholder="Item Name" required>
  <input name="qty" placeholder="Qty" required>
  <button type="submit" style="grid-column:span 4;">➕ Add Opening Stock</button>
</form>

<p>{msg}</p>

<table>
<tr><th>Date</th><th>Code</th><th>Name</th><th>Qty</th></tr>
{trs}
<tr class="total-row">
<td colspan="3">TOTAL</td><td>{total}</td>
</tr>
</table>

<br>
<a href="/admin">⬅ Back to Admin Panel</a>
</div>
<script src="/static/item_autofill.js"></script>
</body>
</html>
""")



# ================= INVENTORY SECTION =================

# ================= INVENTORY SECTION =================
from datetime import date, timedelta
@app.route("/admin/inv/<cat>")
def view_inventory(cat):
    if session.get("user") != "admin":
        return redirect("/login")

    con = db()
    cur = con.cursor()
    cat_u = cat.upper()
    rows = cur.execute("""
        SELECT code, name, SUM(qty) as qty FROM (

            SELECT code, name, qty
            FROM stock_ledger
            WHERE category=? AND source='OPENING'

            UNION ALL

            SELECT gi.code, gi.name, gi.qty
            FROM grs_items gi
            JOIN grs g ON g.id = gi.grs_id
            WHERE gi.category=?

            UNION ALL

            SELECT ci.code, ci.name, -ci.qty
            FROM challan_items ci
            JOIN challan c ON c.id = ci.challan_id
            WHERE ci.category=? AND c.from_depot='admin'

        )
        GROUP BY code, name
        ORDER BY name
    """, (cat_u, cat_u, cat_u)).fetchall()
    con.close()

    trs = ""
    for r in rows:
        q = float(r["qty"] or 0)
        trs += f"""
<tr>
  <td>
    <a href="/admin/inv/{cat}/{r['code']}">
      {r['code']} - {r['name']}
    </a>
  </td>
  <td>{q}</td>
</tr>
"""

    return make_response(f"""
<!DOCTYPE html>
<html>
<head>
<title>Inventory - {cat.upper()}</title>
<link rel="stylesheet" href="/static/style.css">
<style>
table {{
  width:100%;
  border-collapse:collapse;
  font-size:14px;
}}
th,td {{
  border:1px solid #ccc;
  padding:8px;
  text-align:center;
}}
th {{
  background:#003d80;
  color:white;
}}
tr:nth-child(even) {{ background:#f9f9f9; }}
a {{ color:#003d80; text-decoration:none; font-weight:bold; }}

.print-btn {{
  background:#003d80;
  color:white;
  border:none;
  padding:6px 12px;
  border-radius:5px;
  cursor:pointer;
}}
</style>
</head>
<body>

<div style="padding:15px;">
<h2>📦 Inventory - {cat.upper()}</h2>

<button class="print-btn" onclick="printPage()">🖨️ Print</button>
<br><br>

<table id="invTable">
<tr><th>Item</th><th>Qty</th></tr>
{trs}
</table>

<br>
<a href="/admin">⬅ Back</a>
</div>

<script>
function printPage(){{
  var c = document.getElementById("invTable").outerHTML;
  var w = window.open('', '', 'width=900,height=600');
  w.document.write('<html><head><title>Print</title>');
  w.document.write('<style>table{{width:100%;border-collapse:collapse;font-size:12px}} th,td{{border:1px solid #000;padding:5px;text-align:center}}</style>');
  w.document.write('</head><body>');
  w.document.write(c);
  w.document.write('</body></html>');
  w.document.close();
  w.print();
}}
</script>
<script src="/static/item_autofill.js"></script>

</body>
</html>
""")



@app.route("/admin/inv/<cat>/<code>")
def inventory_item_detail(cat, code):
    if session.get("user") != "admin":
        return redirect("/login")

    con = db()
    cur = con.cursor()
    cat_u = cat.upper()

    # ---- item name ----
    row = cur.execute("""
        SELECT name FROM inventory
        WHERE category=? AND code=?
        LIMIT 1
    """, (cat_u, code)).fetchone()
    name = row["name"] if row else ""

    # ---- ALL movements with No. column ----
    rows = cur.execute("""
        SELECT entry_date as dt, 'OPENING' as typ, '-' as no, '-' as party, qty as q
        FROM stock_ledger
        WHERE category=? AND code=? AND source='OPENING'

        UNION ALL

        SELECT g.grs_date as dt, 'GRS' as typ, g.grs_no as no, g.firm as party, gi.qty as q
        FROM grs_items gi
        JOIN grs g ON g.id = gi.grs_id
        WHERE gi.category=? AND gi.code=?

        UNION ALL

        SELECT c.challan_date as dt, 'CHALLAN' as typ, c.challan_no as no, c.depot as party, -ci.qty as q
        FROM challan_items ci
        JOIN challan c ON c.id = ci.challan_id
        WHERE c.from_depot='admin'
        AND ci.category=? AND ci.code=?


        ORDER BY dt
    """, (cat_u, code, cat_u, code, cat_u, code)).fetchall()

    trs = ""
    sn = 1
    total = 0

    for r in rows:
        q = float(r["q"] or 0)
        total += q
        trs += f"""
<tr>
  <td>{sn}</td>
  <td>{r['typ']}</td>
  <td>{r['no']}</td>
  <td>{r['dt']}</td>
  <td>{r['party']}</td>
  <td>{q}</td>
</tr>
"""
        sn += 1

    con.close()

    return make_response(f"""
<!DOCTYPE html>
<html>
<head>
<title>Central Store Item Ledger</title>
<link rel="stylesheet" href="/static/style.css">
<style>
table{{width:100%;border-collapse:collapse;font-size:14px}}
th,td{{border:1px solid #999;padding:6px;text-align:center}}
th{{background:#003d80;color:white}}
.total-row td{{font-weight:bold;background:#f0f0f0}}
</style>
</head>
<body>
<div style="padding:15px;">
<h2>🏬 Central Store Item Ledger</h2>
<h3>{code} - {name} ({cat_u})</h3>

<table>
<tr>
  <th>#</th>
  <th>Type</th>
  <th>No.</th>
  <th>Date</th>
  <th>Firm / Depot</th>
  <th>Qty</th>
</tr>

{trs}

<tr class="total-row">
  <td colspan="5">TOTAL</td>
  <td>{total}</td>
</tr>
</table>

<br>
<button onclick="printItem()">🖨️ Print</button>
<br><br>
<a href="/admin/inv/{cat}">⬅ Back to Inventory</a>
</div>

<script>
function printItem(){{
 var c=document.body.innerHTML;
 var w=window.open('','','width=900,height=600');
 w.document.write('<html><head><title>Print</title>');
 w.document.write('<style>table{{width:100%;border-collapse:collapse;font-size:12px}} th,td{{border:1px solid #000;padding:4px;text-align:center}}</style>');
 w.document.write('</head><body>'+c+'</body></html>');
 w.document.close(); w.print();
}}
</script>
</body>
</html>
""")



# ------------------ GENERATE CHALLAN (ADMIN) ------------------
@app.route("/admin/challan", methods=["GET", "POST"])
def challan_new():
    if session.get("user") != "admin":
        return redirect("/login")

    msg = ""

    if request.method == "POST":
        challan_no = request.form.get("challan_no")
        challan_date = request.form.get("challan_date")
        depot = request.form.get("depot")

        cats = request.form.getlist("category[]")
        codes = request.form.getlist("code[]")
        names = request.form.getlist("name[]")
        qtys = request.form.getlist("qty[]")
        prices = request.form.getlist("price[]")
        totals = request.form.getlist("total[]")

        if challan_no and challan_date and depot:
            con = db()
            cur = con.cursor()

            try:
                # ---- save challan master ----
                cur.execute("""
                    INSERT INTO challan (challan_no, challan_date, depot, from_depot)
                    VALUES (?,?,?,?)
                """, (challan_no, challan_date, depot, "admin"))
                cid = cur.lastrowid

                for i in range(len(names)):
                    if names[i].strip():
                        cat = cats[i].upper().strip()
                        code = codes[i].strip()
                        name = names[i].strip()
                        qty = float(qtys[i] or 0)
                        price = float(prices[i] or 0)

                        # ✅ server-side safe calculation
                        total = qty * price

                        # ---- live available stock ----
                        row = cur.execute("""
                            SELECT SUM(qty) AS avail FROM (
                                SELECT qty FROM opening_stock
                                WHERE category=? AND code=?

                                UNION ALL
                                SELECT gi.qty
                                FROM grs_items gi
                                JOIN grs g ON g.id = gi.grs_id
                                WHERE gi.category=? AND gi.code=?

                                UNION ALL
                                SELECT -ci.qty
                                FROM challan_items ci
                                JOIN challan c ON c.id = ci.challan_id
                                WHERE ci.category=? AND ci.code=?
                            )
                        """, (
                            cat, code,
                            cat, code,
                            cat, code
                        )).fetchone()

                        avail = float(row["avail"] or 0)

                        if avail < qty:
                            con.rollback()
                            msg = f"❌ Stock not enough for {code}. Available: {avail}"
                            raise Exception(msg)

                        # ---- save challan item ----
                        cur.execute("""
                            INSERT INTO challan_items
                            (challan_id, category, code, name, qty, price, total)
                            VALUES (?,?,?,?,?,?,?)
                        """, (cid, cat, code, name, qty, price, total))

                con.commit()
                con.close()
                return redirect("/admin/challan/detail")

            except Exception as e:
                con.rollback()
                con.close()
                msg = str(e)

    depot_opts = "".join([f"<option>{d}</option>" for d in DEPOTS])

    html = """
<!DOCTYPE html>
<html>
<head>
<title>Generate Challan</title>
<link rel="stylesheet" href="/static/style.css">
<style>
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{border:1px solid #ccc;padding:5px;text-align:center}
input,select{width:100%;padding:5px}
.top{display:grid;grid-template-columns:1fr 1fr 2fr;gap:8px}
.add-btn{margin:6px 0}
</style>
</head>
<body>

<div style="padding:15px;">
<h2>🚚 Generate Depot Challan</h2>

<form method="post">
<div class="top">
  <input name="challan_no" placeholder="Challan No" required>
  <input type="date" name="challan_date" required>
  <select name="depot" required>
    <option value="">-- Select Depot --</option>
    """ + depot_opts + """
  </select>
</div><br>

<table>
<tr>
<th>Cat</th>
<th>Code</th>
<th>Name</th>
<th>Qty</th>
<th>Price</th>
<th>Total</th>
</tr>

<tbody id="items">
<tr>
<td><input name="category[]"></td>
<td><input name="code[]"></td>
<td><input name="name[]"></td>
<td><input name="qty[]" class="qty" required></td>
<td><input name="price[]" class="price" required></td>
<td><input name="total[]" class="total" readonly></td>
</tr>
</tbody>
</table>

<button type="button" class="add-btn" onclick="addRow()">➕ Add Item</button><br>
<button type="submit">💾 Save Challan</button>
<a href="/admin">⬅ Back</a>

<p style="color:red;">""" + msg + """</p>
</form>
</div>

<script>
function calculateRowTotal(row){
    let qty = parseFloat(row.querySelector(".qty").value) || 0;
    let price = parseFloat(row.querySelector(".price").value) || 0;
    row.querySelector(".total").value = (qty * price).toFixed(2);
}

document.addEventListener("input", function(e){
    if(e.target.classList.contains("qty") ||
       e.target.classList.contains("price")){
        let row = e.target.closest("tr");
        calculateRowTotal(row);
    }
});

function addRow(){
    let r = document.querySelector("#items tr").cloneNode(true);
    r.querySelectorAll("input").forEach(i => i.value = "");
    document.getElementById("items").appendChild(r);
}
</script>

<script src="/static/item_autofill.js"></script>

</body>
</html>
"""
    return make_response(html)



@app.route("/admin/challan/detail")
def challan_detail():
    if session.get("user") != "admin":
        return redirect("/login")

    con = db()
    cur = con.cursor()

    rows = cur.execute("""
        SELECT * FROM challan
        WHERE from_depot=?
        ORDER BY id DESC
    """, ("admin",)).fetchall()

    sections = ""

    for c in rows:
        # ---------- SAFE STATUS READ ----------
        status = "draft"
        if "status" in c.keys():
            status = c["status"]

        # ---------- SEND BUTTON ----------
        send_btn = ""
        if status == "draft":
            send_btn = f"""
            <a href="/admin/challan/send/{c['id']}"
               style="font-size:18px;color:green;text-decoration:none;"
               onclick="return confirm('Send this challan to depot?')">📤</a>
            """

        # ---------- ITEMS ----------
        items = cur.execute("""
            SELECT * FROM challan_items WHERE challan_id=?
        """, (c["id"],)).fetchall()

        cid = f"ch_{c['id']}"

        trs = ""
        for i, it in enumerate(items, 1):
            trs += f"""
<tr>
<td>{i}</td>
<td>{it['category']}</td>
<td>{it['code']}</td>
<td class="wide">{it['name']}</td>
<td>{it['qty']}</td>
<td>{it['price']}</td>
<td>{it['total']}</td>
</tr>
"""

        sections += f"""
<div class="card" id="{cid}">
  <div class="head">
    <h3>
      Challan No: {c['challan_no']} |
      Date: {c['challan_date']} |
      Depot: {c['depot']} |
      Status: <b>{status}</b>
    </h3>
    <div>
      <button class="print-btn" onclick="printSection('{cid}')">🖨️</button>

      {send_btn}

      <a href="/admin/challan/delete/{c['id']}"
         onclick="return confirm('Delete this Challan?')"
         class="del-btn">❌</a>
    </div>
  </div>

  <table class="po-table">
    <tr>
      <th>#</th><th>Cat</th><th>Code</th>
      <th class="wide">Item Name</th>
      <th>Qty</th><th>Price</th><th>Total</th>
    </tr>
    {trs}
  </table>
</div>
"""

    con.close()

    return make_response(f"""
<!DOCTYPE html>
<html>
<head>
<title>Challan Detail</title>
<link rel="stylesheet" href="/static/style.css">
<style>
body {{ background:#f5f6fa; }}
.container {{ padding:20px; }}
.card {{
  background:white;
  padding:12px;
  border-radius:8px;
  margin-bottom:20px;
  box-shadow:0 0 8px #bbb;
}}
.head {{
  display:flex;
  justify-content:space-between;
  align-items:center;
  margin-bottom:10px;
}}
.head h3 {{ margin:0; color:#003d80; }}
.po-table {{
  width:100%;
  border-collapse:collapse;
  font-size:13px;
}}
.po-table th, .po-table td {{
  border:1px solid #ccc;
  padding:6px;
  text-align:center;
}}
.po-table th {{ background:#003d80; color:white; }}
.po-table .wide {{ text-align:left; width:35%; }}
.print-btn {{
  background:transparent;
  border:none;
  font-size:18px;
  cursor:pointer;
  color:#003d80;
}}
.del-btn {{
  color:red;
  font-size:18px;
  text-decoration:none;
  margin-left:10px;
}}
</style>
</head>
<body>

<div class="container">
<h2>📄 Depot Challan Detail</h2>

<a href="/admin/challan">➕ New Challan</a> |
<a href="/admin">⬅ Back</a>
<br><br>

{sections}
</div>

<script>
function printSection(id){{
 var c=document.getElementById(id).innerHTML;
 var w=window.open('','','width=900,height=600');
 w.document.write('<html><head><title>Print</title>');
 w.document.write('<style>'+
 'table{{width:100%;border-collapse:collapse;font-size:11px}}'+
 'th,td{{border:1px solid #000;padding:4px;text-align:center}}'+
 '.wide{{text-align:left;}}'+
 '</style>');
 w.document.write('</head><body>'+c+'</body></html>');
 w.document.close(); w.print();
}}
</script>

</body>
</html>
""")


@app.route("/admin/challan/delete/<int:id>")
def delete_challan(id):
    if session.get("user") != "admin":
        return redirect("/login")

    con = db()
    cur = con.cursor()

    # stock wapas add karna ho to yahan logic daal sakte ho

    cur.execute("DELETE FROM challan_items WHERE challan_id=?", (id,))
    cur.execute("DELETE FROM challan WHERE id=?", (id,))
    con.commit()
    con.close()

    return redirect("/admin/challan/detail")

@app.route("/admin/challan/send/<int:id>")
def admin_challan_send(id):
    if session.get("user") != "admin":
        return redirect("/login")

    con = db()
    cur = con.cursor()

    # 🔁 status = sent
    cur.execute("""
        UPDATE challan
        SET status='sent'
        WHERE id=?
    """, (id,))

    con.commit()
    con.close()

    return redirect("/admin/challan/detail")



from datetime import date

@app.route("/user/opening/<cat>", methods=["GET", "POST"])
def user_opening_stock(cat):
    user = session.get("user")
    if not user:
        return redirect("/login")

    msg = ""
    cat_u = cat.upper()
    con = db()
    cur = con.cursor()

    if request.method == "POST":
        entry_date = request.form.get("entry_date")
        code = request.form.get("code","").strip()
        name = request.form.get("name","").strip()
        qty_raw = request.form.get("qty","").strip()

        try:
            qty = float(qty_raw)
        except:
            qty = 0

        if code and name and entry_date:
            exists = cur.execute("""
                SELECT id FROM user_opening_stock
                WHERE user=? AND category=? AND code=?
            """, (user, cat_u, code)).fetchone()

            if exists:
                msg = "⚠️ Is item ka opening stock aap pehle hi bhar chuke ho"
            else:
                cur.execute("""
                    INSERT INTO user_opening_stock
                    (user, category, code, name, qty, entry_date)
                    VALUES (?,?,?,?,?,?)
                """, (user, cat_u, code, name, qty, entry_date))
                con.commit()
                msg = "✅ Opening stock saved"

    rows = cur.execute("""
        SELECT code, name, qty, entry_date
        FROM user_opening_stock
        WHERE user=? AND category=?
        ORDER BY name
    """, (user, cat_u)).fetchall()
    con.close()

    trs = ""
    total = 0
    for r in rows:
        q = float(r["qty"] or 0)
        total += q
        trs += f"""
<tr>
<td>{r['entry_date'] or ''}</td>
<td>{r['code']}</td>
<td style="text-align:left;">{r['name']}</td>
<td>{q}</td>
</tr>
"""

    return make_response(f"""
<!DOCTYPE html>
<html>
<head>
<title>User Opening Stock - {cat_u}</title>
<link rel="stylesheet" href="/static/style.css">
<style>
table {{width:100%;border-collapse:collapse;font-size:14px}}
th,td {{border:1px solid #ccc;padding:6px;text-align:center}}
th {{background:#003d80;color:white}}
.total-row td {{font-weight:bold;background:#f0f0f0}}
</style>
</head>
<body>
<div style="padding:15px;">
<h2>📊 Opening Stock - {cat_u} (Depot: {user})</h2>
<p style="color:#b00;">
⚠️ You can fill only one time.
</p>

<form method="post"
 style="display:grid;grid-template-columns:1fr 1.5fr 2fr 1fr;gap:8px;max-width:700px;">
  <input type="hidden" id="pageCategory" value="{cat_u}">
  <input type="date" name="entry_date" required>
  <input name="code" placeholder="Item Code" required>
  <input name="name" placeholder="Item Name" required>
  <input name="qty" placeholder="Qty" required>
  <button type="submit" style="grid-column:span 4;">➕ Add Opening Stock</button>
</form>

<p>{msg}</p>

<table>
<tr><th>Date</th><th>Code</th><th>Name</th><th>Qty</th></tr>
{trs}
<tr class="total-row">
<td colspan="3">TOTAL</td><td>{total}</td>
</tr>
</table>

<br>
<a href="/user">⬅ Back to User Panel</a>
</div>
<script src="/static/item_autofill.js"></script>
</body>
</html>
""")




@app.route("/user/grs/new", methods=["GET", "POST"])
def user_grs_new():
    user = session.get("user")
    if not user:
        return redirect("/login")

    msg = ""

    if request.method == "POST":
        grs_no = request.form.get("grs_no")
        grs_date = request.form.get("grs_date")
        firm = request.form.get("firm")

        cats = request.form.getlist("category[]")
        codes = request.form.getlist("code[]")
        names = request.form.getlist("name[]")
        qtys = request.form.getlist("qty[]")
        prices = request.form.getlist("price[]")
        totals = request.form.getlist("total[]")

        if grs_no and grs_date and firm and names:
            con = db()
            cur = con.cursor()

            # ---- save user GRS master ----
            cur.execute("""
                INSERT INTO user_grs (user, grs_no, grs_date, firm)
                VALUES (?,?,?,?)
            """, (user, grs_no, grs_date, firm))
            gid = cur.lastrowid

            for i in range(len(names)):
                if names[i].strip():
                    cat = cats[i].upper().strip()
                    code = codes[i].strip()
                    name = names[i].strip()
                    qty = float(qtys[i] or 0)
                    price = float(prices[i] or 0)

                    # ✅ server-side calculation (safe)
                    total = qty * price

                    # save items
                    cur.execute("""
                        INSERT INTO user_grs_items
                        (grs_id, category, code, name, qty, price, total)
                        VALUES (?,?,?,?,?,?,?)
                    """, (gid, cat, code, name, qty, price, total))

                    # update user inventory
                    row = cur.execute("""
                        SELECT id FROM user_inventory
                        WHERE user=? AND category=? AND code=?
                    """, (user, cat, code)).fetchone()

                    if row:
                        cur.execute("""
                            UPDATE user_inventory
                            SET qty = qty + ?
                            WHERE id=?
                        """, (qty, row["id"]))
                    else:
                        cur.execute("""
                            INSERT INTO user_inventory
                            (user, category, code, name, qty)
                            VALUES (?,?,?,?,?)
                        """, (user, cat, code, name, qty))

            con.commit()
            con.close()
            return redirect("/user/grs/detail")
        else:
            msg = "❌ Fill all fields"

    html = """
<!DOCTYPE html>
<html>
<head>
<title>User GRS</title>
<link rel="stylesheet" href="/static/style.css">
<style>
table{width:100%;border-collapse:collapse}
th,td{border:1px solid #ccc;padding:5px;text-align:center}
.top{display:grid;grid-template-columns:1fr 1fr 2fr;gap:8px}
</style>
</head>
<body>

<div style="padding:15px;">
<h2>📑 GRS (Depot: """ + user + """)</h2>

<form method="post">
<div class="top">
  <input name="grs_no" placeholder="GRS No" required>
  <input type="date" name="grs_date" required>
  <input name="firm" placeholder="Firm" required>
</div><br>

<table>
<tr>
<th>Cat</th>
<th>Code</th>
<th>Name</th>
<th>Qty</th>
<th>Price</th>
<th>Total</th>
</tr>

<tbody id="items">
<tr>
<td><input name="category[]"></td>
<td><input name="code[]"></td>
<td><input name="name[]" required></td>
<td><input name="qty[]" class="qty" required></td>
<td><input name="price[]" class="price" required></td>
<td><input name="total[]" class="total" readonly></td>
</tr>
</tbody>
</table>

<button type="button" onclick="addRow()">➕ Add</button><br><br>
<button type="submit">💾 Save GRS</button>
<a href="/user">⬅ Back</a>

<p style="color:red;">""" + msg + """</p>
</form>
</div>

<script>
function calculateRowTotal(row){
    let qty = parseFloat(row.querySelector(".qty").value) || 0;
    let price = parseFloat(row.querySelector(".price").value) || 0;
    row.querySelector(".total").value = (qty * price).toFixed(2);
}

document.addEventListener("input", function(e){
    if(e.target.classList.contains("qty") ||
       e.target.classList.contains("price")){
        let row = e.target.closest("tr");
        calculateRowTotal(row);
    }
});

function addRow(){
    let r = document.querySelector("#items tr").cloneNode(true);
    r.querySelectorAll("input").forEach(i => i.value = "");
    document.getElementById("items").appendChild(r);
}
</script>

<script src="/static/item_autofill.js"></script>

</body>
</html>
"""
    return make_response(html)


@app.route("/user/grs/detail")
def user_grs_detail():
    user = session.get("user")
    if not user:
        return redirect("/login")

    con = db()
    cur = con.cursor()

    rows = cur.execute("""
        SELECT * FROM user_grs
        WHERE user=?
        ORDER BY id DESC
    """, (user,)).fetchall()

    sections = ""
    for g in rows:
        items = cur.execute("""
            SELECT * FROM user_grs_items WHERE grs_id=?
        """, (g["id"],)).fetchall()

        gid = f"ugrs_{g['id']}"

        trs = ""
        for i, it in enumerate(items, 1):
            trs += f"""
<tr>
  <td>{i}</td>
  <td>{it['category']}</td>
  <td>{it['code']}</td>
  <td class="wide">{it['name']}</td>
  <td>{it['qty']}</td>
  <td>{it['price']}</td>
  <td>{it['total']}</td>
</tr>
"""

        sections += f"""
<div id="{gid}" class="grs-card">
  <div class="grs-head">
    <h3>GRS No: {g['grs_no']} | Date: {g['grs_date']} | Firm: {g['firm']}</h3>
    <div class="action-btns">
      <button onclick="printSection('{gid}')" class="print-btn">🖨️ Print</button>
      <a href="/user/grs/delete/{g['id']}"
         onclick="return confirm('Delete this GRS?')"
         class="del-btn">❌ Delete</a>
    </div>
  </div>

  <table class="po-table">
    <tr>
      <th>#</th><th>Category</th><th>Code</th>
      <th class="wide">Item Name</th>
      <th>Qty</th><th>Price</th><th>Total</th>
    </tr>
    {trs}
  </table>
</div>
"""

    con.close()

    html = f"""
<!DOCTYPE html>
<html>
<head>
<title>User GRS Detail</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/style.css">
<style>
body {{
    background:#f4f6f9;
    font-family: Arial, sans-serif;
}}

.container {{
    padding:20px;
}}

.grs-card {{
    background:white;
    border-radius:8px;
    box-shadow:0 2px 6px rgba(0,0,0,0.2);
    padding:15px;
    margin-bottom:25px;
}}

.del-btn {{
  color:red;
  text-decoration:none;
  font-weight:bold;
  padding:5px 8px;
  border:1px solid red;
  border-radius:4px;
}}

.del-btn:hover {{
  background:#ffe6e6;
}}

.grs-head {{
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:10px;
}}

.grs-head h3 {{
    margin:0;
    color:#003d80;
}}

.action-btns {{
    display:flex;
    gap:10px;
}}

.print-btn {{
    background:#003d80;
    color:white;
    border:none;
    padding:5px 10px;
    border-radius:4px;
    cursor:pointer;
    font-size:14px;
}}

.print-btn:hover {{
    background:#0055aa;
}}

.po-table {{
    width:100%;
    border-collapse:collapse;
    font-size:13px;
    table-layout:fixed;
}}

.po-table th {{
    background:#003d80;
    color:white;
}}

.po-table th, .po-table td {{
    border:1px solid #ccc;
    padding:6px;
    text-align:center;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
}}

.po-table .wide {{
    width:35%;
    text-align:left;
    white-space:normal;
}}

.top-links {{
    margin-bottom:15px;
}}

.top-links a {{
    margin-right:15px;
    text-decoration:none;
    color:#003d80;
    font-weight:bold;
}}
</style>
</head>
<body>

<div class="container">
<h2>📄 My GRS Detail</h2>

<div class="top-links">
  <a href="/user">⬅ Back</a>
</div>

{sections}

</div>

<script>
function printSection(id) {{
 var c=document.getElementById(id).innerHTML;
 var w=window.open('','','width=900,height=600');
 w.document.write('<html><head><title>Print</title>');
 w.document.write('<style>'+
 'table{{width:100%;border-collapse:collapse;font-size:11px;}}'+
 'th,td{{border:1px solid #000;padding:4px;text-align:center;}}'+
 '.wide{{white-space:normal;text-align:left;}}'+
 '</style>');
 w.document.write('</head><body>'+c+'</body></html>');
 w.document.close(); w.print();
}}
</script>

</body>
</html>
"""
    return make_response(html)


@app.route("/user/grs/delete/<int:id>")
def user_delete_grs(id):
    user = session.get("user")
    if not user:
        return redirect("/login")

    con = db()
    cur = con.cursor()

    # pehle items delete
    cur.execute("""
        DELETE FROM user_grs_items
        WHERE grs_id=?
    """, (id,))

    # phir master, sirf current user ka
    cur.execute("""
        DELETE FROM user_grs
        WHERE id=? AND user=?
    """, (id, user))

    con.commit()
    con.close()

    return redirect("/user/grs/detail")




# ------------------ OWN DEPOT ISSUE INDENT ------------------
from datetime import date



@app.route("/user/issue/own", methods=["GET", "POST"])
def user_issue_own():
    user = session.get("user")
    if not user or user == "admin":
        return redirect("/login")

    msg = ""

    if request.method == "POST":
        indent_no = request.form.get("indent_no")
        vehicle_no = request.form.get("vehicle_no")

        # ✅ automatic today date
        indent_date = date.today().isoformat()

        cats = request.form.getlist("category[]")
        codes = request.form.getlist("code[]")
        names = request.form.getlist("name[]")
        qtys = request.form.getlist("qty[]")

        if indent_no and vehicle_no:
            con = db()
            cur = con.cursor()

            # -----------------------------
            # ✅ STOCK CHECK FIRST
            # -----------------------------
            for i in range(len(names)):
                if names[i].strip():
                    cat = cats[i].upper().strip()
                    code = codes[i].strip()
                    req_qty = float(qtys[i] or 0)

                    row = cur.execute("""
                        SELECT SUM(qty) as qty FROM (
                            SELECT qty FROM user_opening_stock
                            WHERE user=? AND category=? AND code=?

                            UNION ALL
                            SELECT i.qty
                            FROM user_grs_items i
                            JOIN user_grs g ON g.id=i.grs_id
                            WHERE g.user=? AND i.category=? AND i.code=?

                            UNION ALL
                            SELECT -i.qty
                            FROM user_indent_items i
                            JOIN user_indent u ON u.id=i.indent_id
                            WHERE u.user=? AND i.category=? AND i.code=?

                            UNION ALL
                            SELECT -i.qty
                            FROM challan_items i
                            JOIN challan c ON c.id=i.challan_id
                            WHERE c.from_depot=? AND i.category=? AND i.code=?
                        )
                    """, (
                        user, cat, code,
                        user, cat, code,
                        user, cat, code,
                        user, cat, code
                    )).fetchone()

                    avail = float(row["qty"] or 0)

                    if avail < req_qty:
                        con.close()
                        msg = f"❌ Stock not enough for {code}. Available: {avail}"
                        break


            # अगर msg set ho gaya to save mat karo
            if msg:
                pass
            else:
                # -----------------------------
                # ✅ SAVE INDENT
                # -----------------------------
                cur.execute("""
                    INSERT INTO user_indent (user, indent_no, indent_date, vehicle_no)
                    VALUES (?,?,?,?)
                """, (user, indent_no, indent_date, vehicle_no))
                iid = cur.lastrowid

                for i in range(len(names)):
                    if names[i].strip():
                        cat = cats[i].upper().strip()
                        code = codes[i].strip()
                        name = names[i].strip()
                        qty = float(qtys[i] or 0)

                        # save indent item
                        cur.execute("""
                            INSERT INTO user_indent_items
                            (indent_id, category, code, name, qty)
                            VALUES (?,?,?,?,?)
                        """, (iid, cat, code, name, qty))

                        # 🔻 minus from inventory
                        cur.execute("""
                            UPDATE user_inventory
                            SET qty = qty - ?
                            WHERE user=? AND category=? AND code=?
                        """, (qty, user, cat, code))

                con.commit()
                con.close()
                return redirect("/user/issue/own/detail")

        else:
            msg = "❌ Please fill all fields"

    return make_response(f"""
<!DOCTYPE html>
<html>
<head>
<title>Own Depot Issue Indent</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<div style="padding:15px;">
<h2>🚚 Own Depot Issue Indent</h2>

<form method="post">
<input name="indent_no" placeholder="Indent No" required>
<input name="vehicle_no" placeholder="Vehicle No" required><br><br>

<table border="1" width="100%">
<tr><th>Cat</th><th>Code</th><th>Name</th><th>Qty</th></tr>
<tbody id="items">
<tr>
<td><input name="category[]"></td>
<td><input name="code[]"></td>
<td><input name="name[]"></td>
<td><input name="qty[]"></td>
</tr>
</tbody>
</table>

<button type="button" onclick="addRow()">➕ Add Item</button><br><br>
<button type="submit">💾 Save Indent</button>
<a href="/user">⬅ Back</a>

<p style="color:red;font-weight:bold;">{msg}</p>
</form>
</div>

<script>
function addRow(){{
 let r=document.querySelector("#items tr").cloneNode(true);
 r.querySelectorAll("input").forEach(i=>i.value="");
 document.getElementById("items").appendChild(r);
}}
</script>
<script src="/static/item_autofill.js"></script>

</body>
</html>
""")



# ---------------- USER OWN DEPOT INDENT DETAIL ----------------
# ---------------- USER OWN DEPOT INDENT DETAIL ----------------
@app.route("/user/issue/own/detail")
def user_issue_own_detail():
    user = session.get("user")
    if not user or user == "admin":
        return redirect("/login")

    con = db()
    cur = con.cursor()

    rows = cur.execute("""
        SELECT * FROM user_indent
        WHERE user=?
        ORDER BY id DESC
    """, (user,)).fetchall()

    sections = ""
    for r in rows:
        items = cur.execute("""
            SELECT * FROM user_indent_items
            WHERE indent_id=?
        """, (r["id"],)).fetchall()

        cid = f"ind_{r['id']}"

        trs = ""
        for i,it in enumerate(items,1):
            trs += f"""
<tr>
<td>{i}</td>
<td>{it['category']}</td>
<td>{it['code']}</td>
<td class="wide">{it['name']}</td>
<td>{it['qty']}</td>
</tr>
"""

        sections += f"""
<div class="card" id="{cid}">
  <div class="head">
    <h3>Indent No: {r['indent_no']} | Date: {r['indent_date']} | Vehicle: {r['vehicle_no']}</h3>
    <div>
      <button class="print-btn" onclick="printSection('{cid}')">🖨️</button>
      <a href="/user/issue/own/delete/{r['id']}"
         onclick="return confirm('Delete this indent?')"
         class="del-btn">❌</a>
    </div>
  </div>

  <table class="po-table">
    <tr>
      <th>#</th><th>Cat</th><th>Code</th>
      <th class="wide">Item Name</th><th>Qty</th>
    </tr>
    {trs}
  </table>
</div>
"""

    con.close()

    return make_response(f"""
<!DOCTYPE html>
<html>
<head>
<title>Own Depot Issue Indent Detail</title>
<link rel="stylesheet" href="/static/style.css">
<style>
body {{ background:#f5f6fa; font-family:Arial; }}
.container {{ padding:20px; }}

.card {{
  background:white;
  padding:12px;
  border-radius:8px;
  margin-bottom:20px;
  box-shadow:0 0 8px #bbb;
}}

.head {{
  display:flex;
  justify-content:space-between;
  align-items:center;
  margin-bottom:10px;
}}

.head h3 {{
  margin:0;
  color:#003d80;
}}

.po-table {{
  width:100%;
  border-collapse:collapse;
  font-size:13px;
}}

.po-table th, .po-table td {{
  border:1px solid #ccc;
  padding:6px;
  text-align:center;
}}

.po-table th {{
  background:#003d80;
  color:white;
}}

.po-table .wide {{
  text-align:left;
  width:40%;
}}

.print-btn {{
  background:transparent;
  border:none;
  font-size:18px;
  cursor:pointer;
  color:#003d80;
}}

.del-btn {{
  color:red;
  font-size:18px;
  text-decoration:none;
  margin-left:10px;
}}

.top-links a {{
  margin-right:15px;
  text-decoration:none;
  color:#003d80;
  font-weight:bold;
}}
</style>
</head>
<body>

<div class="container">
<h2>🚚 Own Depot Issue Indent Detail</h2>

<div class="top-links">
  <a href="/user/issue/own">➕ New Indent</a>
  <a href="/user">⬅ Back</a>
</div>
<br>

{sections}

</div>

<script>
function printSection(id){{
 var c = document.getElementById(id).innerHTML;
 var w = window.open('', '', 'width=900,height=600');
 w.document.write('<html><head><title>Print</title>');
 w.document.write('<style>'+
 'table{{width:100%;border-collapse:collapse;font-size:11px}}'+
 'th,td{{border:1px solid #000;padding:4px;text-align:center}}'+
 '.wide{{text-align:left;}}'+
 '</style>');
 w.document.write('</head><body>'+c+'</body></html>');
 w.document.close();
 w.print();
}}
</script>

</body>
</html>
""")



@app.route("/user/issue/own/delete/<int:id>")
def user_issue_own_delete(id):
    user = session.get("user")
    if not user or user == "admin":
        return redirect("/login")

    con = db()
    cur = con.cursor()

    cur.execute("DELETE FROM user_indent_items WHERE indent_id=?", (id,))
    cur.execute("DELETE FROM user_indent WHERE id=? AND user=?", (id, user))

    con.commit()
    con.close()
    return redirect("/user/issue/own/detail")



# ---------------- USER GENERATE OTHER DEPOT CHALLAN ----------------
@app.route("/user/issue/other", methods=["GET", "POST"])
def user_other_challan_new():
    user = session.get("user")
    if not user:
        return redirect("/login")

    msg = ""

    if request.method == "POST":
        challan_no = request.form.get("challan_no")
        challan_date = request.form.get("challan_date")
        to_depot = request.form.get("to_depot")

        cats = request.form.getlist("category[]")
        codes = request.form.getlist("code[]")
        names = request.form.getlist("name[]")
        qtys = request.form.getlist("qty[]")
        prices = request.form.getlist("price[]")
        totals = request.form.getlist("total[]")

        if challan_no and challan_date and to_depot:
            con = db()
            cur = con.cursor()

            try:
                # ---- save challan master (from = user depot) ----
                cur.execute("""
                    INSERT INTO challan
                    (challan_no, challan_date, depot, from_depot)
                    VALUES (?,?,?,?)
                """, (challan_no, challan_date, to_depot, user))
                cid = cur.lastrowid

                for i in range(len(names)):
                    if names[i].strip():
                        cat = cats[i].upper().strip()
                        code = codes[i].strip()
                        name = names[i].strip()
                        qty = float(qtys[i] or 0)
                        price = float(prices[i] or 0)

                        # ✅ server-side safe calculation
                        total = qty * price

                        # ---- check USER inventory ----
                        row = cur.execute("""
                            SELECT id, qty FROM user_inventory
                            WHERE user=? AND category=? AND code=?
                        """, (user, cat, code)).fetchone()

                        if not row or float(row["qty"]) < qty:
                            raise Exception(f"❌ Stock not enough for {code}")

                        # ---- save challan item ----
                        cur.execute("""
                            INSERT INTO challan_items
                            (challan_id, category, code, name, qty, price, total)
                            VALUES (?,?,?,?,?,?,?)
                        """, (cid, cat, code, name, qty, price, total))

                        # ---- minus from user_inventory ----
                        cur.execute("""
                            UPDATE user_inventory
                            SET qty = qty - ?
                            WHERE id=?
                        """, (qty, row["id"]))

                con.commit()
                con.close()
                return redirect("/user/issue/other/detail")

            except Exception as e:
                con.rollback()
                con.close()
                msg = str(e)

    depot_opts = "".join([f"<option>{d}</option>" for d in DEPOTS])

    html = """
<!DOCTYPE html>
<html>
<head>
<title>Generate Other Depot Challan</title>
<link rel="stylesheet" href="/static/style.css">
<style>
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{border:1px solid #ccc;padding:5px;text-align:center}
input,select{width:100%;padding:5px}
.top{display:grid;grid-template-columns:1fr 1fr 2fr;gap:8px}
.add-btn{margin:6px 0}
</style>
</head>
<body>

<div style="padding:15px;">
<h2>🚚 Generate Other Depot Challan</h2>

<form method="post">
<div class="top">
  <input name="challan_no" placeholder="Challan No" required>
  <input type="date" name="challan_date" required>
  <select name="to_depot" required>
    <option value="">-- Select To Depot --</option>
    """ + depot_opts + """
  </select>
</div><br>

<table>
<tr>
<th>Cat</th>
<th>Code</th>
<th>Name</th>
<th>Qty</th>
<th>Price</th>
<th>Total</th>
</tr>

<tbody id="items">
<tr>
<td><input name="category[]"></td>
<td><input name="code[]"></td>
<td><input name="name[]" required></td>
<td><input name="qty[]" class="qty" required></td>
<td><input name="price[]" class="price" required></td>
<td><input name="total[]" class="total" readonly></td>
</tr>
</tbody>
</table>

<button type="button" class="add-btn" onclick="addRow()">➕ Add Item</button><br>
<button type="submit">💾 Save Challan</button>
<a href="/user">⬅ Back</a>

<p style="color:red;">""" + msg + """</p>
</form>
</div>

<script>
function calculateRowTotal(row){
    let qty = parseFloat(row.querySelector(".qty").value) || 0;
    let price = parseFloat(row.querySelector(".price").value) || 0;
    row.querySelector(".total").value = (qty * price).toFixed(2);
}

document.addEventListener("input", function(e){
    if(e.target.classList.contains("qty") ||
       e.target.classList.contains("price")){
        let row = e.target.closest("tr");
        calculateRowTotal(row);
    }
});

function addRow(){
    let r = document.querySelector("#items tr").cloneNode(true);
    r.querySelectorAll("input").forEach(i => i.value = "");
    document.getElementById("items").appendChild(r);
}
</script>

<script src="/static/item_autofill.js"></script>

</body>
</html>
"""
    return make_response(html)


# ---------------- USER OTHER DEPOT CHALLAN DETAIL ----------------
@app.route("/user/issue/other/detail")
def user_other_challan_detail():
    user = session.get("user")
    if not user:
        return redirect("/login")

    con = db()
    cur = con.cursor()

    # sirf wahi challan jo is user ne banaye ho
    rows = cur.execute("""
        SELECT * FROM challan
        WHERE from_depot=?
        ORDER BY id DESC
    """, (user,)).fetchall()

    sections = ""
    for c in rows:
        items = cur.execute("""
            SELECT * FROM challan_items WHERE challan_id=?
        """, (c["id"],)).fetchall()

        cid = f"ch_{c['id']}"
        trs = ""
        for i, it in enumerate(items, 1):
            trs += f"""
<tr>
<td>{i}</td>
<td>{it['category']}</td>
<td>{it['code']}</td>
<td class="wide">{it['name']}</td>
<td>{it['qty']}</td>
<td>{it['price']}</td>
<td>{it['total']}</td>
</tr>
"""

        sections += f"""
<div class="card" id="{cid}">
  <div class="head">
    <h3>Challan No: {c['challan_no']} | Date: {c['challan_date']} | To: {c['depot']}</h3>
    <button class="print-btn" onclick="printSection('{cid}')">🖨️</button>
  </div>

  <table class="po-table">
    <tr>
      <th>#</th><th>Cat</th><th>Code</th>
      <th class="wide">Item Name</th>
      <th>Qty</th><th>Price</th><th>Total</th>
    </tr>
    {trs}
  </table>
</div>
"""

    con.close()

    return make_response(f"""
<!DOCTYPE html>
<html>
<head>
<title>Other Depot Challan Detail</title>
<link rel="stylesheet" href="/static/style.css">
<style>
body {{ background:#f5f6fa; }}
.container {{ padding:20px; }}

.card {{
  background:white;
  padding:12px;
  border-radius:8px;
  margin-bottom:20px;
  box-shadow:0 0 8px #bbb;
}}

.head {{
  display:flex;
  justify-content:space-between;
  align-items:center;
  margin-bottom:10px;
}}

.head h3 {{
  margin:0;
  color:#003d80;
}}

.po-table {{
  width:100%;
  border-collapse:collapse;
  font-size:13px;
}}

.po-table th, .po-table td {{
  border:1px solid #ccc;
  padding:6px;
  text-align:center;
}}

.po-table th {{
  background:#003d80;
  color:white;
}}

.po-table .wide {{
  text-align:left;
  width:35%;
}}

.print-btn {{
  background:transparent;
  border:none;
  font-size:18px;
  cursor:pointer;
  color:#003d80;
}}

.top-links a {{
  margin-right:15px;
  text-decoration:none;
  color:#003d80;
  font-weight:bold;
}}
</style>
</head>
<body>

<div class="container">
<h2>📄 Other Depot Challan Detail</h2>

<div class="top-links">
  <a href="/user/issue/other">➕ Generate Other Depot Challan</a>
  <a href="/user">⬅ Back</a>
</div>
<br>

{sections}
</div>

<script>
function printSection(id){{
 var c=document.getElementById(id).innerHTML;
 var w=window.open('','','width=900,height=600');
 w.document.write('<html><head><title>Print</title>');
 w.document.write('<style>'+
 'table{{width:100%;border-collapse:collapse;font-size:11px}}'+
 'th,td{{border:1px solid #000;padding:4px;text-align:center}}'+
 '.wide{{text-align:left;}}'+
 '</style>');
 w.document.write('</head><body>'+c+'</body></html>');
 w.document.close(); w.print();
}}
</script>

</body>
</html>
""")

# ---------------- USER DELETE OTHER DEPOT CHALLAN ----------------
@app.route("/user/issue/other/delete/<int:id>")
def user_other_challan_delete(id):
    user = session.get("user")
    if not user:
        return redirect("/login")

    con = db()
    cur = con.cursor()

    # get items to return stock
    items = cur.execute("""
        SELECT * FROM challan_items WHERE challan_id=?
    """, (id,)).fetchall()

    for it in items:
        cur.execute("""
            UPDATE user_inventory
            SET qty = qty + ?
            WHERE user=? AND category=? AND code=?
        """, (it["qty"], user, it["category"], it["code"]))

    cur.execute("DELETE FROM challan_items WHERE challan_id=?", (id,))
    cur.execute("DELETE FROM challan WHERE id=?", (id,))
    con.commit()
    con.close()

    return redirect("/user/issue/other/detail")





# ================= USER OWN DEPOT INVENTORY =================

@app.route("/user/inv/own")
def user_inventory_own():
    user = session.get("user")
    if not user:
        return redirect("/login")

    con = db()
    cur = con.cursor()

    # ================= OVERALL INVENTORY =================
    rows = cur.execute("""
        SELECT category, code, name, SUM(qty) qty FROM (
            SELECT category, code, name, qty
            FROM user_opening_stock
            WHERE user=?

            UNION ALL

            SELECT i.category, i.code, i.name, i.qty
            FROM user_grs_items i
            JOIN user_grs g ON g.id=i.grs_id
            WHERE g.user=?

            UNION ALL

            SELECT i.category, i.code, i.name, -i.qty
            FROM user_indent_items i
            JOIN user_indent u ON u.id=i.indent_id
            WHERE u.user=?

            UNION ALL

            -- 👉 Other depot challan ISSUE
            SELECT i.category, i.code, i.name, -i.qty
            FROM challan_items i
            JOIN challan c ON c.id=i.challan_id
            WHERE c.from_depot=?
        )
        GROUP BY category, code, name
        ORDER BY category, name
    """, (user, user, user, user)).fetchall()


    # ================= VEHICLE WISE (ONLY INDENT with DATE) =================
    vrows = cur.execute("""
        SELECT
            u.vehicle_no,
            u.indent_date,
            i.category,
            i.code,
            i.name,
            i.qty
        FROM user_indent_items i
        JOIN user_indent u ON u.id=i.indent_id
        WHERE u.user=?
        ORDER BY u.vehicle_no, u.indent_date
    """, (user,)).fetchall()

    vmap = {}
    for r in vrows:
        vmap.setdefault(r["vehicle_no"], []).append(r)

    # ================= FIRM WISE (ONLY GRS with DATE) =================
    frows = cur.execute("""
        SELECT
            g.firm,
            g.grs_date,
            i.category,
            i.code,
            i.name,
            i.qty
        FROM user_grs_items i
        JOIN user_grs g ON g.id=i.grs_id
        WHERE g.user=?
        ORDER BY g.firm, g.grs_date
    """, (user,)).fetchall()

    fmap = {}
    for r in frows:
        fmap.setdefault(r["firm"], []).append(r)

    con.close()

    # ================= BUILD OVERALL TABLE =================
    trs = ""
    for r in rows:
        q = float(r["qty"] or 0)
        trs += f"""
        <tr>
          <td>{r['category']}</td>
          <td>
            <a href="/user/inv/own/{r['category']}/{r['code']}">
              {r['code']} - {r['name']}
            </a>
          </td>
          <td>{q}</td>
        </tr>
        """

    # ================= VEHICLE SECTIONS =================
    vopts = "<option value=''>-- Select Vehicle --</option>"
    vsections = ""
    for v, items in vmap.items():
        vopts += f"<option value='{v}'>{v}</option>"
        vtrs = ""
        for it in items:
            vtrs += f"""
            <tr>
              <td>{it['indent_date']}</td>
              <td>{it['category']}</td>
              <td>{it['code']} - {it['name']}</td>
              <td>{it['qty']}</td>
            </tr>
            """
        vsections += f"""
        <table class="vtbl" data-veh="{v}" style="display:none">
        <tr><th>Date</th><th>Cat</th><th>Item</th><th>Qty</th></tr>
        {vtrs}
        </table>
        """

    # ================= FIRM SECTIONS =================
    fopts = "<option value=''>-- Select Firm --</option>"
    fsections = ""
    for f, items in fmap.items():
        fopts += f"<option value='{f}'>{f}</option>"
        ftrs = ""
        for it in items:
            ftrs += f"""
            <tr>
              <td>{it['grs_date']}</td>
              <td>{it['category']}</td>
              <td>{it['code']} - {it['name']}</td>
              <td>{it['qty']}</td>
            </tr>
            """
        fsections += f"""
        <table class="ftbl" data-firm="{f}" style="display:none">
        <tr><th>Date</th><th>Cat</th><th>Item</th><th>Qty</th></tr>
        {ftrs}
        </table>
        """

    return make_response(f"""
<!DOCTYPE html>
<html>
<head>
<title>Own Depot Inventory</title>
<style>
body{{font-family:Arial;background:#f4fafa}}
table{{width:100%;border-collapse:collapse;font-size:14px;margin-bottom:15px}}
th,td{{border:1px solid #ccc;padding:8px;text-align:center}}
th{{background:#006060;color:white}}
tr:nth-child(even){{background:#e9f3f3}}
.print-btn{{background:#006060;color:white;border:none;padding:6px 12px;border-radius:5px;cursor:pointer}}
.filter{{margin:10px 0}}
select{{padding:6px}}
</style>
</head>
<body>
<div style="padding:15px;">
<h2>📦 Own Depot Inventory ({user})</h2>

<button class="print-btn" onclick="printAny('invTable')">🖨️ Print Inventory</button>

<table id="invTable">
<tr><th>Cat</th><th>Item</th><th>Qty</th></tr>
{trs}
</table>

<hr>

<h3>🚚 Vehicle Wise Issue</h3>
<div class="filter">
<select id="vehSel" onchange="showVeh()">{vopts}</select>
<button class="print-btn" onclick="printVeh()">🖨️ Print Vehicle</button>
</div>
{vsections}

<hr>

<h3>🏢 Firm Wise GRS</h3>
<div class="filter">
<select id="firmSel" onchange="showFirm()">{fopts}</select>
<button class="print-btn" onclick="printFirm()">🖨️ Print Firm</button>
</div>
{fsections}

<br>
<a href="/user">⬅ Back</a>
</div>

<script>
function printAny(id){{
  var c=document.getElementById(id).outerHTML;
  var w=window.open('','','width=900,height=600');
  w.document.write('<html><head><title>Print</title>');
  w.document.write('<style>table{{width:100%;border-collapse:collapse;font-size:12px}} th,td{{border:1px solid #000;padding:5px;text-align:center}}</style>');
  w.document.write('</head><body>'+c+'</body></html>');
  w.document.close(); w.print();
}}

function showVeh(){{
  var v=document.getElementById('vehSel').value;
  document.querySelectorAll('.vtbl').forEach(t=>t.style.display='none');
  if(v) document.querySelector('.vtbl[data-veh="'+v+'"]').style.display='table';
}}
function printVeh(){{
  var v=document.getElementById('vehSel').value;
  if(!v) return alert("Select vehicle");
  var t=document.querySelector('.vtbl[data-veh="'+v+'"]');
  t.setAttribute("id","tmpV");
  printAny("tmpV");
}}

function showFirm(){{
  var f=document.getElementById('firmSel').value;
  document.querySelectorAll('.ftbl').forEach(t=>t.style.display='none');
  if(f) document.querySelector('.ftbl[data-firm="'+f+'"]').style.display='table';
}}
function printFirm(){{
  var f=document.getElementById('firmSel').value;
  if(!f) return alert("Select firm");
  var t=document.querySelector('.ftbl[data-firm="'+f+'"]');
  t.setAttribute("id","tmpF");
  printAny("tmpF");
}}
</script>

</body>
</html>
""")




@app.route("/user/inv/own/<cat>/<code>")
def user_inventory_item_detail(cat, code):
    user = session.get("user")
    if not user:
        return redirect("/login")

    con = db()
    cur = con.cursor()
    cat_u = cat.upper()

    # ---- item name (from any table) ----
    row = cur.execute("""
        SELECT name FROM (
            SELECT name FROM user_opening_stock WHERE user=? AND category=? AND code=?
            UNION
            SELECT name FROM user_grs_items WHERE category=? AND code=?
            UNION
            SELECT name FROM user_indent_items WHERE category=? AND code=?
        ) LIMIT 1
    """, (user, cat_u, code, cat_u, code, cat_u, code)).fetchone()
    name = row["name"] if row else ""

    trs = ""
    sn = 1
    total = 0

    # ---- Opening Stock ----
    opens = cur.execute("""
        SELECT entry_date, qty
        FROM user_opening_stock
        WHERE user=? AND category=? AND code=?
    """, (user, cat_u, code)).fetchall()

    for r in opens:
        q = float(r["qty"] or 0)
        total += q
        trs += f"<tr><td>{sn}</td><td>OPENING</td><td>-</td><td>{r['entry_date']}</td><td>-</td><td>{q}</td></tr>"
        sn += 1

    # ---- GRS Entries ----
    grs_rows = cur.execute("""
        SELECT g.grs_date, g.grs_no, g.firm, i.qty
        FROM user_grs_items i
        JOIN user_grs g ON g.id=i.grs_id
        WHERE g.user=? AND i.category=? AND i.code=?
        ORDER BY g.grs_date
    """, (user, cat_u, code)).fetchall()

    for r in grs_rows:
        q = float(r["qty"] or 0)
        total += q
        trs += f"<tr><td>{sn}</td><td>GRS</td><td>{r['grs_no']}</td><td>{r['grs_date']}</td><td>{r['firm']}</td><td>{q}</td></tr>"
        sn += 1

    # ---- Issue / Indent Entries ----
    ind_rows = cur.execute("""
        SELECT u.indent_date, u.indent_no, u.vehicle_no, i.qty
        FROM user_indent_items i
        JOIN user_indent u ON u.id=i.indent_id
        WHERE u.user=? AND i.category=? AND i.code=?
        ORDER BY u.indent_date
    """, (user, cat_u, code)).fetchall()

    for r in ind_rows:
        q = float(r["qty"] or 0)
        total -= q
        trs += f"<tr><td>{sn}</td><td>ISSUE</td><td>{r['indent_no']}</td><td>{r['indent_date']}</td><td>{r['vehicle_no']}</td><td>-{q}</td></tr>"
        sn += 1
        
    # ---- Other Depot Challan ISSUE ----
    ch_rows = cur.execute("""
       SELECT c.challan_date, c.challan_no, c.depot, i.qty
       FROM challan_items i
       JOIN challan c ON c.id=i.challan_id
       WHERE c.from_depot=? AND i.category=? AND i.code=?
       ORDER BY c.challan_date
    """, (user, cat_u, code)).fetchall()

    for r in ch_rows:
        q = float(r["qty"] or 0)
        total -= q
        trs += f"<tr><td>{sn}</td><td>OTHER DEPOT CHALLAN</td><td>{r['challan_no']}</td><td>{r['challan_date']}</td><td>{r['depot']}</td><td>-{q}</td></tr>"
        sn += 1


    con.close()

    return make_response(f"""
<!DOCTYPE html>
<html>
<head>
<title>Item Ledger</title>
<style>
body{{font-family:Arial;background:#f4fafa}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
th,td{{border:1px solid #999;padding:6px;text-align:center}}
th{{background:#006060;color:white}}
.total-row td{{font-weight:bold;background:#f0f0f0}}
.print-btn{{background:#006060;color:white;border:none;padding:6px 12px;border-radius:5px;cursor:pointer}}
</style>
</head>
<body>
<div style="padding:15px;">
<h2>📦 Item Ledger (Depot: {user})</h2>
<h3>{code} - {name} ({cat_u})</h3>

<button class="print-btn" onclick="printItem()">🖨️ Print</button>
<br><br>

<table id="itemTable">
<tr>
  <th>#</th><th>Type</th><th>No.</th><th>Date</th><th>Source / Vehicle</th><th>Qty</th>
</tr>
{trs}
<tr class="total-row">
  <td colspan="5">TOTAL STOCK</td>
  <td>{total}</td>
</tr>
</table>

<br>
<a href="/user/inv/own">⬅ Back to Inventory</a>
</div>

<script>
function printItem(){{
 var c=document.getElementById("itemTable").outerHTML;
 var w=window.open('','','width=900,height=600');
 w.document.write('<html><head><title>Print</title>');
 w.document.write('<style>table{{width:100%;border-collapse:collapse;font-size:12px}} th,td{{border:1px solid #000;padding:4px;text-align:center}}</style>');
 w.document.write('</head><body>'+c+'</body></html>');
 w.document.close(); w.print();
}}
</script>
</body>
</html>
""")



# ================= OTHER DEPOT INVENTORY (VIEW ONLY) =================

@app.route("/user/inv/other", methods=["GET", "POST"])
def user_inventory_other():
    user = session.get("user")
    if not user:
        return redirect("/login")

    selected = request.form.get("depot")
    trs = ""

    if selected:
        con = db()
        cur = con.cursor()

        rows = cur.execute("""
            SELECT category, code, name, SUM(qty) as qty FROM (

                -- Opening
                SELECT category, code, name, qty
                FROM user_opening_stock
                WHERE user=?

                UNION ALL

                -- GRS
                SELECT i.category, i.code, i.name, i.qty
                FROM user_grs_items i
                JOIN user_grs g ON g.id=i.grs_id
                WHERE g.user=?

                UNION ALL

                -- Own depot indent (minus)
                SELECT i.category, i.code, i.name, -i.qty
                FROM user_indent_items i
                JOIN user_indent u ON u.id=i.indent_id
                WHERE u.user=?

                UNION ALL

                -- Other depot challan issue (minus)
                SELECT i.category, i.code, i.name, -i.qty
                FROM challan_items i
                JOIN challan c ON c.id=i.challan_id
                WHERE c.from_depot=?

            )
            GROUP BY category, code, name
            ORDER BY category, name
        """, (selected, selected, selected, selected)).fetchall()

        con.close()

        for r in rows:
            q = float(r["qty"] or 0)
            trs += f"""
            <tr>
              <td>{r['category']}</td>
              <td>{r['code']} - {r['name']}</td>
              <td>{q}</td>
            </tr>
            """

    # 👉 dropdown = DEPOTS list, current user ko chhod ke
    opts = "<option value=''>-- Select Depot --</option>"
    for d in DEPOTS:
        if d != user:
            sel = "selected" if d == selected else ""
            opts += f"<option value='{d}' {sel}>{d}</option>"

    return make_response(f"""
<!DOCTYPE html>
<html>
<head>
<title>Other Depot Inventory</title>
<style>
body{{font-family:Arial;background:#f4fafa}}
table{{width:100%;border-collapse:collapse;font-size:14px;margin-top:15px}}
th,td{{border:1px solid #ccc;padding:8px;text-align:center}}
th{{background:#006060;color:white}}
tr:nth-child(even){{background:#e9f3f3}}
select{{padding:6px;font-size:14px}}
</style>
</head>
<body>
<div style="padding:15px;">
<h2>📦 Other Depot Inventory (View Only)</h2>

<form method="post">
<select name="depot" onchange="this.form.submit()">
{opts}
</select>
</form>

<table id="invTable">
<tr><th>Cat</th><th>Item</th><th>Qty</th></tr>
{trs}
</table>

<br>
<a href="/user">⬅ Back</a>
</div>
</body>
</html>
""")



# ================= CENTRAL STORE INVENTORY (VIEW ONLY) =================

# ================= CENTRAL STORE INVENTORY (LIVE CALC) =================

@app.route("/user/inv/central", methods=["GET", "POST"])
def user_inventory_central():
    user = session.get("user")
    if not user:
        return redirect("/login")

    selected = request.form.get("cat")

    con = db()
    cur = con.cursor()

    trs = ""
    if selected:
        rows = cur.execute("""
            SELECT category, code, name, SUM(qty) as qty FROM (
                -- opening
                SELECT category, code, name, qty
                FROM opening_stock
                WHERE category=?

                UNION ALL

                -- grs
                SELECT gi.category, gi.code, gi.name, gi.qty
                FROM grs_items gi
                JOIN grs g ON g.id = gi.grs_id
                WHERE gi.category=?

                UNION ALL

                -- issue via challan FROM CENTRAL (minus only admin challans)
                SELECT ci.category, ci.code, ci.name, -ci.qty
                FROM challan_items ci
                JOIN challan c ON c.id = ci.challan_id
                WHERE ci.category=? AND c.from_depot='admin'

            )
            GROUP BY category, code, name
            ORDER BY name
        """, (selected.upper(), selected.upper(), selected.upper())).fetchall()

        for r in rows:
            q = float(r["qty"] or 0)
            trs += f"""
            <tr>
              <td>{r['category']}</td>
              <td>{r['code']} - {r['name']}</td>
              <td>{q}</td>
            </tr>
            """

    # categories from opening + grs
    cats = cur.execute("""
        SELECT DISTINCT category FROM (
            SELECT category FROM opening_stock
            UNION
            SELECT gi.category FROM grs_items gi
        )
        ORDER BY category
    """).fetchall()

    con.close()

    opts = "<option value=''>-- Select Category --</option>"
    for c in cats:
        sel = "selected" if c["category"] == selected else ""
        opts += f"<option value='{c['category']}' {sel}>{c['category']}</option>"

    return make_response(f"""
<!DOCTYPE html>
<html>
<head>
<title>Central Store Inventory</title>
<style>
body{{font-family:Arial;background:#f4fafa}}
table{{width:100%;border-collapse:collapse;font-size:14px;margin-top:15px}}
th,td{{border:1px solid #ccc;padding:8px;text-align:center}}
th{{background:#006060;color:white}}
tr:nth-child(even){{background:#e9f3f3}}
select{{padding:6px;font-size:14px}}
.print-btn{{background:#006060;color:white;border:none;padding:6px 12px;border-radius:5px;cursor:pointer}}
</style>
</head>
<body>
<div style="padding:15px;">
<h2>🏬 Central Store Inventory (Live)</h2>

<form method="post">
<select name="cat" onchange="this.form.submit()">
{opts}
</select>
</form>

<button class="print-btn" onclick="printAny()">🖨️ Print</button>

<table id="invTable">
<tr><th>Cat</th><th>Item</th><th>Qty</th></tr>
{trs}
</table>

<br>
<a href="/user">⬅ Back</a>
</div>

<script>
function printAny(){{
  var c=document.getElementById("invTable").outerHTML;
  var w=window.open('','','width=900,height=600');
  w.document.write('<html><head><title>Print</title>');
  w.document.write('<style>table{{width:100%;border-collapse:collapse;font-size:12px}} th,td{{border:1px solid #000;padding:5px;text-align:center}}</style>');
  w.document.write('</head><body>'+c+'</body></html>');
  w.document.close(); w.print();
}}
</script>

</body>
</html>
""")



# ================= ADMIN DEPOT WISE INVENTORY =================

@app.route("/admin/depot_inventory", methods=["GET", "POST"])
def admin_depot_inventory():
    if session.get("user") != "admin":
        return redirect("/login")

    selected = request.form.get("depot") or request.args.get("back")
    trs = ""

    if selected:
        con = db()
        cur = con.cursor()

        rows = cur.execute("""
            SELECT category, code, name, SUM(qty) qty FROM (
                SELECT category, code, name, qty
                FROM user_opening_stock
                WHERE user=?

                UNION ALL

                SELECT i.category, i.code, i.name, i.qty
                FROM user_grs_items i
                JOIN user_grs g ON g.id=i.grs_id
                WHERE g.user=?

                UNION ALL

                SELECT i.category, i.code, i.name, -i.qty
                FROM user_indent_items i
                JOIN user_indent u ON u.id=i.indent_id
                WHERE u.user=?

                UNION ALL

                -- ❗ Other depot challan issue (minus)
                SELECT i.category, i.code, i.name, -i.qty
                FROM challan_items i
                JOIN challan c ON c.id=i.challan_id
                WHERE c.from_depot=?
            )
            GROUP BY category, code, name
            ORDER BY category, name
        """, (selected, selected, selected, selected)).fetchall()

        con.close()

        for r in rows:
            q = float(r["qty"] or 0)
            trs += f"""
            <tr>
              <td>{r['category']}</td>
              <td>
                <a href="/admin/depot_inventory/{selected}/{r['category']}/{r['code']}">
                  {r['code']} - {r['name']}
                </a>
              </td>
              <td>{q}</td>
            </tr>
            """

    opts = "<option value=''>-- Select Depot --</option>"
    for d in DEPOTS:
        sel = "selected" if d == selected else ""
        opts += f"<option value='{d}' {sel}>{d}</option>"

    return make_response(f"""
<!DOCTYPE html>
<html>
<head>
<title>Depot Wise Inventory</title>
<style>
body{{font-family:Arial;background:#f4fafa}}
table{{width:100%;border-collapse:collapse;font-size:14px;margin-top:10px}}
th,td{{border:1px solid #ccc;padding:8px;text-align:center}}
th{{background:#003d80;color:white}}
tr:nth-child(even){{background:#eef3fb}}
a{{color:#003d80;font-weight:bold;text-decoration:none}}
select{{padding:6px;font-size:14px}}
.print-btn{{background:#003d80;color:white;border:none;padding:6px 12px;border-radius:5px;cursor:pointer;margin:8px 0}}
</style>
</head>
<body>
<div style="padding:15px;">
<h2>🏭 Depot Wise Inventory (Admin)</h2>

<form method="post">
<select name="depot" onchange="this.form.submit()">
{opts}
</select>
</form>

<button class="print-btn" onclick="printAny()">🖨️ Print Depot Inventory</button>

<table id="invTable">
<tr><th>Cat</th><th>Item</th><th>Qty</th></tr>
{trs}
</table>

<br>
<a href="/admin">⬅ Back</a>
</div>

<script>
function printAny(){{
  var c=document.getElementById("invTable").outerHTML;
  var w=window.open('','','width=900,height=600');
  w.document.write('<html><head><title>Print</title>');
  w.document.write('<style>table{{width:100%;border-collapse:collapse;font-size:12px}} th,td{{border:1px solid #000;padding:5px;text-align:center}}</style>');
  w.document.write('</head><body>'+c+'</body></html>');
  w.document.close(); w.print();
}}
</script>

</body>
</html>
""")



# ================= ADMIN DEPOT WISE INVENTORY =================

from datetime import date

# ================= ADMIN DEPOT ITEM DETAIL =================

from datetime import date

@app.route("/admin/depot_inventory/<depot>/<cat>/<code>")
def admin_depot_item_detail(depot, cat, code):
    if session.get("user") != "admin":
        return redirect("/login")

    con = db()
    cur = con.cursor()
    cat_u = cat.upper()

    # ---- item name ----
    row = cur.execute("""
        SELECT name FROM user_inventory
        WHERE user=? AND category=? AND code=?
        LIMIT 1
    """, (depot, cat_u, code)).fetchone()
    name = row["name"] if row else ""

    trs = ""
    sn = 1
    total = 0

    # ---------------- OPENING ----------------
    opens = cur.execute("""
        SELECT qty FROM user_opening_stock
        WHERE user=? AND category=? AND code=?
    """, (depot, cat_u, code)).fetchall()

    op_date = date.today().isoformat()
    for r in opens:
        q = float(r["qty"] or 0)
        total += q
        trs += f"""
<tr>
  <td>{sn}</td><td>OPENING</td>
  <td>-</td><td>{op_date}</td>
  <td>-</td><td>{q}</td>
</tr>
"""
        sn += 1

    # ---------------- GRS ----------------
    grs_rows = cur.execute("""
        SELECT g.grs_date, g.grs_no, g.firm, i.qty
        FROM user_grs_items i
        JOIN user_grs g ON g.id=i.grs_id
        WHERE g.user=? AND i.category=? AND i.code=?
        ORDER BY g.grs_date
    """, (depot, cat_u, code)).fetchall()

    for r in grs_rows:
        q = float(r["qty"] or 0)
        total += q
        trs += f"""
<tr>
  <td>{sn}</td><td>GRS</td>
  <td>{r['grs_no']}</td><td>{r['grs_date']}</td>
  <td>{r['firm']}</td><td>{q}</td>
</tr>
"""
        sn += 1

    # ---------------- INDENT / ISSUE ----------------
    ind_rows = cur.execute("""
        SELECT u.indent_date, u.indent_no, u.vehicle_no, i.qty
        FROM user_indent_items i
        JOIN user_indent u ON u.id=i.indent_id
        WHERE u.user=? AND i.category=? AND i.code=?
        ORDER BY u.indent_date
    """, (depot, cat_u, code)).fetchall()

    for r in ind_rows:
        q = float(r["qty"] or 0)
        total -= q
        trs += f"""
<tr>
  <td>{sn}</td><td>ISSUE</td>
  <td>{r['indent_no']}</td><td>{r['indent_date']}</td>
  <td>{r['vehicle_no']}</td><td>-{q}</td>
</tr>
"""
        sn += 1

    # ---------------- OTHER DEPOT CHALLAN ISSUE ----------------
    ch_rows = cur.execute("""
        SELECT c.challan_date, c.challan_no, c.depot, i.qty
        FROM challan_items i
        JOIN challan c ON c.id=i.challan_id
        WHERE c.from_depot=? AND i.category=? AND i.code=?
        ORDER BY c.challan_date
    """, (depot, cat_u, code)).fetchall()

    for r in ch_rows:
        q = float(r["qty"] or 0)
        total -= q
        trs += f"""
<tr>
  <td>{sn}</td><td>OTHER DEPOT CHALLAN</td>
  <td>{r['challan_no']}</td><td>{r['challan_date']}</td>
  <td>{r['depot']}</td><td>-{q}</td>
</tr>
"""
        sn += 1

    con.close()

    return make_response(f"""
<!DOCTYPE html>
<html>
<head>
<title>Depot Item Detail</title>
<style>
body{{font-family:Arial;background:#f4fafa}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
th,td{{border:1px solid #ccc;padding:8px;text-align:center}}
th{{background:#003d80;color:white}}
.total-row td{{font-weight:bold;background:#eef3fb}}
</style>
</head>
<body>
<div style="padding:15px;">
<h2>📦 {depot} - Item Ledger</h2>
<h3>{code} - {name} ({cat_u})</h3>

<table>
<tr>
  <th>#</th><th>Type</th><th>no.</th><th>Date</th>
  <th>Vehicle / Firm</th><th>Qty</th>
</tr>
{trs}
<tr class="total-row">
  <td colspan="5">TOTAL</td>
  <td>{total}</td>
</tr>
</table>

<br>
<a href="/admin/depot_inventory?back={depot}">⬅ Back</a>
</div>
</body>
</html>
""")



from datetime import date, timedelta

@app.route("/user/demand_letter", methods=["GET","POST"])
def user_demand_letter():
    user = session.get("user")
    if not user:
        return redirect("/login")

    con = db()
    cur = con.cursor()
    msg = ""

    # ================= SAVE DEMAND =================
    if request.method == "POST":
        letter_no = request.form.get("letter_no")

        cats   = request.form.getlist("category[]")
        codes  = request.form.getlist("code[]")
        names  = request.form.getlist("name[]")
        qtys   = request.form.getlist("qty[]")
        stocks = request.form.getlist("stock[]")
        cons   = request.form.getlist("cons[]")
        pins   = request.form.getlist("pin[]")

        # ---- SAVE PINNED ITEMS ----
        cur.execute("DELETE FROM user_pinned_items WHERE user=?", (user,))
        for p in pins:
            cat, code = p.split("|")
            cur.execute(
                "INSERT OR IGNORE INTO user_pinned_items (user,category,code) VALUES (?,?,?)",
                (user, cat, code)
            )

        # ---- CREATE NEW DRAFT LETTER ----
        cur.execute("""
            INSERT INTO demand_letter (user, letter_no, letter_date, status)
            VALUES (?,?,?,?)
        """, (user, letter_no, date.today().isoformat(), "draft"))
        lid = cur.lastrowid

        added = False

        # ---- EXCEL ITEMS ----
        for i in range(len(names)):
            q = float(qtys[i] or 0)
            if q > 0:
                added = True
                cur.execute("""
                    INSERT INTO demand_letter_items
                    (letter_id, category, code, name,
                     demand_qty, stock_at_time, last_3m_consumption)
                    VALUES (?,?,?,?,?,?,?)
                """, (
                    lid,
                    cats[i],
                    codes[i],
                    names[i],
                    q,
                    stocks[i],
                    cons[i]
                ))

        # ---- MANUAL ITEMS (CODE = BLANK) ----
        m_cats  = request.form.getlist("m_category[]")
        m_names = request.form.getlist("m_name[]")
        m_qtys  = request.form.getlist("m_qty[]")
        m_stks  = request.form.getlist("m_stock[]")
        m_cons  = request.form.getlist("m_cons[]")

        for i in range(len(m_names)):
            if m_names[i].strip():
                q = float(m_qtys[i] or 0)
                if q > 0:
                    added = True
                    cur.execute("""
                        INSERT INTO demand_letter_items
                        (letter_id, category, code, name,
                         demand_qty, stock_at_time, last_3m_consumption)
                        VALUES (?,?,?,?,?,?,?)
                    """, (
                        lid,
                        m_cats[i].upper(),
                        "",
                        m_names[i],
                        q,
                        m_stks[i],
                        m_cons[i]
                    ))

        if added:
            con.commit()
            con.close()
            return redirect("/user/demand_letter_detail")
        else:
            con.rollback()
            msg = "❌ Kam se kam ek item demand bharo"

    # ================= LOAD LAST DRAFT MANUAL ITEMS =================
    last = cur.execute("""
        SELECT id FROM demand_letter
        WHERE user=?
        ORDER BY id DESC LIMIT 1
    """, (user,)).fetchone()

    manual_rows = ""
    if last:
        mids = cur.execute("""
            SELECT * FROM demand_letter_items
            WHERE letter_id=? AND code=''
        """, (last["id"],)).fetchall()

        for m in mids:
            manual_rows += f"""
<tr>
<td></td>
<td>*</td>
<td><input name="m_category[]" value="{m['category']}"></td>
<td></td>
<td style="text-align:left">
  <input name="m_name[]" value="{m['name']}" style="width:100%">
</td>
<td><input name="m_qty[]" class="qty" value="{m['demand_qty']}"></td>
<td><input name="m_stock[]" class="qty" value="{m['stock_at_time']}"></td>
<td><input name="m_cons[]" class="qty" value="{m['last_3m_consumption']}"></td>
<td class="ro">—</td>
<td class="ro">—</td>
</tr>
"""

    # ================= EXCEL ITEMS =================
    pinned = cur.execute(
        "SELECT category,code FROM user_pinned_items WHERE user=?",
        (user,)
    ).fetchall()
    pinned_set = {(p["category"], p["code"]) for p in pinned}

    df = get_items()
    today = date.today()
    from_dt = (today - timedelta(days=90)).isoformat()

    rows = ""
    idx = 1
    for _, it in df.iterrows():
        cat  = it["category"].upper()
        code = it["code"]
        name = it["name"]

        r = cur.execute("""
            SELECT qty FROM user_inventory
            WHERE user=? AND category=? AND code=?
        """, (user, cat, code)).fetchone()
        stock = r["qty"] if r else 0

        r = cur.execute("""
            SELECT IFNULL(SUM(qty),0) q
            FROM user_indent_items ui
            JOIN user_indent u ON u.id=ui.indent_id
            WHERE u.user=? AND ui.code=? AND u.indent_date>=?
        """, (user, code, from_dt)).fetchone()
        cons = r["q"]

        chk = "checked" if (cat, code) in pinned_set else ""

        rows += f"""
<tr class="item-row" data-cat="{cat}" data-index="{idx}">
<td><input type="checkbox" class="pin-box" name="pin[]" value="{cat}|{code}" {chk}></td>
<td>{idx}</td>
<td>{cat}</td>
<td>{code}</td>
<td style="text-align:left">{name}</td>
<td><input name="qty[]" class="qty"></td>
<td><input name="stock[]" value="{stock}" readonly class="ro"></td>
<td><input name="cons[]" value="{cons}" readonly class="ro"></td>
<td class="ro">—</td>
<td class="ro">—</td>
<input type="hidden" name="category[]" value="{cat}">
<input type="hidden" name="code[]" value="{code}">
<input type="hidden" name="name[]" value="{name}">
</tr>
"""
        idx += 1

    con.close()

    # ================= HTML =================
    html = """
<!DOCTYPE html>
<html>
<head>
<title>Demand Letter</title>
<style>
body{font-family:Arial;background:#f4f6f9}
.container{padding:20px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{border:1px solid #999;padding:6px;text-align:center}
th{background:#003d80;color:white}
.qty{width:70px}
.ro{width:70px;background:#eee;border:none}
.item-row.pinned{background:#fff7cc}
</style>
</head>

<body>
<div class="container">
<h2>📄 Central Store Demand Letter</h2>

<form method="post">
Letter No:
<input name="letter_no" required>

<table id="itemTable">
<tr>
<th>✔</th><th>#</th><th>Cat</th><th>Code</th><th>Name</th>
<th>Demand</th><th>Stock</th><th>Last 3M</th>
<th>1st</th><th>2nd</th>
</tr>

{{ROWS}}

<tbody id="manualRows">
{{MANUAL}}
<tr>
<td></td>
<td>*</td>
<td><input name="m_category[]"></td>
<td></td>
<td style="text-align:left"><input name="m_name[]" style="width:100%"></td>
<td><input name="m_qty[]" class="qty"></td>
<td><input name="m_stock[]" class="qty"></td>
<td><input name="m_cons[]" class="qty"></td>
<td class="ro">—</td>
<td class="ro">—</td>
</tr>
</tbody>
</table>

<button type="button" onclick="addManualRow()">➕ Add More Item</button>
<br><br>

<button type="submit">💾 Save Demand</button>
<span>{{MSG}}</span>
</form>

<a href="/user">⬅ Back</a>
</div>

<script>
const table = document.getElementById("itemTable");

/* 🔑 Always fetch ONLY Excel rows (item-row) */
function getExcelRows(){
  return Array.from(document.querySelectorAll(".item-row"));
}

function sortExcelOrder(){
  const rows = getExcelRows();
  rows.sort((a,b)=>parseInt(a.dataset.index)-parseInt(b.dataset.index))
      .forEach(r=>table.appendChild(r));
}

function sortByCategoryPinned(){
  const rows = getExcelRows();

  const pinned = rows.filter(r => r.querySelector(".pin-box").checked);
  const unpinned = rows.filter(r => !r.querySelector(".pin-box").checked);

  const catMap = {};
  pinned.forEach(r=>{
    const c = r.dataset.cat;
    if(!catMap[c]) catMap[c] = [];
    catMap[c].push(r);
  });

  const cats = Object.keys(catMap).sort();
  let finalRows = [];

  cats.forEach(c=>{
    catMap[c]
      .sort((a,b)=>parseInt(a.dataset.index)-parseInt(b.dataset.index))
      .forEach(r=>{
        r.classList.add("pinned");
        finalRows.push(r);
      });
  });

  unpinned
    .sort((a,b)=>parseInt(a.dataset.index)-parseInt(b.dataset.index))
    .forEach(r=>{
      r.classList.remove("pinned");
      finalRows.push(r);
    });

  finalRows.forEach(r=>table.appendChild(r));
}

/* pin checkbox change */
document.querySelectorAll(".pin-box").forEach(cb=>{
  cb.addEventListener("change", ()=>{
    if(document.querySelector(".pin-box:checked")){
      sortByCategoryPinned();
    }else{
      sortExcelOrder();
    }
  });
});

/* initial load */
if(document.querySelector(".pin-box:checked")){
  sortByCategoryPinned();
}else{
  sortExcelOrder();
}

/* manual row add (NO effect on sorting) */
function addManualRow(){
  const tbody = document.getElementById("manualRows");
  const r = tbody.rows[tbody.rows.length-1].cloneNode(true);
  r.querySelectorAll("input").forEach(i=>i.value="");
  tbody.appendChild(r);
}
</script>

</body>
</html>
"""

    return html.replace("{{ROWS}}", rows)\
               .replace("{{MANUAL}}", manual_rows)\
               .replace("{{MSG}}", msg)





@app.route("/user/demand_letter_detail")
def user_demand_letter_detail():
    user = session.get("user")
    if not user:
        return redirect("/login")

    con = db()
    cur = con.cursor()

    letters = cur.execute("""
        SELECT *
        FROM demand_letter
        WHERE user=?
        ORDER BY id DESC
    """, (user,)).fetchall()

    sections = ""

    for l in letters:
        items = cur.execute("""
            SELECT *
            FROM demand_letter_items
            WHERE letter_id=?
            ORDER BY
              category ASC,
              CASE WHEN code='' THEN 2 ELSE 1 END,
              COALESCE(NULLIF(code,''), name) ASC
        """, (l["id"],)).fetchall()

        trs = ""
        for i, it in enumerate(items, 1):
            trs += f"""
<tr>
  <td>{i}</td>
  <td>{it['category']}</td>
  <td>{it['code'] or ""}</td>
  <td style="text-align:left">{it['name']}</td>
  <td>{it['demand_qty']}</td>
  <td>{it['stock_at_time']}</td>
  <td>{it['last_3m_consumption']}</td>
  <td>{it['issue_1st'] or "NA"}</td>
  <td>{it['issue_2nd'] or "NA"}</td>
</tr>
"""

        sections += f"""
<div class="card" id="demand_{l['id']}">
  <div class="head">
    <h3>
      Letter No: {l['letter_no']} |
      Date: {l['letter_date']} |
      Status: <b>{l['status']}</b>
    </h3>

    <div>
      <button onclick="printSection('demand_{l['id']}')">🖨️</button>

      {'<a href="/user/demand_letter/send/'+str(l['id'])+'">📤 Send</a>' if l['status']=='draft' else ''}

      <a href="/user/demand_letter/delete/{l['id']}"
         onclick="return confirm('Delete this demand?')"
         style="color:red">❌</a>
    </div>
  </div>

  <table>
    <tr>
      <th>#</th>
      <th>Cat</th>
      <th>Code</th>
      <th>Name</th>
      <th>Demand</th>
      <th>Stock</th>
      <th>Last 3M</th>
      <th>1st Turn</th>
      <th>2nd Turn</th>
    </tr>
    {trs}
  </table>
</div>
"""

    con.close()

    return f"""
<!DOCTYPE html>
<html>
<head>
<title>Demand Detail</title>
<style>
body{{font-family:Arial;background:#f4f6f9}}
.container{{padding:20px}}
.card{{background:white;padding:12px;margin-bottom:20px;
       border-radius:8px;box-shadow:0 0 8px #aaa}}
.head{{display:flex;justify-content:space-between;align-items:center}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{border:1px solid #000;padding:6px;text-align:center}}
th{{background:#003d80;color:white}}
button{{cursor:pointer}}
</style>
</head>

<body>
<div class="container">
<h2>📄 Central Store Demand Detail</h2>

<a href="/user/demand_letter">➕ New Demand</a> |
<a href="/user">⬅ Back</a>

<br><br>

{sections}
</div>

<script>
function printSection(id){{
  var c=document.getElementById(id).innerHTML;
  var w=window.open('','','width=900,height=600');
  w.document.write('<html><head><title>Print</title>');
  w.document.write('<style>');
  w.document.write('table{{width:100%;border-collapse:collapse;font-size:12px}}');
  w.document.write('th,td{{border:1px solid #000;padding:5px;text-align:center}}');
  w.document.write('</style></head><body>');
  w.document.write(c);
  w.document.write('</body></html>');
  w.document.close();
  w.print();
  w.close();
}}
</script>

</body>
</html>
"""

@app.route("/user/demand_letter/view/<int:id>")
def user_demand_letter_view(id):
    user = session.get("user")
    if not user:
        return redirect("/login")

    con = db()
    cur = con.cursor()

    letter = cur.execute("""
        SELECT * FROM demand_letter
        WHERE id=? AND user=?
    """, (id, user)).fetchone()

    items = cur.execute("""
        SELECT * FROM demand_letter_items
        WHERE letter_id=?
    """, (id,)).fetchall()

    trs = ""
    for i,it in enumerate(items,1):
        trs += f"""
<tr>
<td>{i}</td>
<td>{it['category']}</td>
<td>{it['code']}</td>
<td>{it['name']}</td>
<td>{it['demand_qty']}</td>
<td>{it['stock_at_time']}</td>
<td>{it['last_3m_consumption']}</td>
<td>{it['issue_1st'] or "—"}</td>
<td>{it['issue_2nd'] or "—"}</td>
</tr>
"""

    con.close()

    return f"""
<!DOCTYPE html>
<html>
<head>
<title>Demand View</title>
<style>
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{border:1px solid #000;padding:6px;text-align:center}}
th{{background:#003d80;color:white}}
</style>
</head>
<body>

<h3>
Demand Letter No: {letter['letter_no']} |
Date: {letter['letter_date']}
</h3>

<table>
<tr>
<th>#</th><th>Cat</th><th>Code</th><th>Name</th>
<th>Demand</th><th>Stock</th><th>Last 3M</th>
<th>1st Turn</th><th>2nd Turn</th>
</tr>
{trs}
</table>

<br>
<a href="/user/demand_letter_detail">⬅ Back</a>

</body>
</html>
"""


@app.route("/user/demand_letter/send/<int:id>")
def user_demand_letter_send(id):
    user = session.get("user")
    if not user:
        return redirect("/login")

    con = db()
    cur = con.cursor()

    cur.execute("""
        UPDATE demand_letter
        SET status='sent'
        WHERE id=? AND user=?
    """, (id, user))

    con.commit()
    con.close()

    return redirect("/user/demand_letter_detail")

@app.route("/user/demand_letter/print/<int:id>")
def user_demand_letter_print(id):
    user = session.get("user")
    if not user:
        return redirect("/login")

    con = db()
    cur = con.cursor()

    letter = cur.execute("""
        SELECT * FROM demand_letter
        WHERE id=? AND user=?
    """, (id, user)).fetchone()

    items = cur.execute("""
        SELECT * FROM demand_letter_items
        WHERE letter_id=?
    """, (id,)).fetchall()

    trs = ""
    for i,it in enumerate(items,1):
        trs += f"""
<tr>
<td>{i}</td>
<td>{it['category']}</td>
<td>{it['code']}</td>
<td>{it['name']}</td>
<td>{it['demand_qty']}</td>
<td>{it['stock_at_time']}</td>
<td>{it['last_3m_consumption']}</td>
</tr>
"""

    con.close()

    return f"""
<!DOCTYPE html>
<html>
<head>
<title>Print Demand</title>
<style>
table{{width:100%;border-collapse:collapse;font-size:12px}}
th,td{{border:1px solid #000;padding:5px;text-align:center}}
</style>
</head>
<body onload="window.print()">

<h3 style="text-align:center">
RAJASTHAN STATE ROAD TRANSPORT CORPORATION<br>
Central Store Demand Letter
</h3>

<b>Depot:</b> {user}<br>
<b>Letter No:</b> {letter['letter_no']}<br>
<b>Date:</b> {letter['letter_date']}<br><br>

<table>
<tr>
<th>#</th><th>Cat</th><th>Code</th><th>Name</th>
<th>Demand</th><th>Stock</th><th>Last 3M</th>
</tr>
{trs}
</table>

<br><br>
<div style="text-align:right">
Signature ____________
</div>

</body>
</html>
"""

@app.route("/user/demand_letter/delete/<int:id>")
def demand_letter_delete(id):
    user = session.get("user")
    if not user:
        return redirect("/login")

    con = db()
    cur = con.cursor()

    cur.execute("DELETE FROM demand_letter_items WHERE letter_id=?", (id,))
    cur.execute("DELETE FROM demand_letter WHERE id=? AND user=?", (id, user))

    con.commit()
    con.close()

    return redirect("/user/demand_letter_detail")

@app.route("/admin/demand_receive")
def admin_demand_receive():
    if session.get("user") != "admin":
        return redirect("/login")

    con = db()
    cur = con.cursor()

    letters = cur.execute("""
        SELECT * FROM demand_letter
        WHERE status IN ('sent','received','closed')
        ORDER BY letter_date DESC, id DESC
    """).fetchall()

    blocks = ""
    for l in letters:
        blocks += f"""
        <tr>
          <td>{l['letter_no']}</td>
          <td>{l['user']}</td>
          <td>{l['letter_date']}</td>
          <td>{l['status']}</td>
          <td>
            <a href="/admin/demand_receive/{l['id']}">✏️ Receive</a>
            &nbsp;
            <a href="/admin/demand_print/{l['id']}">🖨️</a>
            &nbsp;
            <a href="/admin/demand_delete/{l['id']}"
               onclick="return confirm('Delete demand permanently?')"
               style="color:red;">❌</a>
          </td>
        </tr>
        """

    con.close()

    return f"""
    <html>
    <head>
    <style>
    table{{width:100%;border-collapse:collapse}}
    th,td{{border:1px solid #000;padding:6px;text-align:center}}
    th{{background:#003d80;color:white}}
    </style>
    </head>
    <body>

    <h2>📥 Receive Demand Letters</h2>

    <table>
    <tr>
      <th>Letter No</th>
      <th>Depot</th>
      <th>Date</th>
      <th>Status</th>
      <th>Action</th>
    </tr>
    {blocks}
    </table>

    <br>
    <a href="/admin">⬅ Back</a>
    </body>
    </html>
    """
@app.route("/admin/demand_delete/<int:lid>")
def admin_demand_delete(lid):
    if session.get("user") != "admin":
        return redirect("/login")

    con = db()
    cur = con.cursor()

    cur.execute("DELETE FROM demand_letter_items WHERE letter_id=?", (lid,))
    cur.execute("DELETE FROM demand_letter WHERE id=?", (lid,))

    con.commit()
    con.close()

    return redirect("/admin/demand_receive")
@app.route("/admin/demand_print/<int:lid>")
def admin_demand_print(lid):
    if session.get("user") != "admin":
        return redirect("/login")

    con = db()
    cur = con.cursor()

    letter = cur.execute(
        "SELECT * FROM demand_letter WHERE id=?", (lid,)
    ).fetchone()

    items = cur.execute("""
        SELECT * FROM demand_letter_items
        WHERE letter_id=?
    """, (lid,)).fetchall()

    trs = ""
    i = 1
    for it in items:
        trs += f"""
        <tr>
          <td>{i}</td>
          <td>{it['category']}</td>
          <td>{it['code']}</td>
          <td>{it['name']}</td>
          <td>{it['demand_qty']}</td>
          <td>{it['issue_1st'] or 'NA'}</td>
          <td>{it['issue_2nd'] or 'NA'}</td>
        </tr>
        """
        i += 1

    con.close()

    return f"""
    <html>
    <head>
    <style>
    table{{width:100%;border-collapse:collapse;font-size:12px}}
    th,td{{border:1px solid #000;padding:5px;text-align:center}}
    </style>
    </head>
    <body onload="window.print()">

    <h3 style="text-align:center;">
    RAJASTHAN STATE ROAD TRANSPORT CORPORATION<br>
    Central Store Demand Letter
    </h3>

    <p>
    Depot: <b>{letter['user']}</b><br>
    Letter No: <b>{letter['letter_no']}</b><br>
    Date: <b>{letter['letter_date']}</b>
    </p>

    <table>
    <tr>
      <th>#</th><th>Cat</th><th>Code</th><th>Name</th>
      <th>Demand</th><th>1st Turn</th><th>2nd Turn</th>
    </tr>
    {trs}
    </table>

    </body>
    </html>
    """

@app.route("/admin/demand_receive/<int:lid>", methods=["GET","POST"])
def admin_demand_receive_edit(lid):
    if session.get("user") != "admin":
        return redirect("/login")

    con = db()
    cur = con.cursor()

    # ================= POST (SAVE / FINAL) =================
    if request.method == "POST":
        action = request.form.get("action")   # save | final

        iids = request.form.getlist("iid[]")
        t1s  = request.form.getlist("t1[]")
        t2s  = request.form.getlist("t2[]")

        for i in range(len(iids)):
            t1 = t1s[i].strip() if t1s[i].strip() else "NA"
            t2 = t2s[i].strip() if t2s[i].strip() else "NA"

            cur.execute("""
                UPDATE demand_letter_items
                SET issue_1st=?, issue_2nd=?
                WHERE id=?
            """, (t1, t2, iids[i]))

        if action == "final":
            cur.execute("""
                UPDATE demand_letter
                SET status='closed', is_final=1
                WHERE id=?
            """, (lid,))
        else:
            cur.execute("""
                UPDATE demand_letter
                SET status='received'
                WHERE id=?
            """, (lid,))

        con.commit()
        con.close()
        return redirect("/admin/demand_receive")

    # ================= GET =================
    letter = cur.execute("""
        SELECT * FROM demand_letter WHERE id=?
    """, (lid,)).fetchone()

    items = cur.execute("""
        SELECT *
        FROM demand_letter_items
        WHERE letter_id=?
        ORDER BY
          category ASC,
          CASE WHEN code='' THEN 2 ELSE 1 END,
          COALESCE(NULLIF(code,''), name) ASC
    """, (lid,)).fetchall()


    is_final = True if letter["is_final"] == 1 else False

    trs = ""
    for it in items:
        ro = "readonly" if is_final else ""
        trs += f"""
<tr>
<td>{it['category']}</td>
<td>{it['code']}</td>
<td style="text-align:left">{it['name']}</td>
<td>{it['demand_qty']}</td>

<td>
  <input name="t1[]" value="{it['issue_1st'] or ''}" {ro}>
</td>
<td>
  <input name="t2[]" value="{it['issue_2nd'] or ''}" {ro}>
</td>

<input type="hidden" name="iid[]" value="{it['id']}">
</tr>
"""

    con.close()

    final_btn = ""
    if not is_final:
        final_btn = """
        <button type="submit" name="action" value="final"
        onclick="return confirm('Final submit ke baad edit possible nahi hoga. Continue?')">
        🔒 Final Submit
        </button>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
<title>Receive Demand</title>
<style>
body{{font-family:Arial;background:#f4f6f9}}
.container{{padding:20px}}
table{{width:100%;border-collapse:collapse}}
th,td{{border:1px solid #000;padding:6px;text-align:center}}
th{{background:#003d80;color:white}}
input{{width:80px;text-align:center}}
</style>
</head>

<body>
<div class="container">

<h2>📥 Receive Demand</h2>

<b>Depot:</b> {letter['user']} |
<b>Letter No:</b> {letter['letter_no']} |
<b>Status:</b> {letter['status']}

<form method="post">
<table>
<tr>
<th>Cat</th><th>Code</th><th>Name</th>
<th>Demand</th><th>1st Turn</th><th>2nd Turn</th>
</tr>
{trs}
</table>

<br>

<button type="submit" name="action" value="save">💾 Submit Issue</button>
{final_btn}

</form>

<br>
<a href="/admin/demand_receive">⬅ Back</a>

</div>
</body>
</html>
"""







from datetime import date, timedelta

@app.route("/user/others/dead-stock", methods=["GET", "POST"])
def user_dead_stock():
    user = session.get("user")
    if not user:
        return redirect("/login")

    # ---------- DAYS INPUT ----------
    try:
        days = int(request.form.get("days", 30))
    except:
        days = 30

    from_dt = (date.today() - timedelta(days=days)).isoformat()

    con = db()
    cur = con.cursor()

    # ---------- CORE LOGIC ----------
    # 1. Item ka current stock > 0
    # 2. Last X din me qty < 0 (issue) NA hua ho
    rows = cur.execute("""
        SELECT
            category,
            code,
            name,
            SUM(qty) AS qty
        FROM user_stock_ledger
        WHERE user=?
        GROUP BY category, code, name
        HAVING qty > 0
        AND code NOT IN (
            SELECT DISTINCT code
            FROM user_stock_ledger
            WHERE user=?
            AND qty < 0
            AND entry_date >= ?
        )
        ORDER BY name
    """, (user, user, from_dt)).fetchall()

    con.close()

    # ---------- TABLE ROWS ----------
    trs = ""
    for i, r in enumerate(rows, 1):
        trs += f"""
<tr>
  <td>{i}</td>
  <td>{r['category']}</td>
  <td>{r['code']}</td>
  <td style="text-align:left">{r['name']}</td>
  <td>{r['qty']}</td>
</tr>
"""

    if not trs:
        trs = "<tr><td colspan='5'>❌ No Dead Stock Found</td></tr>"

    # ---------- HTML ----------
    return f"""
<!DOCTYPE html>
<html>
<head>
<title>User Dead Stock</title>
<style>
body{{font-family:Arial;background:#f4f6f9}}
.container{{padding:20px}}
h2{{color:#003d80}}

.filter{{margin-bottom:10px}}
.filter input{{width:60px;padding:4px}}
.filter button{{
  padding:5px 10px;
  background:#003d80;
  color:white;
  border:none;
  border-radius:4px;
  cursor:pointer
}}

table{{width:100%;border-collapse:collapse;font-size:14px}}
th,td{{border:1px solid #999;padding:6px;text-align:center}}
th{{background:#003d80;color:white}}

.back{{text-decoration:none;font-weight:bold;color:#003d80}}
</style>
</head>

<body>
<div class="container">

<a class="back" href="/user">⬅ Back</a>
<h2>🧊 Dead Stock – Depot: {user}</h2>

<div class="filter">
<form method="post">
Dead for last
<input name="days" value="{days}"> days
<button type="submit">Show</button>
<button type="button" onclick="printPage()">🖨️ Print</button>
</form>
</div>

<table id="tbl">
<tr>
<th>#</th>
<th>Cat</th>
<th>Code</th>
<th>Item</th>
<th>Qty</th>
</tr>
{trs}
</table>

</div>

<script>
function printPage(){{
 var c=document.getElementById("tbl").outerHTML;
 var w=window.open('','','width=900,height=600');
 w.document.write('<html><head><title>Print</title>');
 w.document.write('<style>');
 w.document.write('table{{width:100%;border-collapse:collapse;font-size:12px}}');
 w.document.write('th,td{{border:1px solid #000;padding:4px;text-align:center}}');
 w.document.write('</style>');
 w.document.write('</head><body>'+c+'</body></html>');
 w.document.close();
 w.print();
}}
</script>

</body>

</html>
"""

from datetime import date, timedelta

@app.route("/admin/others/dead-stock", methods=["GET", "POST"])
def admin_dead_stock():
    if session.get("user") != "admin":
        return redirect("/login")

    # ---------- DAYS INPUT ----------
    try:
        days = int(request.form.get("days", 30))
    except:
        days = 30

    from_dt = (date.today() - timedelta(days=days)).isoformat()

    con = db()
    cur = con.cursor()

    # ---------- CORE LOGIC ----------
    # 1. Central store ka current stock > 0
    # 2. Last X din me koi challan (qty < 0) NA bana ho
    rows = cur.execute("""
        SELECT
            category,
            code,
            name,
            SUM(qty) AS qty
        FROM stock_ledger
        GROUP BY category, code, name
        HAVING qty > 0
        AND code NOT IN (
            SELECT DISTINCT ci.code
            FROM challan_items ci
            JOIN challan c ON c.id = ci.challan_id
            WHERE c.from_depot = 'admin'
            AND ci.qty > 0
            AND c.challan_date >= ?
        )
        ORDER BY name
    """, (from_dt,)).fetchall()

    con.close()

    # ---------- TABLE ROWS ----------
    trs = ""
    for i, r in enumerate(rows, 1):
        trs += f"""
<tr>
  <td>{i}</td>
  <td>{r['category']}</td>
  <td>{r['code']}</td>
  <td style="text-align:left">{r['name']}</td>
  <td>{r['qty']}</td>
</tr>
"""

    if not trs:
        trs = "<tr><td colspan='5'>❌ No Dead Stock Found</td></tr>"

    # ---------- HTML ----------
    return f"""
<!DOCTYPE html>
<html>
<head>
<title>Admin Dead Stock</title>
<style>
body{{font-family:Arial;background:#f4f6f9}}
.container{{padding:20px}}
h2{{color:#800000}}

.filter{{margin-bottom:10px}}
.filter input{{width:60px;padding:4px}}
.filter button{{
  padding:5px 10px;
  background:#800000;
  color:white;
  border:none;
  border-radius:4px;
  cursor:pointer
}}

table{{width:100%;border-collapse:collapse;font-size:14px}}
th,td{{border:1px solid #999;padding:6px;text-align:center}}
th{{background:#800000;color:white}}

.back{{text-decoration:none;font-weight:bold;color:#800000}}
</style>
</head>

<body>
<div class="container">

<a class="back" href="/admin">⬅ Back</a>
<h2>🧊 Dead Stock – CENTRAL STORE</h2>

<div class="filter">
<form method="post">
Dead for last
<input name="days" value="{days}"> days
<button type="submit">Show</button>
<button type="button" onclick="printPage()">🖨️ Print</button>
</form>
</div>

<table id="tbl">
<tr>
<th>#</th>
<th>Cat</th>
<th>Code</th>
<th>Item</th>
<th>Qty</th>
</tr>
{trs}
</table>

</div>

<script>
function printPage(){{
 var c=document.getElementById("tbl").outerHTML;
 var w=window.open('','','width=900,height=600');
 w.document.write('<html><head><title>Print</title>');
 w.document.write('<style>');
 w.document.write('table{{width:100%;border-collapse:collapse;font-size:12px}}');
 w.document.write('th,td{{border:1px solid #000;padding:4px;text-align:center}}');
 w.document.write('</style>');
 w.document.write('</head><body>'+c+'</body></html>');
 w.document.close();
 w.print();
}}
</script>

</body>
</html>
"""




@app.route("/user/others/mis", methods=["GET","POST"])
def user_mis():
    user = session.get("user")
    if not user:
        return redirect("/login")

    from_date = request.form.get("from_date")
    to_date   = request.form.get("to_date")

    rows = []

    if from_date and to_date:
        con = db()
        cur = con.cursor()

        rows = cur.execute("""
            SELECT
                g.grs_no,
                g.grs_date,
                SUM(i.total) AS total_amount
            FROM user_grs g
            JOIN user_grs_items i ON i.grs_id = g.id
            WHERE g.user=?
            AND g.grs_date BETWEEN ? AND ?
            GROUP BY g.grs_no, g.grs_date
            ORDER BY g.grs_date, g.grs_no
        """, (user, from_date, to_date)).fetchall()

        con.close()

    trs = ""
    for i,r in enumerate(rows,1):
        amt = round(r["total_amount"] or 0, 2)
        trs += f"""
<tr>
<td>{i}</td>
<td>{r['grs_no']}</td>
<td>{r['grs_date']}</td>
<td style="text-align:right;">₹ {amt:,.2f}</td>
</tr>
"""

    if from_date and to_date and not trs:
        trs = "<tr><td colspan='4'>❌ No GRS Found</td></tr>"

    return f"""
<!DOCTYPE html>
<html>
<head>
<title>User MIS - GRS Value</title>
<style>
body{{font-family:Arial;background:#f4f6f9}}
.container{{padding:20px}}
h2{{color:#003d80}}

.filter input{{padding:5px}}
.filter button{{
  padding:6px 12px;
  background:#003d80;
  color:white;
  border:none;
  border-radius:4px;
  cursor:pointer
}}

table{{width:100%;border-collapse:collapse;margin-top:15px}}
th,td{{border:1px solid #999;padding:6px;text-align:center}}
th{{background:#003d80;color:white}}

.back{{text-decoration:none;font-weight:bold;color:#003d80}}
</style>
</head>

<body>
<div class="container">

<a class="back" href="/user">⬅ Back</a>
<h2>📊 MIS – GRS Receive Value (User)</h2>

<form method="post" class="filter">
From:
<input type="date" name="from_date" value="{from_date or ''}">
To:
<input type="date" name="to_date" value="{to_date or ''}">
<button type="submit">Show</button>
<button type="button" onclick="printPage()">🖨️ Print</button>
</form>

<table id="tbl">
<tr>
<th>#</th>
<th>GRS No</th>
<th>GRS Date</th>
<th>Total Amount (₹)</th>
</tr>
{trs}
</table>

</div>

<script>
function printPage(){{
 var c=document.getElementById("tbl").outerHTML;
 var w=window.open('','','width=900,height=600');
 w.document.write('<html><head><title>Print</title>');
 w.document.write('<style>table{{width:100%;border-collapse:collapse;font-size:12px}} th,td{{border:1px solid #000;padding:4px;text-align:center}}</style>');
 w.document.write('</head><body>'+c+'</body></html>');
 w.document.close(); w.print();
}}
</script>

</body>
</html>
"""


@app.route("/admin/others/mis", methods=["GET","POST"])
def admin_mis():
    if session.get("user") != "admin":
        return redirect("/login")

    from_date = request.form.get("from_date")
    to_date   = request.form.get("to_date")

    rows = []

    if from_date and to_date:
        con = db()
        cur = con.cursor()

        rows = cur.execute("""
            SELECT
                g.grs_no,
                g.grs_date,
                SUM(i.total) AS total_amount
            FROM grs g
            JOIN grs_items i ON i.grs_id = g.id
            WHERE g.grs_date BETWEEN ? AND ?
            GROUP BY g.grs_no, g.grs_date
            ORDER BY g.grs_date, g.grs_no
        """, (from_date, to_date)).fetchall()

        con.close()

    trs = ""
    for i,r in enumerate(rows,1):
        amt = round(r["total_amount"] or 0, 2)
        trs += f"""
<tr>
<td>{i}</td>
<td>{r['grs_no']}</td>
<td>{r['grs_date']}</td>
<td style="text-align:right;">₹ {amt:,.2f}</td>
</tr>
"""

    if from_date and to_date and not trs:
        trs = "<tr><td colspan='4'>❌ No GRS Found</td></tr>"

    return f"""
<!DOCTYPE html>
<html>
<head>
<title>Admin MIS - GRS Value</title>
<style>
body{{font-family:Arial;background:#f4f6f9}}
.container{{padding:20px}}
h2{{color:#800000}}

.filter input{{padding:5px}}
.filter button{{
  padding:6px 12px;
  background:#800000;
  color:white;
  border:none;
  border-radius:4px;
  cursor:pointer
}}

table{{width:100%;border-collapse:collapse;margin-top:15px}}
th,td{{border:1px solid #999;padding:6px;text-align:center}}
th{{background:#800000;color:white}}

.back{{text-decoration:none;font-weight:bold;color:#800000}}
</style>
</head>

<body>
<div class="container">

<a class="back" href="/admin">⬅ Back</a>
<h2>📊 MIS – GRS Receive Value (Admin)</h2>

<form method="post" class="filter">
From:
<input type="date" name="from_date" value="{from_date or ''}">
To:
<input type="date" name="to_date" value="{to_date or ''}">
<button type="submit">Show</button>
<button type="button" onclick="printPage()">🖨️ Print</button>
</form>

<table id="tbl">
<tr>
<th>#</th>
<th>GRS No</th>
<th>GRS Date</th>
<th>Total Amount (₹)</th>
</tr>
{trs}
</table>

</div>

<script>
function printPage(){{
 var c=document.getElementById("tbl").outerHTML;
 var w=window.open('','','width=900,height=600');
 w.document.write('<html><head><title>Print</title>');
 w.document.write('<style>table{{width:100%;border-collapse:collapse;font-size:12px}} th,td{{border:1px solid #000;padding:4px;text-align:center}}</style>');
 w.document.write('</head><body>'+c+'</body></html>');
 w.document.close(); w.print();
}}
</script>

</body>
</html>
"""








def detect_intent(q):
    q = q.lower()

    intent = {
        "type": "stock",   # stock | challan | grs | issue
        "depot": None,
        "item": None
    }

    # ---- DEPOT DETECTION ----
    for d in DEPOTS:   # e.g. ["AJMER","DAUSA","KOTA"]
        if d.lower() in q:
            intent["depot"] = d
            break

    # ---- CHALLAN DETECTION ----
    if "challan" in q:
        intent["type"] = "challan"
        return intent   # ⛔ stock logic skip

    # ---- GRS DETECTION ----
    if "grs" in q or "receive" in q or "aaya" in q:
        intent["type"] = "grs"
        return intent

    # ---- ITEM DETECTION ----
    if "bulb" in q:
        intent["item"] = "bulb"

    # default = stock
    return intent

def build_sql(intent):

    # ---------- CHALLAN ----------
    if intent["type"] == "challan":
        return f"""
        SELECT challan_no, challan_date
        FROM challan
        WHERE depot = '{intent["depot"]}'
        ORDER BY challan_date DESC
        """

    # ---------- GRS ----------
    if intent["type"] == "grs":
        return f"""
        SELECT grs_no, grs_date
        FROM user_grs
        WHERE user = '{intent["depot"]}'
        ORDER BY grs_date DESC
        """

    # ---------- STOCK ----------
    sql = """
    SELECT
      user AS depot,
      category,
      code,
      name,
      SUM(qty) AS stock
    FROM user_inventory
    WHERE 1=1
    """

    if intent["depot"]:
        sql += f" AND user='{intent['depot']}'"

    if intent["item"]:
        sql += f" AND name LIKE '%{intent['item']}%'"

    sql += """
    GROUP BY user, category, code, name
    HAVING SUM(qty) > 0
    ORDER BY name
    """

    return sql





def clean_sql(text):
    text = text.strip()
    text = text.replace("```sql", "").replace("```", "")
    if text.lower().startswith("sql"):
        text = text.split(":", 1)[-1]
    return text.strip()


def is_safe_sql(sql):
    s = sql.lower().strip()

    if not s.startswith("select"):
        return False

    banned = [
        "insert", "update", "delete",
        "drop", "alter", "truncate",
        "pragma", "attach", "detach"
    ]
    return not any(b in s for b in banned)
def human_answer(rows):
    if not rows:
        return "❌ Koi data nahi mila"

    out = ""
    for r in rows:
        out += f"📦 {r['depot']} → {r['name']} ({r['code']}): {r['stock']}\n"
    return out


import google.generativeai as genai

genai.configure(api_key="AIzaSyCq4QLN83ay4CvEvIjpIU6CFVmJKKsdHoU")

model = genai.GenerativeModel("gemini-2.5-flash")


def clean_sql(text):
    text = text.strip()
    text = text.replace("```sql", "").replace("```", "")
    if text.lower().startswith("sql"):
        text = text.split(":", 1)[-1]
    return text.strip()


def is_safe_sql(sql):
    s = sql.lower()

    banned = [
        "insert", "update", "delete",
        "drop", "alter", "truncate",
        "pragma", "attach", "detach"
    ]

    if not s.strip().startswith("select"):
        return False

    for b in banned:
        if f" {b} " in s:
            return False

    return True



@app.route("/admin/others/ai", methods=["GET","POST"])
def admin_ai():
    if session.get("user") != "admin":
        return redirect("/login")

    question = request.form.get("question", "")
    answer = "❓ Kuch poochho. Example: dausa me kitne bulb hai"

    if question:
        prompt = f"""
You are an expert SQLite database assistant.

IMPORTANT DATABASE SCHEMA (FOLLOW STRICTLY):

inventory(
  category TEXT,
  code TEXT,
  name TEXT,
  qty REAL
)

user_inventory(
  user TEXT,
  category TEXT,
  code TEXT,
  name TEXT,
  qty REAL
)

grs(grs_no, grs_date)
grs_items(grs_id, category, code, name, qty, price, total)

user_grs(grs_no, grs_date, user)
user_grs_items(grs_id, category, code, name, qty, price, total)

challan(challan_no, challan_date, depot, from_depot)
challan_items(challan_id, category, code, name, qty, price, total)

user_indent(indent_no, indent_date, user)
user_indent_items(indent_id, category, code, name, qty)

RULES (VERY IMPORTANT):
- Column name is ALWAYS `qty` (NOT quantity)
- Amount column is `total`
- Generate ONLY ONE SQL SELECT query
- If question asks "kitne", "total", "quantity" → USE SUM(qty)
- NEVER use COUNT for stock quantity
- Stock quantity is ALWAYS SUM(qty)
- NEVER use COUNT() for stock
- If question includes "kitne", "stock", "quantity" → use SUM(qty)
- If asking item list → SELECT code, name, SUM(qty)

- No explanation, ONLY SQL
- Read-only (no insert/update/delete)
- Use LIKE '%bulb%' for item name search

QUESTION:
{question}
"""

        try:
            intent = detect_intent(question)
            sql = build_sql(intent)


            if is_safe_sql(sql):
                con = db()
                cur = con.cursor()
                rows = cur.execute(sql).fetchall()
                con.close()

                if rows:
                    answer = "ANSWER:\n"
                    for r in rows:
                        answer += str(dict(r)) + "\n"
                else:
                    answer = "No data found"

            else:
                answer = "❌ Unsafe SQL blocked"

        except Exception as e:
            answer = f"AI Error: {e}"

    return f"""
<!DOCTYPE html>
<html>
<head>
<title>Admin AI</title>
<style>
body{{font-family:Arial;background:#f4f6f9}}
.container{{padding:20px}}
textarea{{width:100%;height:120px;padding:10px}}
button{{padding:8px 15px;background:#800000;color:white;border:none}}
pre{{background:white;padding:12px;white-space:pre-wrap}}
.back{{font-weight:bold;text-decoration:none;color:#800000}}
</style>
</head>
<body>

<div class="container">
<a class="back" href="/admin">⬅ Back</a>
<h2>🤖 Admin AI (AI + Database)</h2>

<form method="post">
<textarea name="question" placeholder="Examples:
- dausa me kitne bulb hai
- ajmer depot me last 5 din me kya aaya
- sab depots me kitne bulb hai
- sabse zyada issue hone wala item kaunsa hai">{question}</textarea>
<br><br>
<button>Ask AI</button>
</form>

<pre>{answer}</pre>
</div>

</body>
</html>
"""





def detect_user_intent(q, user):
    q = q.lower()

    intent = {
        "type": "stock",   # stock | grs | grs_items | challan
        "user": user,
        "item": None,
        "grs_no": None
    }

    # -------- GRS --------
    if "grs" in q:
        intent["type"] = "grs"

        # GRS number capture (GRS-123)
        import re
        m = re.search(r"grs[-\s]*(\d+)", q)
        if m:
            intent["type"] = "grs_items"
            intent["grs_no"] = "GRS-" + m.group(1)

        return intent

    # -------- CHALLAN / ISSUE --------
    if "challan" in q or "issue" in q or "nikla" in q:
        intent["type"] = "challan"
        return intent

    # -------- ITEM --------
    if "battery" in q or "batri" in q:
        intent["item"] = "battery"
    elif "bulb" in q:
        intent["item"] = "bulb"
    elif "starter" in q:
        intent["item"] = "starter"

    return intent
def build_user_sql(intent):

    # ---------- USER GRS ----------
    if intent["type"] == "grs":
        return f"""
        SELECT grs_no, grs_date
        FROM user_grs
        WHERE user = '{intent["user"]}'
        ORDER BY grs_date DESC
        """

    # ---------- USER GRS ITEMS ----------
    if intent["type"] == "grs_items":
        return f"""
        SELECT gi.category, gi.code, gi.name, gi.qty
        FROM user_grs_items gi
        JOIN user_grs g ON g.id = gi.grs_id
        WHERE g.user = '{intent["user"]}'
          AND g.grs_no = '{intent["grs_no"]}'
        ORDER BY gi.name
        """

    # ---------- USER CHALLAN ----------
    if intent["type"] == "challan":
        return f"""
        SELECT indent_no, indent_date
        FROM user_indent
        WHERE user = '{intent["user"]}'
        ORDER BY indent_date DESC
        """

    # ---------- USER STOCK (FIXED) ----------
    sql = f"""
    SELECT
      category,
      code,
      name,
      SUM(qty) AS stock
    FROM user_inventory
    WHERE user = '{intent["user"]}'
    """

    # ⭐⭐⭐ ITEM FILTER (MOST IMPORTANT)
    if intent["item"]:
        sql += f" AND name LIKE '%{intent['item']}%'"

    sql += """
    GROUP BY category, code, name
    HAVING SUM(qty) > 0
    ORDER BY name
    """

    return sql


@app.route("/user/others/ai", methods=["GET","POST"])
def user_ai():
    user = session.get("user")
    if not user:
        return redirect("/login")

    question = request.form.get("question", "")
    answer = "❓ Kuch poochho. Example: mera grs no. kitna hai"

    if question:
        try:
            intent = detect_user_intent(question, user)
            sql = build_user_sql(intent)

            if is_safe_sql(sql):
                con = db()
                cur = con.cursor()
                rows = cur.execute(sql).fetchall()
                con.close()

                if rows:
                    answer = "ANSWER:\n"
                    for r in rows:
                        answer += str(dict(r)) + "\n"
                else:
                    answer = "No data found"
            else:
                answer = "❌ Unsafe SQL blocked"

        except Exception as e:
            answer = f"Error: {e}"

    return f"""
<!DOCTYPE html>
<html>
<head>
<title>User AI</title>
<style>
body{{font-family:Arial;background:#f4f6f9}}
.container{{padding:20px}}
textarea{{width:100%;height:120px;padding:10px}}
button{{padding:8px 15px;background:#003d80;color:white;border:none}}
pre{{background:white;padding:12px;white-space:pre-wrap}}
</style>
</head>
<body>

<div class="container">
<a href="/user">⬅ Back</a>
<h2>🤖 AI Assistant (Your Depot)</h2>

<form method="post">
<textarea name="question" placeholder="Examples:
- mera grs no. kitna hai
- mera last grs kaunsa hai
- mere paas kitne bulb hai
- maine kaunsa challan banaya">{question}</textarea>
<br><br>
<button>Ask AI</button>
</form>

<pre>{answer}</pre>

</div>
</body>
</html>
"""




import os

if __name__ == "__main__":
    init_db()

    port = int(os.environ.get("PORT", 10000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )


