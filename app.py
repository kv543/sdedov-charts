"""
app.py — שרת Flask לאוטומציה של גרפי שדה דב
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
נתיבים:
  GET  /login         ← טופס כניסה
  POST /login         ← אימות סיסמה
  GET  /logout        ← יציאה
  GET  /              ← ממשק הטעינה (מוגן)
  POST /process       ← מקבל Excel ראשי, מעבד, מחזיר JSON
  POST /process-land  ← מקבל Excel קרקע (אופציונלי)
  GET  /export/json   ← ZIP עם קבצי JSON
  GET  /export/html   ← HTML עצמאי עם נתונים מוטבעים
"""

import os
import json
import zipfile
from io import BytesIO
from functools import wraps

from flask import (Flask, request, jsonify, render_template,
                   send_file, session, redirect, url_for)

from generate_lib import generate_all_data, generate_land_chart_data

# ── הגדרות ──────────────────────────────────────────────────
TEMP_DIR     = "/tmp/sdedov_last"
os.makedirs(TEMP_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key    = os.environ.get("SECRET_KEY",    "sdedov-internal-key-2024")
APP_PASSWORD      = os.environ.get("APP_PASSWORD",  "sdedov2024")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

# מאגרי זיכרון
_last_data:      dict = {}
_last_land_data: dict = {}

JSON_FILES = {
    "shadeh-dov-kpi.json":          "kpi",
    "shadeh-dov-charts.json":       "charts",
    "shadeh-dov-pie-charts.json":   "pie",
    "shadeh-dov-rooms-charts.json": "rooms_charts",
    "shadeh-dov-price-ranges.json": "price_ranges",
    "shadeh-dov-transactions.json": "transactions",
}


# ── דקורטור Login Required ───────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── אימות ────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == APP_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "סיסמה שגויה"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── עמוד ראשי ────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return render_template("index.html")


# ── עיבוד Excel ראשי ─────────────────────────────────────────

@app.route("/process", methods=["POST"])
@login_required
def process():
    if "excel" not in request.files:
        return jsonify({"success": False, "error": "לא נמצא קובץ"}), 400

    file = request.files["excel"]
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        return jsonify({"success": False, "error": "יש להעלות קובץ Excel (.xlsx)"}), 400

    tmp_path = os.path.join(TEMP_DIR, "upload.xlsx")
    file.save(tmp_path)

    try:
        data = generate_all_data(tmp_path)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    # שמירת JSON לדיסק
    for fname, key in JSON_FILES.items():
        with open(os.path.join(TEMP_DIR, fname), "w", encoding="utf-8") as f:
            json.dump(data[key], f, ensure_ascii=False, indent=2)

    _last_data.clear()
    _last_data.update(data)

    return jsonify({"success": True, "data": data})


# ── עיבוד Excel קרקע (אופציונלי) ────────────────────────────

@app.route("/process-land", methods=["POST"])
@login_required
def process_land():
    if "excel" not in request.files:
        return jsonify({"success": False, "error": "לא נמצא קובץ"}), 400

    file = request.files["excel"]
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        return jsonify({"success": False, "error": "יש להעלות קובץ Excel (.xlsx)"}), 400

    tmp_path = os.path.join(TEMP_DIR, "upload_land.xlsx")
    file.save(tmp_path)

    try:
        land_data = generate_land_chart_data(tmp_path)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    # שמירה לדיסק ובזיכרון
    with open(os.path.join(TEMP_DIR, "shadeh-dov-land-chart.json"), "w", encoding="utf-8") as f:
        json.dump(land_data, f, ensure_ascii=False, indent=2)

    _last_land_data.clear()
    _last_land_data.update(land_data)

    return jsonify({"success": True, "data": land_data})


# ── ייצוא JSON ───────────────────────────────────────────────

@app.route("/export/json")
@login_required
def export_json():
    if not _last_data:
        return "אין נתונים. אנא העלה קובץ Excel תחילה.", 400

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, key in JSON_FILES.items():
            content = json.dumps(_last_data.get(key, {}), ensure_ascii=False, indent=2)
            zf.writestr(fname, content)
        # קובץ קרקע — רק אם קיים
        if _last_land_data:
            content = json.dumps(_last_land_data, ensure_ascii=False, indent=2)
            zf.writestr("shadeh-dov-land-chart.json", content)

    buf.seek(0)
    return send_file(buf, mimetype="application/zip",
                     as_attachment=True, download_name="sdedov-data.zip")


# ── ייצוא HTML (ZIP של ווידג'טים) ────────────────────────────

# רשימת קבצי ווידג'ט לייצוא (שם קובץ, שם תבנית)
WIDGET_FILES = [
    ("01-charts.html",       "widgets/charts.html"),
    ("02-pie-rooms.html",    "widgets/pie_rooms.html"),
    ("03-ranges.html",       "widgets/ranges.html"),
    ("04-transactions.html", "widgets/transactions.html"),
]

WIDGET_FILES_LAND = ("05-land.html", "widgets/land.html")


@app.route("/export/html")
@login_required
def export_html():
    import traceback
    if not _last_data:
        return "אין נתונים. אנא העלה קובץ Excel תחילה.", 400

    export_data = dict(_last_data)
    export_data["land_chart"] = _last_land_data if _last_land_data else None

    try:
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname, tpl in WIDGET_FILES:
                try:
                    html = render_template(tpl, data=export_data)
                    zf.writestr(fname, html.encode("utf-8"))
                except Exception as e:
                    zf.writestr(fname + ".error.txt",
                                f"ERROR in {tpl}:\n{traceback.format_exc()}".encode("utf-8"))
            # קובץ קרקע — רק אם קיים
            if _last_land_data:
                try:
                    html = render_template(WIDGET_FILES_LAND[1], data=export_data)
                    zf.writestr(WIDGET_FILES_LAND[0], html.encode("utf-8"))
                except Exception as e:
                    zf.writestr(WIDGET_FILES_LAND[0] + ".error.txt",
                                f"ERROR in land.html:\n{traceback.format_exc()}".encode("utf-8"))

        buf.seek(0)
        return send_file(buf, mimetype="application/zip",
                         as_attachment=True, download_name="sdedov-widgets.zip")
    except Exception as e:
        return f"<pre>EXPORT ERROR:\n{traceback.format_exc()}</pre>", 500


# ── הפעלה ────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
