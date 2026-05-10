"""
generate_lib.py — ספריית עיבוד נתוני שדה דב
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
פונקציה אחת ראשית: generate_all_data(excel_path, ...)
מחזירה dict עם כל הנתונים הנדרשים לגרפים.

שינויים מהותיים (2026-05):
1. סיווג "מתחם" — כל שורה משויכת ל"אשכול" / "מרכז" לפי (גוש, חלקה).
2. שני סטים נפרדים במקום פילטר אחד של "אופציה":
   - df_count: לספירת עסקאות = דירה + אופציה
     ("מימוש אופציה" אינו עסקה חדשה אלא רה-קלסיפיקציה של אופציה קיימת)
   - df_real:  לניתוחי עומק = דירה + מימוש אופציה
     ("מימוש אופציה" כולל נתוני מחיר/מ"ר אמיתיים, בניגוד לאופציה)
3. כל וויג'ט מחזיר נתונים בממדים [compound][time], כך שה-UI יכול לסנן.
4. פלט חדש: comparison — נתוני השוואה בין מתחמים (12 חודשים אחרונים).
"""

import math
import pandas as pd

# ── קבועים ──────────────────────────────────────────────────
MONTHS_HE = {
    1: "ינואר", 2: "פברואר", 3: "מרץ",     4: "אפריל",
    5: "מאי",   6: "יוני",   7: "יולי",    8: "אוגוסט",
    9: "ספטמבר",10: "אוקטובר",11: "נובמבר",12: "דצמבר"
}
PIE_COLORS_ROOMS = ["#496970", "#64929C", "#689CAB", "#82C2D2", "#61C0CC"]
PIE_COLORS_PRICE = ["#496970", "#64929C", "#82C2D2", "#61C0CC"]
ROOMS_ORDER     = ["2 חדרים", "3 חדרים", "4 חדרים", "5 חדרים", "6+"]
ROOMS_BAR_ORDER = ["2 חדרים", "3 חדרים", "4 חדרים", "5 חדרים"]

COMPOUND_KEYS = ["all", "eshkol", "merkaz"]
COMPOUND_LABELS = {"all": "כל המתחמים", "eshkol": "אשכול", "merkaz": "מרכז"}
COMPOUND_COLORS = {"eshkol": "#496970", "merkaz": "#61C0CC"}

# סך יחידות הדיור בכל מתחם (קבוע, לתצוגת ה-KPI "מתוך X דירות")
COMPOUND_TOTAL_UNITS = {"all": 16000, "eshkol": 4844, "merkaz": 7128}
COMPOUND_UNITS_LABEL = {
    "all":    "ברובע שדה דב",
    "eshkol": "במתחם אשכול",
    "merkaz": "במתחם המרכזי",
}

# ── טבלת שיוך גוש/חלקה למתחם ────────────────────────────────
# מבוסס על "שיוך גוש חלקה לפרוייקטים.xlsx" (2026-05).
# כל שורה שלא מופיעה כאן אינה חלק משדה דב ותוסר מהניתוח.
_ESHKOL_6634 = [6, 15, 149, 150, 164, 165, 166, 167, 168, 169, 208,
                209, 219, 221, 223, 238, 242, 243, 246, 312, 314, 324]
_MERKAZ_6896 = [204, 34, 46, 47]
_MERKAZ_6885 = [4, 19, 20]

COMPOUND_MAP = {}
for c in _ESHKOL_6634:    COMPOUND_MAP[(6634, c)] = "eshkol"
COMPOUND_MAP[(7186, 3)]   = "eshkol"
COMPOUND_MAP[(6900, 23)]  = "merkaz"
for c in _MERKAZ_6896:    COMPOUND_MAP[(6896, c)] = "merkaz"
COMPOUND_MAP[(6884, 2)]   = "merkaz"
for c in _MERKAZ_6885:    COMPOUND_MAP[(6885, c)] = "merkaz"


# ── עזר ────────────────────────────────────────────────────

