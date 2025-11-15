# app.py (Mongo-ready, corrected)
from flask import Flask, render_template, send_from_directory, session, redirect, url_for, request, jsonify
import os
import json
import datetime
import joblib
import pandas as pd
from io import StringIO
import csv

# Mongo imports
try:
    from pymongo.mongo_client import MongoClient
    from pymongo.server_api import ServerApi
except Exception:
    MongoClient = None
    ServerApi = None

# ---------- Configuration ----------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Local fallback SQLite DB (optional); kept for local dev if you want it
DB_DIR = os.path.join(BASE_DIR, "data")
SQLITE_DB_PATH = os.path.join(DB_DIR, "users.db")

app = Flask(__name__, template_folder="templates")
app.secret_key = "dev-secret-change-this"  # change for production

# ---------- MongoDB connection ----------
MONGO_URI = os.environ.get("MONGO_URI", None)
# Optionally you can build a URI here (not recommended to hardcode credentials)
# Example (not recommended): "mongodb+srv://user:password@cluster0.djel7c3.mongodb.net/student_predictor?retryWrites=true&w=majority"

DB = None
client = None
if MONGO_URI and MongoClient is not None:
    try:
        # Use ServerApi for modern clusters (optional)
        client = MongoClient(MONGO_URI, server_api=ServerApi("1"))
        # Try a ping to verify connection
        client.admin.command("ping")
        # Prefer default DB from URI if present, else use 'student_predictor'
        try:
            DB = client.get_default_database()
            if DB is None:
                DB = client["student_predictor"]
        except Exception:
            DB = client["student_predictor"]
        print("Connected to MongoDB Atlas. DB:", DB.name if DB is not None else None)
    except Exception as e:
        print("MongoDB connection failed:", e)
        DB = None
else:
    if MONGO_URI is None:
        print("MONGO_URI not set — running without MongoDB (DB will be None).")
    else:
        print("pymongo not installed; Mongo support disabled.")
    DB = None

# Collections (safe setup)
users_coll = DB.users if DB is not None else None
preds_coll = DB.predictions if DB is not None else None

def ensure_indexes():
    if DB is None:
        return
    try:
        users_coll.create_index("email", unique=True, background=True)
        users_coll.create_index("username", unique=True, background=True)
        preds_coll.create_index("user_id", background=True)
    except Exception as e:
        print("Index creation warning:", e)

# ensure indexes on startup
ensure_indexes()

# ---------- Optional: local SQLite helper (if you want fallback) ----------
def get_sqlite_conn():
    import sqlite3
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH, timeout=30, check_same_thread=False)
    # enable WAL for better concurrency
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    return conn

