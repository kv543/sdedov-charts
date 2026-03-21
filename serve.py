#!/usr/bin/env python3
"""
שרת מקומי לתצוגה מקדימה של גרפי שדה דב
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
שימוש:
  python serve.py                        ← שואל על קובץ האקסל
  python serve.py "קובץ_נתונים.xlsx"    ← מעבד ישירות

מה קורה:
  1. מעבד את קובץ האקסל → מייצר JSON בתיקיית data/
  2. מפעיל שרת מקומי על פורט 8080
  3. פותח דפדפן עם תצוגה מקדימה מלאה של הגרפים
"""

import sys
import os
import subprocess
import webbrowser
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8080
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class CORSHandler(SimpleHTTPRequestHandler):
    """שרת HTTP עם תמיכת CORS ולוג מינימלי"""
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format, *args):
        # הצג רק שגיאות, לא כל request
        if args and str(args[1]) not in ("200", "304"):
            super().log_message(format, *args)


def find_excel():
    """מחפש קובץ אקסל בתיקייה הנוכחית"""
    excels = [f for f in os.listdir(SCRIPT_DIR)
              if f.lower().endswith((".xlsx", ".xls")) and not f.startswith("~")]
    return excels


def process_excel(path):
    """מריץ את generate.py על קובץ האקסל"""
    generate_script = os.path.join(SCRIPT_DIR, "generate.py")
    result = subprocess.run(
        [sys.executable, generate_script, path],
        cwd=SCRIPT_DIR,
        capture_output=False
    )
    return result.returncode == 0


def open_browser():
    url = f"http://localhost:{PORT}/preview.html"
    webbrowser.open(url)


def main():
    os.chdir(SCRIPT_DIR)

    # ── מציאת קובץ האקסל ──────────────────────────────────
    if len(sys.argv) > 1:
        excel_path = sys.argv[1]
    else:
        excels = find_excel()
        if len(excels) == 1:
            excel_path = excels[0]
            print(f"\n📂  נמצא קובץ: {excel_path}")
        elif len(excels) > 1:
            print("\n📂  נמצאו מספר קבצי אקסל:")
            for i, f in enumerate(excels, 1):
                print(f"    {i}. {f}")
            choice = input("\nבחר מספר: ").strip()
            try:
                excel_path = excels[int(choice) - 1]
            except (ValueError, IndexError):
                print("❌  בחירה לא תקינה")
                sys.exit(1)
        else:
            print("\n❌  לא נמצא קובץ אקסל בתיקייה.")
            print("   הכנס את קובץ האקסל לתיקייה זו והפעל מחדש.")
            sys.exit(1)

    # ── עיבוד ─────────────────────────────────────────────
    if not os.path.isabs(excel_path):
        excel_path = os.path.join(SCRIPT_DIR, excel_path)

    if not os.path.exists(excel_path):
        print(f"❌  הקובץ לא נמצא: {excel_path}")
        sys.exit(1)

    print(f"\n🔄  מעבד נתונים...")
    ok = process_excel(excel_path)
    if not ok:
        print("❌  שגיאה בעיבוד הנתונים")
        sys.exit(1)

    # ── שרת מקומי ─────────────────────────────────────────
    print(f"\n🌐  שרת פועל: http://localhost:{PORT}/preview.html")
    print("    לסיום לחץ Ctrl+C\n")

    threading.Timer(1.2, open_browser).start()

    try:
        HTTPServer(("", PORT), CORSHandler).serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋  השרת נסגר")


if __name__ == "__main__":
    main()