def classify_compound(gush, chelka):
    try:
        return COMPOUND_MAP.get((int(gush), int(chelka)))
    except Exception:
        return None

def month_label(year, month):
    return f"{MONTHS_HE[int(month)]} {int(year)}"

def quarter_label(year, quarter):
    return f"רבעון {quarter} {int(year)}"

def safe_int(v):
    try:
        iv = int(v)
        return iv if iv == v else float(v)
    except Exception:
        return str(v) if v is not None else ""

def safe_float(v, default=0.0):
    try:
        f = float(v)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except Exception:
        return default

def format_date_he(row):
    return f"{int(row['יום'])} ב{MONTHS_HE[int(row['חודש'])]} {int(row['שנה'])}"

def rooms_group(r):
    """קיבוץ מדויק — רק מספרים שלמים. לגרף עמודות (ממוצע)."""
    if   r == 2.0: return "2 חדרים"
    elif r == 3.0: return "3 חדרים"
    elif r == 4.0: return "4 חדרים"
    elif r == 5.0: return "5 חדרים"
    elif r >= 6.0 and r == int(r): return "6+"
    else:          return None

def rooms_group_pie(r):
    """קיבוץ כוללני — X.5 נכלל עם X. לגרף עוגה (התפלגות 100%)."""
    if   r <= 0:   return None
    elif r <= 2.5: return "2 חדרים"
    elif r <= 3.5: return "3 חדרים"
    elif r <= 4.5: return "4 חדרים"
    elif r <= 5.5: return "5 חדרים"
    else:          return "6+"


