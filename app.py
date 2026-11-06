"""
CampusFix - Campus Service Request System (prototype)
Course: Software Construction and Development (SW315) - Lab 16 CEP

Students submit and track campus facility requests; maintenance staff
process the queue; admins manage categories. Single-file Flask + SQLite.

Run:  python app.py   ->  http://127.0.0.1:5000
Demo accounts (seeded automatically):
  student:  ali@student.uet.edu.pk / ali123
  staff:    staff@uet.edu.pk / staff123
"""
import sqlite3
from datetime import datetime
from flask import (Flask, g, redirect, render_template_string, request,
                   session, url_for)

app = Flask(__name__)
app.secret_key = "campusfix-demo-key"        # demo only; use env var in production
DB = "campusfix.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS user(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
  password TEXT NOT NULL,                    -- prototype only; hashing in hardening step
  role TEXT NOT NULL CHECK(role IN ('student','staff','admin')));
CREATE TABLE IF NOT EXISTS category(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS request(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  category_id INTEGER NOT NULL REFERENCES category(id),
  location TEXT NOT NULL,
  description TEXT NOT NULL,
  priority TEXT NOT NULL CHECK(priority IN ('low','medium','high')),
  status TEXT NOT NULL DEFAULT 'Submitted',
  created_at TEXT NOT NULL,
  student_id INTEGER NOT NULL REFERENCES user(id),
  staff_id INTEGER REFERENCES user(id));
CREATE TABLE IF NOT EXISTS status_update(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id INTEGER NOT NULL REFERENCES request(id),
  staff_id INTEGER NOT NULL REFERENCES user(id),
  old_status TEXT NOT NULL, new_status TEXT NOT NULL,
  note TEXT, timestamp TEXT NOT NULL);
"""

PAGE = """<!doctype html><html><head><title>CampusFix</title>
<style>body{font-family:Arial;margin:2em auto;max-width:720px}
table{border-collapse:collapse;width:100%%}td,th{border:1px solid #999;padding:6px}
input,select,textarea{width:100%%;margin-bottom:8px;padding:6px}
.badge{padding:2px 8px;border-radius:4px;background:#ddd}
.err{color:#b00}</style></head><body>
<h2>CampusFix %s</h2>%s
<p><a href="/">Home</a> | <a href="/logout">Logout (%s)</a></p></body></html>"""


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    d = g.pop("db", None)
    if d:
        d.close()


@app.route("/health")
def health():
    return "ok", 200


@app.route("/register", methods=["GET", "POST"])
def register():
    msg = ""
    if request.method == "POST":
        name, email = request.form["name"].strip(), request.form["email"].strip()
        pw, role = request.form["password"], request.form.get("role", "student")
        if not (name and email and pw):
            msg = "All fields are required."
        elif db().execute("SELECT 1 FROM user WHERE email=?", (email,)).fetchone():
            msg = "Email already registered."
        else:
            db().execute("INSERT INTO user(name,email,password,role) VALUES(?,?,?,?)",
                         (name, email, pw, role if role in ("student", "staff") else "student"))
            db().commit()
            return redirect(url_for("login"))
    return PAGE % ("Register", _form(msg), "guest")


def _form(msg=""):
    err = "<p class='err'>%s</p>" % msg if msg else ""
    return err + ("<form method='post'>Name<input name='name'>Email<input name='email'>"
                  "Password<input type='password' name='password'>"
                  "Role<select name='role'><option>student</option><option>staff</option></select>"
                  "<button>Go</button></form>")


@app.route("/login", methods=["GET", "POST"])
def login():
    msg = ""
    if request.method == "POST":
        row = db().execute("SELECT * FROM user WHERE email=? AND password=?",
                           (request.form["email"], request.form["password"])).fetchone()
        if row:
            session["uid"], session["name"], session["role"] = row["id"], row["name"], row["role"]
            return redirect(url_for("index"))
        msg = "Invalid email or password."
    return PAGE % ("Login", ("<p class='err'>%s</p>" % msg if msg else "") +
                   "<form method='post'>Email<input name='email'>"
                   "Password<input type='password' name='password'><button>Login</button></form>",
                   "guest")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    if "uid" not in session:
        return redirect(url_for("login"))
    return PAGE % ("Home",
                   ("<p><a href='/submit'>Submit new request</a> | <a href='/my'>My requests</a></p>"
                    if session["role"] == "student" else
                    "<p><a href='/queue'>Request queue</a></p>"),
                   session["name"])


@app.route("/submit", methods=["GET", "POST"])
def submit():
    if session.get("role") != "student":
        return PAGE % ("Denied", "<p class='err'>Only students can submit requests.</p>",
                       session.get("name", "guest"))
    msg = ""
    if request.method == "POST":
        f = request.form
        if not (f["title"].strip() and f["location"].strip() and f["description"].strip()):
            msg = "All fields are required."
        else:
            cur = db().execute(
                "INSERT INTO request(title,category_id,location,description,priority,"
                "status,created_at,student_id) VALUES(?,?,?,?,?,'Submitted',?,?)",
                (f["title"], f["category"], f["location"], f["description"],
                 f["priority"], datetime.now().isoformat(timespec="seconds"), session["uid"]))
            db().commit()
            return PAGE % ("Submitted", "<p>Request <b>#%d</b> created successfully.</p>"
                           % cur.lastrowid, session["name"])
    opts = "".join("<option value='%d'>%s</option>" % (c["id"], c["name"])
                   for c in db().execute("SELECT * FROM category ORDER BY name"))
    form = ("<p class='err'>%s</p><form method='post'>Title<input name='title'>"
            "Category<select name='category'>%s</select>"
            "Location (hostel/lab/room)<input name='location'>"
            "Description<textarea name='description' rows='3'></textarea>"
            "Priority<select name='priority'><option>low</option><option>medium</option>"
            "<option>high</option></select><button>Submit</button></form>" % (msg, opts))
    return PAGE % ("New request", form, session["name"])


@app.route("/my")
def my():
    rows = db().execute(
        "SELECT r.*, c.name cat FROM request r JOIN category c ON c.id=r.category_id "
        "WHERE student_id=? ORDER BY r.id DESC", (session["uid"],)).fetchall()
    body = _table(rows)
    return PAGE % ("My requests", body, session["name"])


@app.route("/queue")
def queue():
    if session.get("role") != "staff":
        return PAGE % ("Denied", "<p class='err'>Staff access only.</p>", session["name"])
    rows = db().execute(
        "SELECT r.*, c.name cat FROM request r JOIN category c ON c.id=r.category_id "
        "ORDER BY CASE r.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, r.id").fetchall()
    body = _table(rows, staff=True)
    return PAGE % ("Request queue (high priority first)", body, session["name"])


@app.route("/request/<int:rid>/update", methods=["POST"])
def update(rid):
    if session.get("role") != "staff":
        return PAGE % ("Denied", "<p class='err'>Staff access only.</p>", session["name"])
    new, note = request.form["status"], request.form["note"]
    row = db().execute("SELECT status FROM request WHERE id=?", (rid,)).fetchone()
    if row and new in ("Submitted", "In Progress", "Resolved"):
        db().execute("UPDATE request SET status=?, staff_id=? WHERE id=?",
                     (new, session["uid"], rid))
        db().execute("INSERT INTO status_update(request_id,staff_id,old_status,new_status,"
                     "note,timestamp) VALUES(?,?,?,?,?,?)",
                     (rid, session["uid"], row["status"], new, note,
                      datetime.now().isoformat(timespec="seconds")))
        db().commit()
    return redirect(url_for("queue"))


def _table(rows, staff=False):
    out = ["<table><tr><th>#</th><th>Title</th><th>Category</th><th>Location</th>"
           "<th>Priority</th><th>Status</th>"]
    if staff:
        out.append("<th>Update</th>")
    out.append("</tr>")
    for r in rows:
        out.append("<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
                   "<td><span class='badge'>%s</span></td>"
                   % (r["id"], r["title"], r["cat"], r["location"], r["priority"], r["status"]))
        if staff:
            out.append("<td><form method='post' action='/request/%d/update'>"
                       "<select name='status'><option>In Progress</option><option>Resolved</option>"
                       "</select><input name='note' placeholder='note'><button>Save</button>"
                       "</form></td>" % r["id"])
        out.append("</tr>")
    out.append("</table>")
    return "".join(out) or "<p>No requests yet.</p>"


def seed():
    d = sqlite3.connect(DB)
    d.executescript(SCHEMA)
    d.execute("INSERT OR IGNORE INTO category(name) VALUES('Electrical')")
    d.execute("INSERT OR IGNORE INTO category(name) VALUES('Plumbing')")
    d.execute("INSERT OR IGNORE INTO category(name) VALUES('Furniture')")
    d.execute("INSERT OR IGNORE INTO category(name) VALUES('IT / Network')")
    if not d.execute("SELECT 1 FROM user WHERE email='staff@uet.edu.pk'").fetchone():
        d.execute("INSERT INTO user(name,email,password,role) "
                  "VALUES('Helpdesk Staff','staff@uet.edu.pk','staff123','staff')")
        d.execute("INSERT INTO user(name,email,password,role) "
                  "VALUES('Ali Raza','ali@student.uet.edu.pk','ali123','student')")
    d.commit()
    d.close()


seed()

if __name__ == "__main__":
    app.run(debug=True)
