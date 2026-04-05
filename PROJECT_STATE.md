# Project State — sdedov-charts

> **Last updated:** 2026-04-05
> **Purpose:** Single source of truth for resuming development after any break.
> **Rule:** Update this file at the end of every work session.

---

## 1. Project Overview

A password-protected internal web application for the **שדה דב real estate project** (Tel Aviv).

**What it does:**
- Accepts two Excel files uploaded by the user (main sales DB + optional land tenders DB)
- Processes them server-side with Pandas → generates structured JSON data
- Displays an interactive dashboard with 7 chart/table widgets (Chart.js)
- Exports each widget as a **self-contained HTML snippet** to be pasted into **Elementor** (WordPress) as HTML widgets
- The export UI shows a "copy to clipboard" button per widget — no file download needed

**Who uses it:** One internal user (Yuval) — Hebrew UI, RTL layout.

**Live URL:** Deployed on Railway (private URL, password protected)

---

## 2. Current Status

### ✅ Fully Working
- Password login/logout (`/login`, `/logout`)
- Main Excel upload → full data processing → interactive dashboard (`POST /process`)
- Optional land Excel upload → land cost chart (`POST /process-land`)
- Dashboard auto-loads on page return (via `GET /api/data` + disk cache) — no need to re-upload
- All 7 dashboard widgets render correctly with correct colors/scales matching live Elementor site
- Export copy page (`GET /export/copy`) — shows all widgets with "copy code" clipboard buttons
- Export ZIP download (`GET /export/html`) — downloads `sdedov-widgets.zip` with per-widget HTML files
- Export JSON ZIP (`GET /export/json`) — downloads all data as JSON files
- Server restart recovery — data persists to `/tmp/sdedov_last/` and auto-reloads on next request
- Land widget (widget 7) appears only when land data is present

### ⚠️ Partially Implemented
- `templates/widgets/pie_rooms.html` — exists but **deprecated** (replaced by separate `pie.html` + `rooms_bar.html`). Can be deleted.
- `/export/html` ZIP route still has debug error-trap code (`.error.txt` files in ZIP) — useful for debugging but not production-clean

### ❌ Not Implemented
- No automatic data refresh / scheduled updates
- No multi-user support (single shared session/data)
- No data validation UI (if Excel has wrong columns, error is shown but not detailed)
- `generate.py` and `serve.py` in root — legacy scripts, not used by the Flask app

---

## 2b. Changes Made in Session 2026-04-05

### Architecture clarification
- Confirmed the live Elementor widgets fetch JSON **dynamically** from `https://sdedov.co.il/wp-content/uploads/data/` — no need to re-paste HTML on data updates
- Workflow on data update: upload Excel → export JSON → upload JSON files to WordPress server

### `generate_lib.py` changes
1. **Two separate room-grouping functions:**
   - `rooms_group(r)` — exact integer match only (2.0/3.0/4.0/5.0/6+); used by bar chart. Removes .5 values from averages.
   - `rooms_group_pie(r)` — inclusive ranges (2.5→"2 חדרים", 3.5→"3 חדרים" etc.); used by pie chart so 100% of transactions are counted.
   - Both computed at row level: `rooms_label` (bar) and `rooms_label_pie` (pie) columns added in processing loop.
