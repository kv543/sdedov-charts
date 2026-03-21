"""
app.py — שרת Flask לאוטומציה של גרפי שדה דב
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
נתיבים:
  GET  /              ← ממשק הטעינה
  POST /process       ← מקבל Excel, מעבד, מחזיר JSON
  GET  /export/json   ← ZIP עם 6 קבצי JSON
  GET  /export/html   ← HTML עצמאי עם הנתונים מוטבעים
"""

import os
import json
import zipfile
from io import BytesIO

from flask import Flask, request, jsonify, render_template, send_file
from generate_lib import generate_all_data

# ── הגדרות ──────────────────────────────────────────────────
TEMP_DIR = "/tmp/sdedov_last"
os.makedirs(TEMP_DIR, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

# מאגר זיכרון לנתונים האחרונים שעובדו
_last_data: dict = {}

# שמות קבצי JSON לייצוא
JSON_FILES = {
    "shadeh-dov-kpi.json":          "kpi",
    "shadeh-dov-charts.json":       "charts",
    "shadeh-dov-pie-charts.json":   "pie",
    "shadeh-dov-rooms-charts.json": "rooms_charts",
    "shadeh-dov-price-ranges.json": "price_ranges",
    "shadeh-dov-transactions.json": "transactions",
}


# ── נתיבים ──────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process():
    """מקבל קובץ Excel, מעבד, מחזיר את כל הנתונים כ-JSON."""
    if "excel" not in request.files:
        return jsonify({"success": False, "error": "לא נמצא קובץ בבקשה"}), 400

    file = request.files["excel"]
    if not file.filename:
        return jsonify({"success": False, "error": "שם קובץ ריק"}), 400

    if not file.filename.lower().endswith((".xlsx", ".xls")):
        return jsonify({"success": False, "error": "יש להעלות קובץ Excel (.xlsx)"}), 400

    # שמירה זמנית
    tmp_path = os.path.join(TEMP_DIR, "upload.xlsx")
    file.save(tmp_path)

    try:
        data = generate_all_data(tmp_path)
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    # שמירת קבצי JSON לדיסק (לייצוא)
    for fname, key in JSON_FILES.items():
        out_path = os.path.join(TEMP_DIR, fname)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data[key], f, ensure_ascii=False, indent=2)

    # שמירה בזיכרון
    _last_data.clear()
    _last_data.update(data)

    return jsonify({"success": True, "data": data})


@app.route("/export/json")
def export_json():
    """מחזיר ZIP עם 6 קבצי JSON."""
    if not _last_data:
        return "אין נתונים. אנא העלה קובץ Excel תחילה.", 400

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, key in JSON_FILES.items():
            content = json.dumps(_last_data.get(key, {}), ensure_ascii=False, indent=2)
            zf.writestr(fname, content)

    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name="sdedov-data.zip"
    )


@app.route("/export/html")
def export_html():
    """מחזיר HTML עצמאי עם כל הנתונים מוטבעים פנימה."""
    if not _last_data:
        return "אין נתונים. אנא העלה קובץ Excel תחילה.", 400

    html = render_template("export_standalone.html", data=_last_data)
    buf  = BytesIO(html.encode("utf-8"))
    return send_file(
        buf,
        mimetype="text/html",
        as_attachment=True,
        download_name="sdedov-charts.html"
    )


# ── הפעלה ───────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