def _add_numeric_cols(src):
    """מוסיף עמודות מספריות ופרמטרי תאריך ל-DataFrame."""
    src["price"]       = pd.to_numeric(src['תמורה מוצהרת בש"ח'], errors="coerce")
    src["ppm"]         = pd.to_numeric(src["מחיר למ״ר"],          errors="coerce")
    src["sqm"]         = pd.to_numeric(src["שטח"],                 errors="coerce")
    src["year"]        = src["שנה"].astype(int)
    src["month"]       = src["חודש"].astype(int)
    src["rooms_raw"]   = pd.to_numeric(src["חדרים"], errors="coerce").fillna(0)
    src["build_year"]  = pd.to_numeric(src["שנת בניה"], errors="coerce")
    src["rooms_label"]     = src["rooms_raw"].apply(rooms_group)
    src["rooms_label_pie"] = src["rooms_raw"].apply(rooms_group_pie)
    src["quarter"]     = ((src["month"] - 1) // 3 + 1).astype(int)
    src["ym"]          = list(zip(src["year"], src["month"]))
    src["yq"]          = list(zip(src["year"], src["quarter"]))
    src["_date_ym"]    = pd.to_datetime({"year": src["year"], "month": src["month"], "day": 1})
    return src


def _slice(df, compound, cutoff=None):
    """חיתוך DataFrame לפי מתחם וזמן."""
    s = df if compound == "all" else df[df["compound"] == compound]
    if cutoff is not None:
        s = s[s["_date_ym"] >= cutoff]
    return s


# ── פונקציה ראשית ───────────────────────────────────────────

def generate_all_data(
    excel_path,
    projects_count: int = 7,
    projects_url:   str = "https://sdedov.co.il/projects/"
) -> dict:
    """
    קורא קובץ Excel ומחזיר dict עם כל הנתונים לגרפים.

    מבנה הפלט:
    {
      kpi:          {compound: {...kpi fields...}}     # compound ∈ {all, eshkol, merkaz}
      charts:       {key: {... data: {compound: {time: [...]}}, ...}}
      pie:          {key: {... data: {compound: {time: [...]}}, ...}}
      rooms_charts: {key: {... data: {compound: {time: [...]}}, ...}}
      price_ranges: {cheap/expensive: {... data: {compound: [...]}, ...}}
      transactions: {compound: {expensive:[...], cheap:[...]}}
      comparison:   {ppm_by_rooms: {...}, summary: {...}}
      meta:         {date_range, total_count, total_real, ...}
    }
    """

    # ── טעינה וסיווג מתחמים ──────────────────────────────────
    df_all_raw = pd.read_excel(excel_path)
    df_all_raw["compound"] = df_all_raw.apply(
        lambda r: classify_compound(r["גוש"], r["חלקה"]), axis=1
    )
    # סינון שורות שאינן שדה דב (לא סווגו)
    df_all = df_all_raw[df_all_raw["compound"].notna()].copy()

    # שני סטים נפרדים
    types = df_all["סוג עסקה"].astype(str)
    df_count = _add_numeric_cols(df_all[types.isin(["אופציה", "דירה"])].copy())
    df_real  = _add_numeric_cols(df_all[types.isin(["דירה", "מימוש אופציה"])].copy())

    # cutoffs — מבוסס על תאריך מקסימלי ב-df_all (שכולל גם מימוש אופציה)
    df_all["_year"]     = df_all["שנה"].astype(int)
    df_all["_month"]    = df_all["חודש"].astype(int)
    df_all["_date_ym"]  = pd.to_datetime({"year": df_all["_year"], "month": df_all["_month"], "day": 1})
    max_ym = df_all["_date_ym"].max()
    cut_24 = max_ym - pd.DateOffset(months=23)
    cut_12 = max_ym - pd.DateOffset(months=11)
    cuts   = {"all": None, "24": cut_24, "12": cut_12}

    # subsets לניתוחי עומק
    df_real_price = df_real.dropna(subset=["price"])
    df_real_sqm   = df_real.dropna(subset=["sqm"])
    df_real_ppm   = df_real.dropna(subset=["ppm"])

    # ── 1. KPI — לכל מתחם בנפרד ──────────────────────────────
    def _kpi(compound):
        d_count = _slice(df_count, compound)
        d_price = _slice(df_real_price, compound)
        d_sqm   = _slice(df_real_sqm,   compound)
        d_ppm   = _slice(df_real_ppm,   compound)

        def avg_price_rooms(n):
            label = f"{n} חדרים"
            sub = d_price[d_price["rooms_label"] == label]["price"]
            return round(safe_float(sub.mean()) / 1e6, 2) if len(sub) else 0

        return {
            "avg_ppm":            round(safe_float(d_ppm["ppm"].mean())) if len(d_ppm) else 0,
            "avg_price":          round(safe_float(d_price["price"].mean())) if len(d_price) else 0,
            "avg_sqm":            round(safe_float(d_sqm["sqm"].mean()), 1) if len(d_sqm) else 0,
            "total_transactions": int(len(d_count)),
            "total_units":        int(COMPOUND_TOTAL_UNITS.get(compound, 0)),
            "units_label":        COMPOUND_UNITS_LABEL.get(compound, ""),
            "avg_price_3rooms":   avg_price_rooms(3),
            "avg_price_4rooms":   avg_price_rooms(4),
            "projects_count":     int(projects_count),
            "projects_url":       projects_url,
        }

    kpi = {ck: _kpi(ck) for ck in COMPOUND_KEYS}

    # ── 2. גרף חודשי — count, cumulative, ppm ────────────────
    # התוויות (חודשים) מחושבות גלובלית — מבוססות על כל df_count
    monthly_global = (df_count.groupby("ym")
                      .agg(count=("price", "count"))
                      .reset_index()
                      .sort_values("ym"))
    global_ym_list = list(monthly_global["ym"])
    labels_global  = [month_label(y, m) for y, m in global_ym_list]

    def _monthly_count(compound):
        sub = _slice(df_count, compound)
        if len(sub) == 0:
            return [0] * len(global_ym_list)
        m = sub.groupby("ym").size().to_dict()
        return [int(m.get(ym, 0)) for ym in global_ym_list]

    def _monthly_cumulative(counts):
        out, total = [], 0
        for c in counts:
            total += c
            out.append(total)
        return out

    def _monthly_ppm(compound):
        sub = _slice(df_real_ppm, compound)
        if len(sub) == 0:
            return [0] * len(global_ym_list)
        m = sub.groupby("ym")["ppm"].mean().to_dict()
        return [round(safe_float(m.get(ym, 0))) for ym in global_ym_list]

    counts_data      = {ck: _monthly_count(ck) for ck in COMPOUND_KEYS}
    cumulative_data  = {ck: _monthly_cumulative(counts_data[ck]) for ck in COMPOUND_KEYS}
    ppm_data         = {ck: _monthly_ppm(ck) for ck in COMPOUND_KEYS}

    charts = {
        "count": {
            "title":       "כמות דירות שנמכרו בשדה דב לפי חודשים",
            "labels":      labels_global,
            "data":        counts_data,
            "color":       "#496970",
            "tooltipType": "count",
            "yMin":        0,
            "yMax":        None
        },
        "cumulative": {
            "title":       "כמות מצטברת של דירות שנמכרו בשדה דב",
            "labels":      labels_global,
            "data":        cumulative_data,
            "color":       "#496970",
            "tooltipType": "cumulative",
            "yMin":        0,
            "yMax":        None
        },
        "price": {
            "title":       'התפתחות המחיר הממוצע למ"ר בשדה דב',
            "labels":      labels_global,
            "data":        ppm_data,
            "color":       "#61C0CC",
            "tooltipType": "price",
            "yMin":        0,
            "yMax":        120000
        }
    }

    # ── 3. גרף עוגה ──────────────────────────────────────────
    price_breaks = [0, 4e6, 7e6, 10e6, float("inf")]
    price_labels = ["עד 4 מ' ₪", "4-7 מ' ₪", "7-10 מ' ₪", "מעל 10 מ' ₪"]

    def _rooms_pie(df_sub):
        rv = df_sub[df_sub["rooms_label_pie"].notna()]
        return [int(len(rv[rv["rooms_label_pie"] == l])) for l in ROOMS_ORDER]

    def _price_pie(df_sub):
        dp = df_sub.dropna(subset=["price"])
        return [int(((dp["price"] >= price_breaks[i]) & (dp["price"] < price_breaks[i+1])).sum())
                for i in range(4)]

    def _ct_pie(fn, base):
        return {ck: {tk: fn(_slice(base, ck, cuts[tk])) for tk in cuts}
                for ck in COMPOUND_KEYS}

    pie = {
        "rooms": {
            "title":    "התפלגות מכירות לפי מספר חדרים",
            "subtitle": "ללא עסקאות אופציה",
            "labels":   ROOMS_ORDER,
            "data":     _ct_pie(_rooms_pie, df_real),
            "colors":   PIE_COLORS_ROOMS
        },
        "price": {
            "title":    "התפלגות מכירות לפי עלות דירה",
            "subtitle": "ללא עסקאות אופציה",
            "labels":   price_labels,
            "data":     _ct_pie(_price_pie, df_real),
            "colors":   PIE_COLORS_PRICE
        }
    }

    # ── 4. גרף עמודות — ממוצע לפי חדרים ───────────────────────
    def _rooms_mean(src, col, compound, cutoff=None):
        s = _slice(src, compound, cutoff)
        s = s[s["rooms_label"].isin(ROOMS_BAR_ORDER)]
        return s.groupby("rooms_label")[col].mean().reindex(ROOMS_BAR_ORDER)

    def _ct_rooms(src, col, fmt):
        return {ck: {tk: fmt(_rooms_mean(src, col, ck, cuts[tk])) for tk in cuts}
                for ck in COMPOUND_KEYS}

    to_m  = lambda series: [round(safe_float(v) / 1e6, 2) for v in series]
    to_m1 = lambda series: [round(safe_float(v), 1)        for v in series]
    to_i  = lambda series: [round(safe_float(v))            for v in series]

    rooms_charts = {
        "price": {
            "title":       "מחיר דירה ממוצע לפי מס' חדרים",
            "subtitle":    'במיליוני ש"ח',
            "labels":      ROOMS_BAR_ORDER,
            "data":        _ct_rooms(df_real_price, "price", to_m),
            "color":       "#689CAB",
            "tooltipType": "price",
            "yMin":        0,
            "yMax":        14
        },
        "size": {
            "title":       "שטח דירה ממוצע לפי מס' חדרים",
            "subtitle":    'במטרים רבועים',
            "labels":      ROOMS_BAR_ORDER,
            "data":        _ct_rooms(df_real_sqm, "sqm", to_m1),
            "color":       "#61C0CC",
            "tooltipType": "size",
            "yMin":        0,
            "yMax":        160
        },
        "pricePerSqm": {
            "title":       'מחיר ממוצע למ"ר לפי מס\' חדרים',
            "subtitle":    'בש"ח',
            "labels":      ROOMS_BAR_ORDER,
            "data":        _ct_rooms(df_real_ppm, "ppm", to_i),
            "color":       "#61C0CC",
            "tooltipType": "pricePerSqm",
            "yMin":        20000,
            "yMax":        100000
        }
    }

    # ── 5. מחירי קצה — רבעוני (לפי מתחם) ─────────────────────
    quarters_sorted = sorted(df_real_price["yq"].unique())
    q_labels        = [quarter_label(y, q) for y, q in quarters_sorted]

    def _q_count(df_sub):
        return [int(len(df_sub[df_sub["yq"] == yq])) for yq in quarters_sorted]

    cheap_data, expensive_data = {}, {}
    for ck in COMPOUND_KEYS:
        sub = _slice(df_real_price, ck)
        cheap_data[ck]     = _q_count(sub[sub["price"] < 4e6])
        expensive_data[ck] = _q_count(sub[sub["price"] > 10e6])

    price_ranges = {
        "cheap":     {"labels": q_labels, "data": cheap_data,     "color": "#61C0CC"},
        "expensive": {"labels": q_labels, "data": expensive_data, "color": "#496970"}
    }

    # ── 6. טבלת עסקאות — לכל מתחם ────────────────────────────
    def _make_row(row):
        complex_label = COMPOUND_LABELS.get(row["compound"], "שדה דב")
        return {
            "date":       format_date_he(row),
            "complex":    complex_label,
            "price":      round(safe_float(row["price"])),
            "sqm":        round(safe_float(row["sqm"])),
            "rooms":      safe_int(row["rooms_raw"]),
            "build_year": safe_int(row["build_year"]) if pd.notna(row["build_year"]) else "",
            "ppm":        round(safe_float(row["ppm"])),
            "compound":   row["compound"],
        }

    transactions = {}
    for ck in COMPOUND_KEYS:
        sub = _slice(df_real_price, ck)
        if len(sub) == 0:
            transactions[ck] = {"expensive": [], "cheap": []}
            continue
        top_exp   = sub.nlargest(10, "price")
        top_cheap = sub.nsmallest(10, "price")
        transactions[ck] = {
            "expensive": [_make_row(r) for _, r in top_exp.iterrows()],
            "cheap":     [_make_row(r) for _, r in top_cheap.iterrows()]
        }

    # ── 7. השוואה בין מתחמים — 12 חודשים אחרונים ────────────
    # מ"ר ממוצע לפי חדרים — שתי סדרות
    eshkol_ppm_by_rooms = to_i(_rooms_mean(df_real_ppm, "ppm", "eshkol", cut_12))
    merkaz_ppm_by_rooms = to_i(_rooms_mean(df_real_ppm, "ppm", "merkaz", cut_12))

    # תוויות חודש לפועל לכל מתחם — כדי לציין בסאב-טייטל מה הטווח האמיתי
    def _range_label(compound, src):
        sub = _slice(src, compound, cut_12)
        if len(sub) == 0:
            return "אין נתונים"
        ymin = sub["_date_ym"].min()
        ymax = sub["_date_ym"].max()
        return f"{month_label(ymin.year, ymin.month)} – {month_label(ymax.year, ymax.month)}"

    range_eshkol = _range_label("eshkol", df_real)
    range_merkaz = _range_label("merkaz", df_real)

    # טבלת סיכום
    def _stats(compound):
        d_count = _slice(df_count, compound, cut_12)
        d_price = _slice(df_real_price, compound, cut_12)
        d_sqm   = _slice(df_real_sqm,   compound, cut_12)
        d_ppm   = _slice(df_real_ppm,   compound, cut_12)
        return {
            "transactions": int(len(d_count)),
            "real_rows":    int(len(d_price)),
            "avg_price":    round(safe_float(d_price["price"].mean())) if len(d_price) else 0,
            "avg_sqm":      round(safe_float(d_sqm["sqm"].mean()), 1) if len(d_sqm) else 0,
            "avg_ppm":      round(safe_float(d_ppm["ppm"].mean())) if len(d_ppm) else 0,
            "median_price": round(safe_float(d_price["price"].median())) if len(d_price) else 0,
            "median_ppm":   round(safe_float(d_ppm["ppm"].median())) if len(d_ppm) else 0,
        }

    comparison = {
        "ppm_by_rooms": {
            "title":    'מחיר ממוצע למ"ר לפי מס\' חדרים — השוואת מתחמים',
            "subtitle": '12 חודשים אחרונים, ש"ח למ"ר',
            "note":     "* עסקאות מימוש אופציה במרכז משקפות תנאי שננעלו במועד חתימת האופציה המקורית",
            "labels":   ROOMS_BAR_ORDER,
            "series": [
                {"name": "אשכול", "key": "eshkol", "data": eshkol_ppm_by_rooms,
                 "color": COMPOUND_COLORS["eshkol"], "range": range_eshkol},
                {"name": "מרכז",  "key": "merkaz", "data": merkaz_ppm_by_rooms,
                 "color": COMPOUND_COLORS["merkaz"], "range": range_merkaz}
            ],
            "yMin": 0,
            "yMax": 100000
        },
        "summary": {
            "title":    "השוואה מספרית בין מתחמים",
            "subtitle": "12 חודשים אחרונים",
            "note":     "* עסקאות מימוש אופציה במרכז משקפות תנאי שננעלו במועד חתימת האופציה המקורית",
            "compounds": {
                "eshkol": {"label": "אשכול", "color": COMPOUND_COLORS["eshkol"], "range": range_eshkol, "stats": _stats("eshkol")},
                "merkaz": {"label": "מרכז",  "color": COMPOUND_COLORS["merkaz"], "range": range_merkaz, "stats": _stats("merkaz")},
            },
            "rows": [
                {"key": "transactions", "label": "סך עסקאות (כולל אופציה)", "format": "int"},
                {"key": "real_rows",    "label": 'עסקאות עם נתוני מ"ר',     "format": "int"},
                {"key": "avg_price",    "label": "מחיר ממוצע לדירה",         "format": "shekel"},
                {"key": "median_price", "label": "מחיר חציוני לדירה",        "format": "shekel"},
                {"key": "avg_sqm",      "label": 'שטח ממוצע (מ"ר)',         "format": "sqm"},
                {"key": "avg_ppm",      "label": 'מחיר ממוצע למ"ר',          "format": "shekel_int"},
                {"key": "median_ppm",   "label": 'מחיר חציוני למ"ר',         "format": "shekel_int"},
            ]
        }
    }

    # ── מטא-נתונים ────────────────────────────────────────────
    yr_min  = int(df_real["year"].min())
    mo_min  = int(df_real.loc[df_real["year"] == yr_min, "month"].min())
    yr_max  = int(df_real["year"].max())
    mo_max  = int(df_real.loc[df_real["year"] == yr_max, "month"].max())

    meta = {
        "total_count":     int(len(df_count)),       # סך עסקאות לספירה (אופציה + דירה)
        "total_real":      int(len(df_real)),         # סך שורות עם נתוני אמת (דירה + מימוש)
        "total_raw":       int(len(df_all)),          # סך השורות בקובץ ששויכו לשדה דב
        "compounds": {
            "eshkol": int((df_all["compound"] == "eshkol").sum()),
            "merkaz": int((df_all["compound"] == "merkaz").sum()),
        },
        "by_type": {
            "אופציה":       int((df_all["סוג עסקה"] == "אופציה").sum()),
            "דירה":         int((df_all["סוג עסקה"] == "דירה").sum()),
            "מימוש אופציה": int((df_all["סוג עסקה"] == "מימוש אופציה").sum()),
        },
        "date_range":      f"{month_label(yr_min, mo_min)} – {month_label(yr_max, mo_max)}",
        "max_ym":          [int(max_ym.year), int(max_ym.month)],
    }

    return {
        "kpi":          kpi,
        "charts":       charts,
        "pie":          pie,
        "rooms_charts": rooms_charts,
        "price_ranges": price_ranges,
        "transactions": transactions,
        "comparison":   comparison,
        "meta":         meta
    }


# ── פונקציה לגרף עלות קרקע ──────────────────────────────────

def generate_land_chart_data(excel_path) -> dict:
    """
    מייצר נתונים לגרף עלות קרקע ליחידת דיור.

    מבנה אקסל נדרש (גמיש — מזהה עמודות לפי שם):
      - סדר כרונולוגי      : מספר מכרז (לקיבוץ)
      - תאריך סגירת מכרז   : תאריך בפורמט DD.M.YY
      - מספר מכרז          : מחרוזת כגון "62/2021"
      - מתחם               : שם מתחם
      - עלות ממוצעת לקרקע ליחידת דיור : עלות לכל זוכה (₪)
      - ממוצע למכרז        : ממוצע מכרז (₪)
    """
    df = pd.read_excel(excel_path)

    def _parse_date(s):
        s = str(s).strip()
        parts = s.split(".")
        if len(parts) == 3:
            day, month, yr = int(parts[0]), int(parts[1]), int(parts[2])
            if yr < 100:
                yr += 2000
            return pd.Timestamp(year=yr, month=month, day=day)
        return pd.NaT

    df["_date"]       = df["תאריך סגירת מכרז"].apply(_parse_date)
    df["_seq"]        = pd.to_numeric(df["סדר כרונולוגי"], errors="coerce")
    df["_unit_cost"]  = pd.to_numeric(df["עלות ממוצעת לקרקע ליחידת דיור"], errors="coerce")
    df["_tender_avg"] = pd.to_numeric(df["ממוצע למכרז"], errors="coerce")

    tenders = []
    for seq_val, group in df.groupby("_seq", sort=True):
        group = group.dropna(subset=["_date"])
        if group.empty:
            continue
        row1    = group.iloc[0]
        date    = row1["_date"]

        xLabel     = f"{MONTHS_HE[date.month]} {date.year}"
        date_short = f"{date.day}.{date.month}.{str(date.year)[2:]}"

        tender_num = str(row1["מספר מכרז"]).strip()
        area       = str(row1["מתחם"]).strip()

        avg_val = safe_float(row1["_tender_avg"])
        vals    = group["_unit_cost"].dropna()
        min_val = safe_float(vals.min()) if len(vals) > 0 else avg_val
        max_val = safe_float(vals.max()) if len(vals) > 0 else avg_val
        winners = len(group)

        tenders.append({
            "xLabel":  xLabel,
            "date":    date_short,
            "tender":  tender_num,
            "area":    area,
            "avg":     round(avg_val),
            "min":     round(min_val),
            "max":     round(max_val),
            "winners": winners
        })

    return {
        "title":    "עלות קרקע ליחידת דיור",
        "subtitle": 'התפתחות מחיר הקרקע הממוצע ליח"ד במכרזי שדה דב לפי תאריך סגירת מכרז',
        "note":     "* הטווח מייצג את הפיזור בין הצעות הזוכים בכל מכרז",
        "tenders":  tenders
    }