2. **Date column `_date_ym`** added to `df` before creating df_price/df_sqm/df_ppm so all subsets inherit it.
3. **Time-window cutoffs** computed once: `_max_ym`, `_cut_24` (last 24 months), `_cut_12` (last 12 months).
4. **`pie` data structure changed**: `data` is now `{"all": [...], "24": [...], "12": [...]}` instead of a plain array.
5. **`rooms_charts` data structure changed**: `data` in each sub-chart is now `{"all": [...], "24": [...], "12": [...]}` instead of a plain array.
6. **Rooms bar chart titles**: removed "(ללא עסקאות אופציה)" from all 3 titles (it's already shown as subtitle text).
7. **KPI ppm unit**: display changed from "83,009 ₪ למ״ר" → "83,009 ₪" (label appears below).

### `templates/widgets/transactions.html` (Elementor widget)
- Added `formatDateShort()`: converts `"21 באפריל 2024"` → `"21.4.24"` (matches live Elementor site)
- Added `dateToNum()` for sort comparisons
- Added `class="num"` on numeric `<td>` elements with `font-variant-numeric: tabular-nums`
- Added `#tbl-loading` spinner (`@keyframes spin4`) and `#tbl-error` div
- Removed pulse animation from select; sort reset on select change (cheap→asc, expensive→desc)

### `templates/widgets/pie.html` (Elementor widget)
- Added time-filter tabs: הכל / 24 חודשים / 12 חודשים (same design as charts.html)
- Widget now uses `c.data[pieFilter]` instead of `c.data`

### `templates/widgets/rooms_bar.html` (Elementor widget)
- Added time-filter tabs: הכל / 24 חודשים / 12 חודשים
- Widget now uses `c.data[currentFilter]` instead of `c.data`

### `templates/widgets/kpi.html` (Elementor widget)
- Removed "למ״ר" suffix from ppm value display (kept only in label below)

### `templates/index.html` (dashboard)
- **Bug fix**: `renderRoomsChart` now uses `c.data[roomsFilter]` — previously crashed when `c.data` was an object (breaking all subsequent chart loads)
- Added `roomsFilter` variable + rooms tabs + tab event listeners + CSS + reset
- Added `pieFilter` variable + pie tabs + tab event listeners + CSS + reset
- Added `formatDateShort()` to transactions table — dates now show as `21.4.24` instead of Hebrew long format
- Removed "למ״ר" suffix from ppm KPI display

---

## 3. Architecture

### Frontend
- **Single-page app** inside `templates/index.html` (~1160 lines)
- Two states: upload screen (`#upload-section`) ↔ dashboard (`#dashboard`)
- Chart.js 4.4.1 (CDN) for all charts
- Heebo font (Google Fonts CDN), RTL, Hebrew UI
- On page load: `fetch('/api/data')` → if data available, auto-calls `loadDashboard()`
- Land chart: toggle (average-only / average+range), external tooltip with CSS classes, vertical dashed line plugin, SVG legend

### Backend
- **Flask** (Python 3.11) — `app.py`
- Core data processing: `generate_lib.py`
  - `generate_all_data(excel_path)` → returns `{kpi, charts, pie, rooms_charts, price_ranges, transactions, meta}`
  - `generate_land_chart_data(excel_path)` → returns `{title, subtitle, note, tenders[]}`
- In-memory storage: `_last_data` (dict) + `_last_land_data` (dict)
- Disk persistence: `/tmp/sdedov_last/` — 6 JSON files + optional land JSON
- `_load_from_disk()` called at start of every export/API route

### Database
- None. All data is ephemeral: uploaded per-session, cached to `/tmp/`.
- **Important:** `/tmp/` on Railway may be wiped on redeploy or dyno restart. User must re-upload Excel after server restart IF `/tmp` was cleared. The app handles this gracefully (shows upload screen).

### External Services / APIs
- None. Fully self-contained.
- Chart.js + Google Fonts loaded from CDN (requires internet in browser)

### Deployment
- **Railway** — auto-deploys from GitHub `main` branch on push
- `Procfile`: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app`
- `nixpacks.toml` for build config
- `.python-version` specifies Python version
- Env vars on Railway: `SECRET_KEY`, `APP_PASSWORD` (default: `sdedov2024`)
- Max upload: 50MB

---

## 4. Key Decisions

| Decision | Rationale |
|---|---|
| Flask + Pandas, not Node.js | Python is ideal for Excel processing; simple stack |
| In-memory + disk cache (no DB) | No need for persistence across users; simpler deployment |
| Elementor HTML widgets (not iframes) | Client pastes raw HTML into Elementor's HTML widget; self-contained |
| Copy-to-clipboard UI instead of file download | `.html` files open as rendered pages in macOS, not as text; copy is more convenient |
| `Chart.js 4.4.1` (fixed version) | Avoid breaking changes from updates |
| `fill: 1` / `fill: '+1'` for band chart | Chart.js v4 syntax for area between two datasets (land chart range) |
| Per-widget Jinja2 templates | Each widget is a standalone `<html>` doc; avoids Elementor CSS conflicts |
| `beginAtZero: true` + conditional `yMax` override | Monthly charts start at 0; specific yMax values match live site JSON exactly |
| Toggle changes `backgroundColor`/`fill`, not `hidden` | Hiding datasets in Chart.js v4 removes them from layout; changing fill preserves axis scale |

---

## 5. Existing Features (Technical Detail)

### Routes
| Method | Path | Description |
|---|---|---|
| GET/POST | `/login` | Password form; sets `session["logged_in"]` |
| GET | `/logout` | Clears session |
| GET | `/` | Main dashboard page (requires login) |
| POST | `/process` | Upload main Excel → processes → saves to `/tmp` → returns JSON |
| POST | `/process-land` | Upload land Excel → processes → saves to `/tmp` → returns JSON |
| GET | `/api/data` | Returns current data (from memory or disk); `{"available": bool, "data": {...}}` |
| GET | `/export/json` | ZIP of 6-7 JSON files |
| GET | `/export/copy` | HTML page with copy-to-clipboard buttons for all 7 widget HTML codes |
| GET | `/export/html` | ZIP of 6-7 self-contained widget HTML files |

### Widget Templates (`templates/widgets/`)
| File | Widget | Data key(s) used |
|---|---|---|
| `kpi.html` | 4 KPI cards with animated counters + gauge | `data.kpi` |
| `charts.html` | Monthly line chart (count / cumulative / price/sqm) | `data.charts` |
| `pie.html` | Pie chart (by rooms / by price range) | `data.pie` |
| `rooms_bar.html` | Bar chart by room count (price / size / ppm) | `data.rooms_charts` |
| `ranges.html` | Line chart: cheap (<4M) vs expensive (>10M) over time | `data.price_ranges` |
| `transactions.html` | Table: top 10 most/least expensive transactions | `data.transactions` |
| `land.html` | Land cost per unit — line + range band, external tooltip | `data.land_chart.tenders` |

### Excel Column Requirements (Main DB)
`תמורה מוצהרת בש"ח`, `מחיר למ״ר`, `שטח`, `שנה`, `חודש`, `יום`, `חדרים`, `שנת בניה`, `סוג עסקה`

### Excel Column Requirements (Land DB)
`סדר כרונולוגי`, `תאריך סגירת מכרז`, `מספר מכרז`, `מתחם`, `עלות ממוצעת לקרקע ליחידת דיור`, `ממוצע למכרז`

### Chart Colors (must match live Elementor site)
| Chart | Color |
|---|---|
| Monthly price/sqm | `#61C0CC`, yMax=120,000 |
| Monthly count / cumulative | `#496970`, yMax=null |
| Rooms: price | `#689CAB`, yMax=14 |
| Rooms: size | `#61C0CC`, yMax=160 |
| Rooms: ppm | `#61C0CC`, yMin=20000, yMax=100000 |
| Land line | `#496970` |
| Land band | `rgba(73,105,112,0.16)` |

### generate_lib.py Key Behaviors
- Filters "עסקאות אופציה" using `str.contains("אופציה")` on `סוג עסקה` column
- `safe_float()` handles NaN/Inf → returns 0.0
- `safe_int()` converts to Python native int/float/str (avoids numpy serialization issues)
- Land date parsing: `DD.M.YY` → `pd.Timestamp`; groups by `סדר כרונולוגי`
- Land: per-tender `avg`, `min`, `max` (from individual winner rows), `winners` count
- **Two room grouping functions** (see section 2b): `rooms_group` (exact, for bar) vs `rooms_group_pie` (inclusive, for pie)
- **Time windows**: `_date_ym` column added to `df` before subset creation; `_cut_24`/`_cut_12` computed from `_max_ym` (latest date in dataset)
- **`pie.data` and `rooms_charts[x].data`** are now objects `{"all", "24", "12"}` — not plain arrays

### Date Handling
- Raw dates in JSON: `"21 באפריל 2024"` (Hebrew long format, from `format_date_he()`)
- Displayed in widgets/dashboard: `"21.4.24"` (via `formatDateShort()` in browser JS)
- `formatDateShort(s)`: splits on space, maps Hebrew month name to number, returns `DD.M.YY`

---

## 6. Known Issues / Gaps

1. **`pie_rooms.html` still exists** in `templates/widgets/` — it's a leftover combined widget that was split into `pie.html` + `rooms_bar.html`. Should be deleted to avoid confusion.

2. **`/tmp` data loss on Railway redeploy** — `/tmp/sdedov_last/` persists during server lifetime but is wiped on redeploy. After each Railway deployment, user must re-upload Excel files once. App shows upload screen gracefully.

3. **No error detail on upload failure** — if Excel has wrong column names, user sees a generic Hebrew error. No guidance on which column is missing.

4. **`generate.py` + `serve.py` are legacy** — never called by Flask; they're old standalone scripts. They clutter the repo.

5. **`/export/html` has debug code** — per-widget try/except writes `.error.txt` into ZIP on failure. This is useful for debugging but ideally would be removed or toggled by a debug flag in production.

6. **gunicorn uses 2 workers** — shared in-memory `_last_data` dict is NOT shared between workers. In practice this works because Railway typically routes a user's session to the same worker, but it's technically fragile. The disk persistence (`_load_from_disk`) mitigates this.

7. **`projects_count` and `projects_url` are hardcoded** in `generate_all_data()` defaults: `projects_count=7`, `projects_url="https://sdedov.co.il/projects/"`. These should be editable via UI or env var.

---

## 7. Next Step (MOST IMPORTANT)

Compare the live Elementor `transactions` widget HTML/CSS exactly against the current `transactions.html` widget template — the user noted visual differences in row styling beyond just the date format. Also: complete review of all 6 widgets against live Elementor site.

---

## 8. Short TODO List

- [ ] **Visual review**: compare all 6 Elementor widget templates against live site screenshots — ensure design parity
- [ ] Delete `templates/widgets/pie_rooms.html` (replaced by `pie.html` + `rooms_bar.html`)
- [ ] Delete or archive `generate.py` and `serve.py` (legacy, not used by Flask)
- [ ] Add `projects_count` input field in upload form (currently hardcoded to 7)
- [ ] Remove debug `.error.txt` logic from `/export/html` route (or gate behind `DEBUG` flag)
- [ ] Consider fixing gunicorn to 1 worker to avoid in-memory fragmentation (or switch to a proper cache)
- [ ] Add column-name validation in `generate_all_data()` with a clear error message listing missing columns
- [ ] Test land widget appearance in actual Elementor (confirm tooltip CSS, SVG legend, toggle behavior match live site)

---

## 9. Notes for Future Sessions

### How to resume:
1. Read this file first
2. Check `git log --oneline -10` to see recent commits
3. The app is live on Railway — just push to `main` branch to deploy
4. Password: set via `APP_PASSWORD` env var on Railway (default: `sdedov2024`)

### Jinja2 gotcha (IMPORTANT):
- Widget templates use `{{ data.xxx | tojson }}` to embed data
- **Never use `{#` in CSS within widget templates** — Jinja2 parses it as a comment tag start
- Example fix: `{ #id-selector {` → add a space, or split to separate lines

### Chart.js v4 gotchas:
- `fill: 1` = fill toward dataset at index 1 (for band between max/min datasets)
- Toggle range band: change `dataset.backgroundColor` + `dataset.fill`, NOT `dataset.hidden`
- External tooltip: use `plugins.tooltip.enabled: false` + `external: myTooltipFn`
- Vertical line plugin: implemented as custom `afterDraw` plugin (not built-in)

### Data flow summary:
```
Excel upload → POST /process → generate_lib.py → _last_data (memory) + /tmp/*.json (disk)
                                                         ↓
GET / → fetch('/api/data') → _load_from_disk() if empty → loadDashboard(data)
                                                         ↓
GET /export/copy → render_template each widget → copy-to-clipboard UI
```

### Excel structure notes:
- Main DB: one row per transaction; columns in Hebrew
- Land DB: one row per **winner** within a tender; grouped by `סדר כרונולוגי`
- Option transactions (`סוג עסקה` contains "אופציה") are filtered out from all analysis
- Land date format: `DD.M.YY` (e.g. `23.8.21`) — custom parser in `generate_land_chart_data`

### Elementor integration:
- Each widget is a fully self-contained `<!DOCTYPE html>` snippet
- User copies HTML from `/export/copy` page and pastes into Elementor HTML widget
- Widgets are independent — no shared state between them on the WordPress page
- All fonts/CDN resources load from external URLs (Chart.js CDN, Google Fonts)

---

*This file was generated and should be updated at the end of every dev session.*