def init_sqlite_db():
    if DB is not None:
        return   # using Mongo DB, skip sqlite init
    import sqlite3
    conn = get_sqlite_conn()
    try:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            );
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NULL,
                input_json TEXT NOT NULL,
                predicted_role TEXT,
                confidence REAL,
                created_at TEXT NOT NULL
            );
        ''')
        conn.commit()
    finally:
        conn.close()

# initialize local sqlite only if Mongo not used
init_sqlite_db()

# ---------- Model loading (unchanged) ----------
MODEL = None
LABEL_MAP = None
FEATURE_COLUMNS = None

def try_load_model():
    global MODEL, LABEL_MAP, FEATURE_COLUMNS
    candidates = []
    try:
        for fn in os.listdir(BASE_DIR):
            if fn.lower().endswith((".pkl", ".joblib")) and ("model" in fn.lower() or "career" in fn.lower() or "prediction" in fn.lower()):
                candidates.append(fn)
    except Exception:
        pass

    if not candidates:
        print("MODEL LOAD: No candidate model files found in project root:", BASE_DIR)
    else:
        print("MODEL LOAD: Found candidate files:", candidates)

    model_loaded = False
    for fn in candidates:
        p = os.path.join(BASE_DIR, fn)
        try:
            print(f"MODEL LOAD: Attempting to load model from {p} ...")
            MODEL = joblib.load(p)
            print("MODEL LOAD: Successfully loaded model from", fn)
            model_loaded = True
            break
        except Exception as e:
            print(f"MODEL LOAD: Failed to load {fn}: {e}")

    # label mapping
    label_candidates = []
    try:
        for fn in os.listdir(BASE_DIR):
            if ("label" in fn.lower() or "mapping" in fn.lower()) and fn.lower().endswith((".pkl", ".json", ".joblib")):
                label_candidates.append(fn)
    except Exception:
        pass

    if label_candidates:
        for lf in label_candidates:
            lp = os.path.join(BASE_DIR, lf)
            try:
                if lf.lower().endswith((".pkl", ".joblib")):
                    LABEL_MAP = joblib.load(lp)
                else:
                    with open(lp, "r", encoding="utf-8") as fh:
                        LABEL_MAP = json.load(fh)
                print("LABEL LOAD: Loaded label mapping from", lf)
                break
            except Exception as e:
                print("LABEL LOAD: Failed to load", lf, ":", e)
    else:
        print("LABEL LOAD: No label_mapping file found (optional).")

    # feature_columns.json
    fc_path = os.path.join(BASE_DIR, "feature_columns.json")
    if os.path.exists(fc_path):
        try:
            with open(fc_path, "r", encoding="utf-8") as f:
                FEATURE_COLUMNS = json.load(f)
            print("FEATURES LOAD: Loaded feature_columns.json")
        except Exception as e:
            print("FEATURES LOAD: Failed to load feature_columns.json:", e)
    else:
        print("FEATURES LOAD: feature_columns.json not found (optional).")

    if not model_loaded:
        print("MODEL LOAD: No model loaded. /predict will return fallback message.")
    return

try_load_model()

# ---------- Helpers ----------
from werkzeug.security import generate_password_hash, check_password_hash

def is_admin_user(session_user):
    try:
        return session_user and session_user.get("username") and session_user.get("username").lower() == "admin"
    except Exception:
        return False

# ---------- DB action implementations (Mongo first, fallback to sqlite) ----------

def create_user(username, email, password):
    pw_hash = generate_password_hash(password)
    if DB is not None:
        try:
            res = users_coll.insert_one({"username": username, "email": email, "password_hash": pw_hash})
            return True, None
        except Exception as e:
            # duplicate key on unique index will raise
            return False, str(e)
    else:
        # fallback to sqlite
        try:
            import sqlite3
            conn = get_sqlite_conn()
            c = conn.cursor()
            c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)", (username, email, pw_hash))
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            return False, str(e)

def get_user_by_username(username_or_email):
    if DB is not None:
        row = users_coll.find_one({"$or": [{"username": username_or_email}, {"email": username_or_email}]})
        if not row:
            return None
        return (row.get("_id"), row.get("username"), row.get("email"), row.get("password_hash"))
    else:
        import sqlite3
        conn = get_sqlite_conn()
        c = conn.cursor()
        c.execute("SELECT id, username, email, password_hash FROM users WHERE username = ? OR email = ?", (username_or_email, username_or_email))
        row = c.fetchone()
        conn.close()
        return row

def save_prediction(user_id, input_obj, predicted_role, confidence=None):
    created_at = datetime.datetime.utcnow().isoformat() + "Z"
    if DB is not None:
        try:
            doc = {
                "user_id": user_id,
                "input_json": input_obj,
                "predicted_role": predicted_role,
                "confidence": confidence,
                "created_at": created_at
            }
            preds_coll.insert_one(doc)
        except Exception as e:
            print("Failed to save prediction (mongo):", e)
    else:
        try:
            import sqlite3
            conn = get_sqlite_conn()
            c = conn.cursor()
            c.execute("INSERT INTO predictions (user_id, input_json, predicted_role, confidence, created_at) VALUES (?, ?, ?, ?, ?)",
                      (user_id, json.dumps(input_obj, ensure_ascii=False), predicted_role, confidence, created_at))
            conn.commit()
            conn.close()
        except Exception as e:
            print("Failed to save prediction (sqlite):", e)

def get_user_predictions(user_id, limit=200):
    items = []
    if DB is not None:
        try:
            rows = list(preds_coll.find({"user_id": user_id}).sort([("_id", -1)]).limit(limit))
            for r in rows:
                items.append({
                    "id": str(r.get("_id")),
                    "input": r.get("input_json"),
                    "predicted_role": r.get("predicted_role"),
                    "confidence": r.get("confidence"),
                    "created_at": r.get("created_at")
                })
        except Exception as e:
            print("get_user_predictions (mongo) error:", e)
    else:
        import sqlite3
        conn = get_sqlite_conn()
        c = conn.cursor()
        c.execute("SELECT id, input_json, predicted_role, confidence, created_at FROM predictions WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
        rows = c.fetchall()
        conn.close()
        for r in rows:
            _id, input_json, predicted_role, confidence, created_at = r
            try:
                inp = json.loads(input_json)
            except Exception:
                inp = {"raw": input_json}
            items.append({
                "id": _id,
                "input": inp,
                "predicted_role": predicted_role,
                "confidence": confidence,
                "created_at": created_at
            })
    return items

# ---------- Routes ----------

@app.route("/")
def home():
    show_login = session.pop("show_login", False)
    show_signup = session.pop("show_signup", False)
    signup_error = session.pop("signup_error", None)
    login_error = session.pop("login_error", None)
    registered = session.pop("registered", None)

    return render_template(
        "home.html",
        user=session.get("user"),
        show_login=show_login,
        show_signup=show_signup,
        signup_error=signup_error,
        login_error=login_error,
        registered=registered
    )

@app.route("/career-form")
def index():
    return render_template("index.html", user=session.get("user"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html", user=session.get("user"))

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not username or not email or not password:
        session["signup_error"] = "All fields required."
        session["show_signup"] = True
        return redirect(url_for("home"))

    ok, err = create_user(username, email, password)
    if not ok:
        session["signup_error"] = "Could not create user. " + (err or "")
        session["show_signup"] = True
        return redirect(url_for("home"))

    session["registered"] = True
    session["show_login"] = True
    return redirect(url_for("home"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        registered = request.args.get("registered")
        return render_template("login.html", user=session.get("user"), registered=registered)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        session["login_error"] = "Username and password required."
        session["show_login"] = True
        return redirect(url_for("home"))

    row = get_user_by_username(username)
    if not row:
        session["login_error"] = "User not found."
        session["show_login"] = True
        return redirect(url_for("home"))

    uid, uname, email, pw_hash = row
    if not check_password_hash(pw_hash, password):
        session["login_error"] = "Invalid password."
        session["show_login"] = True
        return redirect(url_for("home"))

    session["user"] = {"id": str(uid), "username": uname, "email": email}
    if uname.lower() == "admin":
        return redirect(url_for("admin"))
    else:
        return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json() or request.form.to_dict()
        user = session.get("user")
        user_id = user["id"] if user else None

        if MODEL is None:
            save_prediction(user_id, data, "Model not available (dev).", None)
            return jsonify({
                "predicted_job_role_id": -1,
                "predicted_job_role": "Model not available (dev)."
            }), 200

        if FEATURE_COLUMNS and isinstance(FEATURE_COLUMNS, list):
            row = {}
            for col in FEATURE_COLUMNS:
                found_val = None
                for k, v in data.items():
                    if k.strip().lower() == col.strip().lower():
                        found_val = v
                        break
                try:
                    row[col] = float(found_val) if (found_val is not None and str(found_val) != "") else 0.0
                except Exception:
                    row[col] = 0.0
            X = pd.DataFrame([row], columns=FEATURE_COLUMNS)
        else:
            row = {}
            for k, v in data.items():
                try:
                    row[k] = float(v)
                except Exception:
                    row[k] = v
            X = pd.DataFrame([row])

        try:
            preds = MODEL.predict(X)
        except Exception as e:
            try:
                preds = MODEL.predict(X.values)
            except Exception as e2:
                save_prediction(user_id, data, f"Prediction failed: {e}; {e2}", None)
                return jsonify({"error": f"Model prediction failed: {e}; {e2}"}), 500

        pred = preds[0]
        predicted_label = str(pred)
        if LABEL_MAP:
            try:
                if isinstance(LABEL_MAP, dict):
                    if pred in LABEL_MAP:
                        predicted_label = LABEL_MAP[pred]
                    elif str(pred) in LABEL_MAP:
                        predicted_label = LABEL_MAP[str(pred)]
                    else:
                        for k, v in LABEL_MAP.items():
                            if v == pred:
                                predicted_label = k
                                break
                else:
                    predicted_label = str(pred)
            except Exception:
                predicted_label = str(pred)

        confidence = None
        try:
            if hasattr(MODEL, "predict_proba"):
                probs = MODEL.predict_proba(X)
                if len(probs.shape) == 2:
                    confidence = float(probs[0].max())
                else:
                    confidence = float(probs[0])
        except Exception:
            confidence = None

        save_prediction(user_id, data, predicted_label, confidence)

        return jsonify({
            "predicted_job_role_id": int(pred) if isinstance(pred, (int,)) else -1,
            "predicted_job_role": predicted_label,
            "confidence": confidence
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/history")
def history():
    user = session.get("user")
    if not user:
        session["show_login"] = True
        return redirect(url_for("home"))

    user_id = user["id"]
    items = get_user_predictions(user_id, limit=500)
    return render_template("history.html", user=user, items=items)

@app.route("/admin")
def admin():
    user = session.get("user")
    if not is_admin_user(user):
        session["show_login"] = True
        return redirect(url_for("home"))

    items = []
    if DB is not None:
        try:
            rows = list(preds_coll.aggregate([
                {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "user"}},
                {"$sort": {"_id": -1}},
                {"$limit": 1000}
            ]))
            for r in rows:
                u = (r.get("user") or [])
                uname = u[0].get("username") if len(u) > 0 else None
                email = u[0].get("email") if len(u) > 0 else None
                items.append({
                    "id": str(r.get("_id")),
                    "user_id": str(r.get("user_id")) if r.get("user_id") else None,
                    "username": uname,
                    "email": email,
                    "predicted_role": r.get("predicted_role"),
                    "confidence": r.get("confidence"),
                    "created_at": r.get("created_at"),
                    "input": r.get("input_json")
                })
        except Exception as e:
            print("admin aggregation error:", e)
    else:
        import sqlite3
        conn = get_sqlite_conn()
        c = conn.cursor()
        c.execute("""
          SELECT p.id, p.user_id, u.username, u.email, p.predicted_role, p.confidence, p.created_at, p.input_json
          FROM predictions p
          LEFT JOIN users u ON u.id = p.user_id
          ORDER BY p.id DESC
          LIMIT 1000
        """)
        rows = c.fetchall()
        conn.close()
        for r in rows:
            pid, uid, uname, email, role, conf, created_at, input_json = r
            try:
                inp = json.loads(input_json)
            except Exception:
                inp = {"raw": input_json}
            items.append({
                "id": pid,
                "user_id": uid,
                "username": uname,
                "email": email,
                "predicted_role": role,
                "confidence": conf,
                "created_at": created_at,
                "input": inp
            })

    return render_template("admin.html", user=user, items=items)

@app.route("/export_csv")
def export_csv():
    user = session.get("user")
    if not is_admin_user(user):
        session["show_login"] = True
        return redirect(url_for("home"))

    rows = []
    if DB is not None:
        try:
            cursor = preds_coll.find({}).sort([("_id", -1)])
            for r in cursor:
                # find user if present
                user_doc = users_coll.find_one({"_id": r.get("user_id")}) if r.get("user_id") else None
                rows.append([
                    str(r.get("_id")),
                    str(r.get("user_id")) if r.get("user_id") else "",
                    user_doc.get("username") if user_doc else "",
                    user_doc.get("email") if user_doc else "",
                    r.get("predicted_role"),
                    r.get("confidence"),
                    r.get("created_at"),
                    json.dumps(r.get("input_json", {}), ensure_ascii=False)
                ])
        except Exception as e:
            print("export_csv (mongo) error:", e)
    else:
        import sqlite3
        conn = get_sqlite_conn()
        c = conn.cursor()
        c.execute("SELECT p.id, p.user_id, u.username, u.email, p.predicted_role, p.confidence, p.created_at, p.input_json FROM predictions p LEFT JOIN users u ON u.id = p.user_id ORDER BY p.id DESC")
        rows = c.fetchall()
        conn.close()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "user_id", "username", "email", "predicted_role", "confidence", "created_at", "input_json"])
    for r in rows:
        writer.writerow(r)
    csv_str = output.getvalue()
    output.close()
    return (csv_str, 200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": "attachment; filename=predictions_export.csv"
    })

@app.route('/offline')
def offline():
    return render_template('offline.html')

@app.route("/.well-known/assetlinks.json")
def serve_assetlinks():
    folder = os.path.join(app.root_path, "static", ".well-known")
    file_path = os.path.join(folder, "assetlinks.json")
    if not os.path.exists(file_path):
        from flask import abort
        abort(404)
    return send_from_directory(folder, "assetlinks.json", mimetype="application/json")

if __name__ == "__main__":
    print("Starting Flask app. Mongo URI (hidden) -> DB:", DB.name if DB is not None else None)
    # use_reloader=False prevents multiple process access to DB while developing
    app.run(debug=True, use_reloader=False)
