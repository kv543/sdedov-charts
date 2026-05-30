# Project State — sdedov-charts

> **Last updated:** 2026-05-11 (session 5 — copy review only)
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
- **Compound classification** — every row mapped to אשכול/מרכז via (גוש, חלקה); rows outside Sde Dov dropped
- **Per-widget compound filter** (compact pill UI: הכל / אשכול / מרכז) on KPI, pie, rooms_bar, transactions
- **Two-line monthly ppm chart** — אשכול full history + מרכז starting July 2025
- **Two comparison widgets** — ppm-by-rooms + price-by-rooms, אשכול vs מרכז, 12-month window
- **Per-compound KPI** — `total_transactions`, `avg_ppm`, `avg_price`, `total_units` (16K / 4844 / 7128), `units_label`, `projects_count` (7/5/2)
- **Dynamic KPI subtitle** — "מתוך X יחידות דיור Y" updates with compound selection
- All 8 dashboard widgets + land widget render correctly with correct colors/scales matching live Elementor site
- Export copy page (`GET /export/copy`) — shows all widgets with "copy code" clipboard buttons
- Export ZIP download (`GET /export/html`) — downloads `sdedov-widgets.zip` with per-widget HTML files
- Export JSON ZIP (`GET /export/json`) — downloads 8 (+1 optional) JSON files
- Server restart recovery — data persists to `/tmp/sdedov_last/` and auto-reloads on next request
- Land widget appears only when land data is present
- Single gunicorn worker (iteration 6) — no OOM on Railway

### ⚠️ Partially Implemented
- `templates/widgets/pie_rooms.html` — exists but **deprecated** (replaced by separate `pie.html` + `rooms_bar.html`). Can be deleted.
- `templates/widgets/comparison_summary.html` — no longer registered in `app.py` (iteration 5). Can be deleted.
- `/export/html` ZIP route still has debug error-trap code (`.error.txt` files in ZIP) — useful for debugging but not production-clean
- `preview/` folder is committed to the repo with ~300KB inlined Chart.js; should probably be `.gitignore`-d

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

## 2c. Changes Made in Session 2026-04-05 (Session 3)

### `app.py` — Elementor export fix
1. **`strip_to_fragment(html)`** — new helper function added (uses `re` module, which was also imported).
   Converts a full `<!DOCTYPE html>` document into an Elementor-compatible fragment:
   extracts `<style>` / `<script>` from `<head>`, keeps full `<body>` content, strips `<!DOCTYPE>`, `<html>`, `<head>`, `<body>` wrapper tags.
2. **`/export/copy` route** — now calls `strip_to_fragment(render_template(...))` before adding each widget to the list.
   Result: copy-to-clipboard page now outputs fragments (no DOCTYPE/html/head/body) suitable for direct paste into Elementor HTML widgets.

### Global JS scope conflict fix (CRITICAL BUG)
All Chart.js widgets on the same Elementor page share a single global JS scope. Four templates each declared `const font = "..."` at the global level. `charts.html` ran first and claimed `const font`; the next three all crashed with "Cannot redeclare block-scoped variable 'font'" → blank charts.

Fix applied to all four templates:
- **`charts.html`**: entire `<script>` block wrapped in `(function(){...})()` IIFE
- **`pie.html`**: `const PIE_DATA` and `const font` moved inside existing IIFE
- **`rooms_bar.html`**: `const ROOMS_DATA`, `const font`, and `hexToRgba()` moved inside existing IIFE
- **`ranges.html`**: `const PR_DATA`, `const font`, and `hexToRgba()` moved inside existing IIFE

### Widget heights — unified to match transactions table
All card containers now use `min-height: 480px` (matching `transactions.html`):
- `pie.html`: `460px` → `480px`
- `rooms_bar.html`: `460px` → `480px`
- `ranges.html`: `400px` → `480px`
- `charts.html` (time-series): left at `420px` — this widget is full-width and standalone, does not need matching height
- `pie.html` — added `max-height: 320px` on `#pie-chart-wrap` and canvas to prevent the aspect-ratio-driven canvas from growing beyond the 480px container

### Tab active-state styling — Elementor CSS override fix
WordPress/Elementor theme was overriding `.tab.active` with a red background and blue border (button styles). Fixed across all 4 tab sets by adding `!important` to all relevant properties and adding a `:focus` rule:
- Properties enforced with `!important`: `border:none`, `background:none`, `outline:none`, `box-shadow:none`
- `.active` state enforces: `color:#61C0CC`, `text-decoration:underline`, `background:none`, `border:none`, `outline:none`, `box-shadow:none`
- `:focus` pseudo-class added with `outline:none !important; box-shadow:none !important`
- Applied to: `.chart-tab`, `.pie-tab`, `.rooms-tab`, `.pr-tab`

---

## 2d. Changes Made in Session 2026-05-10 (Session 4)

### Trigger / context
Tax-authority data (Feb–Apr 2026) introduced a new `סוג עסקה` value: **"מימוש אופציה"** (option exercise).
- These rows replace pre-existing "אופציה" rows when the buyer signs the actual purchase deal.
- Per Yuval: do **NOT** count them as new transactions (they are re-classifications of existing options).
- BUT they carry **real** price/sqm/ppm data (224/224 non-null), unlike pure "אופציה" rows (3/692).
- The 222 rows in גוש 6900/חלקה 23 are the **first ever real-data sales** in the central compound (Vogue + First).
- This unlocks compound-level comparison (Eshkol vs Central) for the first time.

### Compound classification — new dimension
A new mapping file `שיוך גוש חלקה לפרוייקטים.xlsx` was provided. Encoded inline in `generate_lib.py` as `COMPOUND_MAP`:

| מתחם | גוש | חלקות |
|---|---|---|
| **אשכול** | 6634 | 6, 15, 149, 150, 164, 165, 166, 167, 168, 169, 208, 209, 219, 221, 223, 238, 242, 243, 246, 312, 314, 324 |
| **אשכול** | 7186 | 3 |
| **מרכז** | 6900 | 23 |
| **מרכז** | 6896 | 204, 34, 46, 47 |
| **מרכז** | 6884 | 2 |
| **מרכז** | 6885 | 4, 19, 20 |

Rows whose (גוש, חלקה) is not in the map are dropped (treated as "not Sde Dov").

In the current Excel file (sdedov-db-0326.xlsx, 1519 rows after compound filter):
- **אשכול** = 522 rows (1 אופציה + 521 דירה), data 03/2023–04/2026.
- **מרכז** = 997 rows (691 אופציה + 82 דירה + 224 מימוש אופציה), real-data rows 07/2025–04/2026.

Note: 6896/204 has projects spanning Eshkol/Central/North in reality, but the user's mapping classifies it as **מרכז** for analysis purposes.

### `generate_lib.py` — major rewrite
Old single filter `is_option = str.contains("אופציה")` (which matched both "אופציה" and "מימוש אופציה") was replaced with two distinct datasets:

- **`df_count`** = transaction-counting set: rows where `סוג עסקה ∈ {"אופציה", "דירה"}`
  - Used for: KPI `total_transactions`, monthly count chart, cumulative chart.
  - Excludes "מימוש אופציה" — it's a reclassification of an existing option, not a new transaction.
- **`df_real`** = real-data set for deep analysis: rows where `סוג עסקה ∈ {"דירה", "מימוש אופציה"}`
  - Used for: monthly ppm chart, pie, rooms_bar, ranges, transactions table, comparison.
  - Includes "מימוש אופציה" — they have full price/sqm/ppm data.

Helpers added:
- `classify_compound(gush, chelka)` — returns "eshkol" | "merkaz" | None.
- `_add_numeric_cols(df)` — adds price/ppm/sqm/year/month/rooms_label/_date_ym.
- `_slice(df, compound, cutoff=None)` — filter helper for compound × time slicing.

### JSON schema — BREAKING CHANGE
Every widget's data is now keyed by `[compound][time]` where:
- `compound ∈ {"all", "eshkol", "merkaz"}`
- `time ∈ {"all", "24", "12"}` (where applicable)

Examples:
```json
"kpi": {"all": {...}, "eshkol": {...}, "merkaz": {...}}
"charts.count.data": {"all": [...], "eshkol": [...], "merkaz": [...]}
"pie.rooms.data": {"all": {"all":[...], "24":[...], "12":[...]}, "eshkol": {...}, "merkaz": {...}}
"rooms_charts.price.data": {"all": {"all":[...], "24":[...], "12":[...]}, "eshkol": {...}, "merkaz": {...}}
"price_ranges.cheap.data": {"all": [...], "eshkol": [...], "merkaz": [...]}
"transactions": {"all": {"expensive":[...], "cheap":[...]}, "eshkol": {...}, "merkaz": {...}}
```

New top-level keys:
- **`comparison`** — dedicated comparison data (12-month window):
  - `comparison.ppm_by_rooms.series` = `[{name, key, data, color, range}, ...]` (אשכול + מרכז).
  - `comparison.summary` = table data: `compounds.{eshkol,merkaz}.stats`, plus `rows[]` defining rows (label, key, format).
- **`meta`** — now exposed as a JSON file too (was internal). Includes `total_count`, `total_real`, `total_raw`, `compounds.{eshkol,merkaz}`, `by_type.{אופציה,דירה,מימוש אופציה}`, `date_range`, `max_ym`.

### `app.py` changes
1. `JSON_FILES` extended with `shadeh-dov-comparison.json` and `shadeh-dov-meta.json`.
2. `WIDGET_FILES` and `WIDGET_NAMES` extended with two new comparison widgets, land widget renumbered 09.

### Dashboard `templates/index.html` — global compound filter
1. New global tab bar (`.compound-bar` / `.compound-tab[data-compound="all|eshkol|merkaz"]`) at the top.
2. New compound stats line shows row counts per compound and per type (אופציה/דירה/מימוש).
3. All render functions updated to read `data[compoundFilter]`:
   - `renderKPI()` (now reads from `KPI_DATA[compoundFilter]`)
   - `filteredMain()`, `renderPieChart()`, `renderRoomsChart()`, `filteredPR()`, `renderTbl()`
4. New `rerenderAllForCompound()` function called when global compound tab changes.
5. New `initComparison()` + `renderCompareBars()` + `renderCompareSummary()` for the comparison section.
6. Meta-bar fields renamed: `total` → `total_count`, `no_option` → `total_real`.

### Elementor widget templates — per-widget compound tabs
Each widget got an independent compound tab row (since Elementor widgets are independent on the live page). State variable `currentCompound = 'all'` per widget. CSS class pattern: `.{prefix}-comp-tab` with active states pseudo-namespaced per widget.

Updated:
- `kpi.html`         — wrapped JS in IIFE, added `render()` function reading `KPI_ALL[currentCompound]`.
- `charts.html`      — `getFilteredData()` now uses `c.data[currentCompound]`.
- `pie.html`         — `c.data[currentCompound][pieFilter]`.
- `rooms_bar.html`   — `c.data[currentCompound][currentFilter]`.
- `ranges.html`      — `PR_DATA.cheap.data[currentCompound]`.
- `transactions.html` — `getRows(key)` helper using `TBL_DATA[currentCompound]`.

New widget templates:
- `comparison_bars.html` — grouped bar chart, אשכול vs מרכז, ppm by rooms, 12-month window.
- `comparison_summary.html` — comparison table with indicators (transactions, real_rows, avg_price, median_price, avg_sqm, avg_ppm, median_ppm). Includes "★ winner" indicator for max value per row.

### Important: deployment coordination
This is a **breaking JSON-schema change**. The old widgets cannot consume the new JSON, and vice versa. Required deployment order:
1. Push code to Railway (auto-deploy).
2. Re-upload Excel via dashboard at `/` (regenerates `/tmp/sdedov_last/*.json` with new schema).
3. Download new JSONs via `/export/json`, upload to WordPress under `/wp-content/uploads/data/`.
4. Replace each Elementor HTML widget with new HTML from `/export/copy`.

The live dynamic-fetch widgets (separate codebase that fetches JSON from WordPress at runtime) **must** be updated separately by the user to consume the new schema; otherwise they'll show empty/broken charts.

### Iteration 2 — UI refinement (within session 4)

After previewing the initial implementation, the global compound filter and the original 3-button compound tabs were replaced with a more compact and consistent design:

1. **Per-widget compound filter on the dashboard too** (no more global bar). Each widget tracks its own compound state independently. State variables: `kpiCompound`, `mainCompound`, `pieCompound`, `roomsCompound`, `prCompound`, `tblCompound`. The single `compoundFilter` global was removed; `rerenderAllForCompound()` and `initCompoundTabs()` were replaced with `initPerWidgetCompoundPills()` + `_bindCompoundPill()` helper.

2. **Compact "segmented pill" design** for the compound filter, replacing the previous 3-outlined-button design:
   - Single rounded pill container (`background:#eef3f4`, `border-radius:14px`, `padding:2px`) with 3 fused inner buttons.
   - Active button: filled with compound color (`#677e85` for "all", `#496970` for אשכול, `#61C0CC` for מרכז), white text, subtle shadow.
   - Short labels: "הכל / אשכול / מרכז" (was "כל המתחמים / אשכול / מרכז").
   - Approximate footprint: ~140-160px wide, ~26px tall (down from ~250px wide previously).
   - Shared CSS class `.cmp-pill` in `index.html`; per-widget pseudo-namespaced classes (e.g. `.kpi-compound-pill`) in Elementor templates to avoid cross-widget bleed.

3. **Dynamic KPI subtitle per compound** — the "מתוך 16,000 יחידות דיור ברובע שדה דב" text now changes based on the selected compound:
   - all → "מתוך 16,000 יחידות דיור ברובע שדה דב"
   - eshkol → "מתוך 4,844 יחידות דיור במתחם אשכול"
   - merkaz → "מתוך 7,128 יחידות דיור במתחם המרכזי"
   - The gauge arc's denominator also switches accordingly so the fill ratio makes sense per compound.
   - Backed by new `kpi[compound].total_units` and `kpi[compound].units_label` fields in the JSON; defined inline in `generate_lib.py` as `COMPOUND_TOTAL_UNITS` and `COMPOUND_UNITS_LABEL` constants.

4. **Compound stats moved into the meta bar** (used to live in the global compound bar above). Now appears on the right side of `meta-bar`: "522 אשכול · 997 מרכז · אופציה 692 · דירה 603 · מימוש 224". Helper class: `.meta-stats-extra`.

5. **Considered but dropped**: an "average build year" row in the comparison summary table. Initial intent was to convey "lower price ↔ later delivery", but the data shows the means are essentially equal (אשכול 2029.7, מרכז 2029.7) due to a bimodal distribution in מרכז (216×2028 in 6900/23 vs 80×2034 in 6896/204). The hypothesis doesn't hold at the compound aggregate level, so the row was omitted to avoid misleading viewers.

### Iteration 3 — time-axis widgets reverted to no-compound, projects_count per compound

After previewing the per-widget compound filters, two more refinements:

1. **Removed compound filter from all time-series widgets** — the user observed that monthly transaction counts and quarterly price-range counts have inherent uncertainty for newly-published months: the data doesn't tell us cleanly whether a given April-2026 transaction is genuinely new or a retroactive `מימוש אופציה` of an option signed earlier. Showing "0 sales in April for מרכז" would be misleading.
   - Affected widgets (now no compound pill, no compound dim in JSON): `charts.html` (count / cumulative / monthly ppm), `ranges.html` (cheap < 4M & expensive > 10M per quarter).
   - Their data shape reverted from `{compound: [...]}` back to a plain array, matching pre-iteration-1 behavior.
   - Compound filter still applies on KPI, pie, rooms_bar, transactions, and the comparison widgets.

2. **`projects_count` is now per-compound**: `COMPOUND_PROJECTS_COUNT = {all: 7, eshkol: 5, merkaz: 2}`. The "פרויקטים בשיווק" KPI card updates accordingly when the compound filter changes.

### Iteration 4 — monthly ppm chart split into two compound lines

After iteration 3, only the monthly average-ppm view (`charts.price`) had a remaining problem: the single combined line showed an apparent "drop" in the last few months, when in reality the drop reflects `מימוש אופציה` rows for מרכז (whose prices were locked at the original option-sign date months earlier). Mixing מרכז's locked-in prices with אשכול's current pricing was misleading.

**Solution**: split the monthly ppm chart into TWO lines.

1. **`generate_lib.py`** — for `charts.price` only:
   - Replaced `data: [...]` with `series: [{name, key, data, color}, ...]`.
   - אשכול series: full timeline (March 2023 — April 2026).
   - מרכז series: same length array, but `null` for months without data (results in line gaps in Chart.js). First non-null month: July 2025.
   - `count` and `cumulative` views unchanged — they keep the simple `data: [...]` shape (no compound split for those).

2. **Both widget code paths** (`templates/widgets/charts.html` and `renderMainChart` in `templates/index.html`):
   - Added `getMainSeries(c)` helper: returns `c.series` if present, else wraps `c.data` as a single-element series. Keeps backward compatibility.
   - `buildDatasets` / dataset construction: iterates the series array. Single-series renders with `fill: true` (existing area behavior). Multi-series renders with `fill: false` to avoid overlap.
   - Added `#chart-legend` element + `renderLegend` / `renderMainLegend` — shown only when there are 2+ named series.
   - Tooltip callback updated to prefix series name when present (e.g. "אשכול: ₪82,000").
   - `spanGaps: false` — Chart.js will leave a gap where data is `null` rather than connecting across.
   - Switched from in-place update (`chartInstance.data...; .update()`) to destroy-and-recreate, since dataset count can change between views.

3. **Title change**: `charts.price.title` from `'התפתחות המחיר הממוצע למ"ר בשדה דב'` → `'התפתחות המחיר הממוצע למ"ר לפי מתחם'`.

### Iteration 5 — comparison summary table replaced with second bar chart

The user reviewed the comparison summary table and decided it doesn't belong on the public site.

1. **Replaced `comparison.summary` (table)** with `comparison.price_by_rooms` — a second bar chart showing average apartment price (in millions ₪) per rooms category, אשכול vs מרכז. Data layout mirrors `ppm_by_rooms`. The two bar charts now sit side-by-side and tell complementary stories: ppm shows the per-meter premium, price shows the actual buyer's check.

2. **New widget `templates/widgets/comparison_price_bars.html`** — near-clone of `comparison_bars.html`, but formatted in millions (`X.XX מ' ₪`). Values like 6.32 / 9.70 / 11.95 etc.

3. **`comparison_summary.html`** is no longer registered in `app.py`'s `WIDGET_FILES` / `WIDGET_NAMES` (file kept on disk for reference but unused). Same for `summary` field — removed from `comparison` dict in `generate_lib.py`.

4. **Dashboard `index.html`**:
   - Refactored `renderCompareBars` into a generic `_renderCmpChart(c, ids, fmt)` helper.
   - Two callers: `renderComparePpm` (existing, formats as "K") and `renderComparePrice` (new, formats as decimals + "מיליון ש"ח").
   - Replaced the summary table HTML with `cmp-price-container` (mirror of `cmp-bars-container`).
   - Two chart instances: `cmpPpmInst`, `cmpPriceInst`.

5. **Note text changed** in `comparison.{ppm,price}_by_rooms.note` from "* עסקאות מימוש אופציה במרכז משקפות תנאי שננעלו במועד חתימת האופציה המקורית" to "האיכלוס במתחם המרכזי צפוי בממוצע כ-3-4 שנים לאחר מתחם אשכול". Both bar charts use the same shared note (`_shared_note` constant in `generate_lib.py`).

6. **`app.py`**: widget order updated — slot 8 is now `comparison_price_bars` instead of `comparison_summary`. Land widget renumbered to `09-land.html`.

### Iteration 6 — gunicorn workers reduced to 1 (OOM fix)

After deploying iteration 5 to Railway, the app started failing with `Application failed to respond`. Deploy logs showed:

```
[ERROR] Worker (pid:3) was sent SIGKILL! Perhaps out of memory?
```

The OOM happened during multipart upload parsing in `/process`. Two gunicorn workers each holding pandas + the in-memory `_last_data` + the upload-time multipart buffer exceeded Railway's RAM.

**Fix**: `Procfile` `--workers 2` → `--workers 1`. This was already on the open TODO list from session 3 ("gunicorn uses 2 workers — shared in-memory `_last_data` dict is NOT shared between workers... Consider fixing gunicorn to 1 worker"). Resolves the OOM and also fixes potential cross-worker inconsistency.

The trigger for the OOM (now vs. earlier sessions when 2 workers were stable): the JSON payload grew with the compound dimension (per-compound KPIs, transactions per compound, comparison section), and the source Excel grew to 1,519 rows. Combined headroom was lost.

### Iteration 7 — "10 העסקאות..." titles cleaned up

The transactions table titles (`"10 העסקאות היקרות ביותר בשדה דב"` / `"...זולות..."`) included the project name "בשדה דב". When a user filters by compound (אשכול / מרכז), the headline became inaccurate — it still said "בשדה דב" even when showing only one compound. Removed the trailing project-name phrase.

- `templates/index.html` — `TBL_TITLES` const updated.
- `templates/widgets/transactions.html` — `TABLE_TITLES` const updated.
- Result: titles are simply `"10 העסקאות היקרות ביותר"` / `"...הזולות ביותר"`, accurate under any compound filter.

### Iteration 8 — Widget heights aligned in pairs

Symptom: on the live site, paired widgets in a `grid-2` row didn't have matching heights — most visibly the transactions table (with compound pill + 10 rows) was taller than the ranges chart sitting next to it.

Root cause: every widget had `min-height: 480px`. Content-rich widgets (transactions table) pushed past 480px while their pair partner stayed at exactly 480px. CSS Grid stretched the grid cells to equal height, but the inner widget cards didn't fill the cells.

**Fix** — for each grid-2 widget:
- Container: `min-height: 480px` → `height: 480px` (fixed). Now both cards in a pair are exactly 480px.
- Transactions: removed `max-height: 360px` on `#tbl-wrap` → `flex: 1` lets it fill whatever space remains inside the 480px container; table content scrolls within the wrap.
- Pie: chart-wrap `max-height: 320px` → `280px`, canvas `max-width: 480px` → `400px`, added `min-height: 0`. Was needed because the natural pie canvas (with `aspectRatio: 1.4`) would have been ~343px tall and pushed the time tabs out of the 480px box.

Applied to: `pie.html`, `rooms_bar.html`, `ranges.html`, `transactions.html`, `comparison_bars.html`, `comparison_price_bars.html`, and the matching containers in `templates/index.html`.

### Iteration 9 — Mobile-responsive widget heights + compact legend

After iteration 8, mobile devices started showing overflow problems:
1. **rooms_bar / pie tabs slipped outside the box on mobile** — narrow screens caused header/title to wrap to 2-3 lines, and with `height: 480px` strict, the bottom tabs were pushed outside the rounded card.
2. **Comparison widget legend wrapped to 2 rows on mobile** — each legend item (e.g. `▢ אשכול מאי 2025 – מרץ 2026`) was too wide to fit two side-by-side on a 380px-wide screen. The wrapped legend exceeded the 480px container.
3. **Compound name vs. swatch alignment** — when the date range was stacked below the compound name (`display: block`), the swatch was vertically centered relative to the now 2-line label, ending up *between* the two lines instead of next to the name.

**Fixes applied via `@media (max-width: 600px)` blocks**:

*All grid-2 widgets* (`pie`, `rooms_bar`, `ranges`, `transactions`, both comparison widgets):
```css
@media (max-width: 600px) {
  #X-container { height: auto; min-height: 480px; }
}
```
On single-column mobile layouts there's no horizontal pair to align with, so the container becomes free to grow if the content needs it.

*Comparison widgets* — compact legend on mobile:
```css
@media (max-width: 600px) {
  .Xcmpb-legend       { gap: 14px; margin-top: 10px; }
  .Xcmpb-legend-item  { font-size: 12px; align-items: flex-start; }
  .Xcmpb-swatch       { margin-top: 3px; }            /* visually align with name baseline */
  .Xcmpb-leg-name     { display: block; line-height: 1.2; }
  .Xcmpb-leg-range    { display: block; margin: 1px 0 0 0; font-size: 10px; line-height: 1.2; }
}
```
Stacking name+range vertically inside each legend item makes each item narrower → two items fit side-by-side without wrapping. `align-items: flex-start` + 3px `margin-top` on the swatch puts the swatch at the same horizontal line as the compound name.

*Comparison containers reverted to flexible height even on desktop*:
```css
#cmpb-container, #cmpp-container { min-height: 480px; }   /* not fixed height */
#cmpb-wrap,      #cmpp-wrap      { min-height: 0; }       /* chart can shrink to absorb legend growth */
.cmpb-legend,    .cmpp-legend    { flex-shrink: 0; }      /* legend keeps its natural height */
.cmpb-note,      .cmpp-note      { flex-shrink: 0; }
```
The pair stays equal-height via CSS Grid's `align-items: stretch`; the wrap absorbs the difference when the legend wraps.

*Dashboard `index.html`* — same compact legend rule and `@media (max-width: 900px)` block to relax all grid-2 widgets when the dashboard collapses to a single column.

### Iteration 10 — Jinja2 `{#X-container{` comment-tag trap

After iteration 9, `/export/copy` started showing `"Missing end of comment tag"` errors on `pie.html`, `rooms_bar.html`, and `ranges.html`. The culprit was the new one-liner media queries:

```css
@media(max-width:600px){#rooms-container{height:auto;min-height:480px;}}
```

The `{#` sequence right before `rooms-container` is identical to Jinja2's comment opener. Jinja parses it as the start of `{# … #}` and then can't find the closing `#}` inside the CSS, throwing the `Missing end of comment tag` error at render time.

**Fix**: separate the opening brace from the `#`, either with a space or with a newline. Example:
```css
@media (max-width: 600px) { #rooms-container { height: auto; min-height: 480px; } }
```

Applied to all four affected widget templates. The existing note in section 9 "Jinja2 gotcha" warned about this exact pattern — easy to re-introduce when iterating quickly on CSS. **For future iterations: always keep at least one space between `{` and `#` when writing CSS inside a Jinja template, or wrap risky CSS in `{% raw %}` / `{% endraw %}` blocks.**

### Sanity checks (passed)
- `total_count` = 1,295 (was 1,519) — `מימוש אופציה` correctly excluded.
- KPI per compound: אשכול avg_ppm 82,890 ₪, מרכז 65,549 ₪ — large but expected gap.
- All 8 widget templates + dashboard render through Jinja without error.
- All Elementor fragments are clean (no DOCTYPE/html/body wrappers).
- Comparison ppm_by_rooms (12mo): אשכול [73390, 80016, 85620, 86510], מרכז [67344, 64908, 64340, 66006].
- **6896/204 fully-מרכז classification is empirically valid** — see section 9 "Watch flags" for the verification and re-evaluation trigger.

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
| GET | `/export/json` | ZIP of 8 JSON files (+ optional land) |
| GET | `/export/copy` | HTML page with copy-to-clipboard buttons for all 8 widget HTML codes (+ optional land) |
| GET | `/export/html` | ZIP of 8 self-contained widget HTML files (+ optional land) |

### Widget Templates (`templates/widgets/`) — see sections 2d–iteration 10 for evolution
| File | Widget | Data key(s) used |
|---|---|---|
| `kpi.html` | 4 KPI cards with animated counters + gauge | `data.kpi[compound]` (compound ∈ all/eshkol/merkaz) |
| `charts.html` | Monthly line chart (count / cumulative / price-by-compound) | `data.charts.count.data` (array), `data.charts.cumulative.data` (array), `data.charts.price.series` (2-line by compound) |
| `pie.html` | Pie chart (by rooms / by price range) | `data.pie[k].data[compound][time]` |
| `rooms_bar.html` | Bar chart by room count (price / size / ppm) | `data.rooms_charts[k].data[compound][time]` |
| `ranges.html` | Line chart: cheap (<4M) vs expensive (>10M) over quarters | `data.price_ranges[cheap|expensive].data` (array, no compound) |
| `transactions.html` | Table: top 10 most/least expensive transactions | `data.transactions[compound][expensive|cheap]` |
| `comparison_bars.html` | Grouped bar: ppm by rooms, אשכול vs מרכז (12mo) | `data.comparison.ppm_by_rooms` |
| `comparison_price_bars.html` | Grouped bar: avg apartment price (₪M) by rooms, אשכול vs מרכז (12mo) | `data.comparison.price_by_rooms` |
| `land.html` | Land cost per unit — line + range band, external tooltip | `data.land_chart.tenders` |

`comparison_summary.html` exists on disk but is no longer registered in `app.py` (replaced by `comparison_price_bars.html` in iteration 5).

### Excel Column Requirements (Main DB)
Required for processing: `תמורה מוצהרת בש"ח`, `מחיר למ״ר`, `שטח`, `שנה`, `חודש`, `יום`, `חדרים`, `שנת בניה`, `סוג עסקה`, **`גוש`**, **`חלקה`** (the last two are used for compound classification).

Rows whose (גוש, חלקה) pair is not in `COMPOUND_MAP` are dropped (treated as not part of Sde Dov). `סוג עסקה` values now have three meanings:
- `אופציה` → counted as transaction, excluded from real-data analysis
- `דירה` → counted as transaction AND included in real-data analysis
- `מימוש אופציה` → NOT counted as transaction (reclassification of existing אופציה), included in real-data analysis

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

6. ~~**gunicorn uses 2 workers**~~ — **resolved in session 4 iteration 6**: `Procfile` now uses `--workers 1`, eliminating both the OOM risk and cross-worker memory inconsistency.

7. **`projects_url` hardcoded** in `generate_all_data()` default (`projects_url="https://sdedov.co.il/projects/"`). Should be editable via UI or env var. (`projects_count` is now per-compound via `COMPOUND_PROJECTS_COUNT` constant — iteration 3.)

8. **`COMPOUND_TOTAL_UNITS` and `COMPOUND_PROJECTS_COUNT` constants** are inline in `generate_lib.py`. Easy to forget when new compounds are added or numbers update. Consider extracting to a config file (or env vars).

9. **`comparison_summary.html` is dead code** — still in `templates/widgets/` but no longer registered in `app.py`. Could be deleted (iteration 5 replaced it with `comparison_price_bars.html`).

---

## 2e. Session 5 — Text/copy review on live page (2026-05-11)

After all session-4 charts deployed to the live Elementor site at `sdedov.co.il/נתוני-שוק-הנדלן-בשדה-דב/`, the live data JSONs were inspected and compared with the Hebrew narrative copy that surrounds the charts. No code changes; only **content/copy** changes were proposed for the user to apply in the WordPress page builder.

### Live data snapshot used for the review (curl from `https://sdedov.co.il/wp-content/uploads/data/`):
- KPI all: total=1,293; avg_ppm=76,456; avg_3rooms=6.41M; avg_4rooms=8.58M; projects=7.
- KPI eshkol: total=520; avg_ppm=82,886; avg_3rooms=6.83M; avg_4rooms=9.65M; projects=5.
- KPI merkaz: total=773; avg_ppm=65,549; avg_3rooms=5.07M; avg_4rooms=6.61M; projects=2.
- Comparison ppm 12mo (אשכול / מרכז): 73,390/67,344 (2 חד), 79,934/64,908 (3), 85,620/64,340 (4), 86,814/66,006 (5).
- Comparison price 12mo (M ₪): 3.34/3.45 (2 חד), 6.35/5.07 (3), 9.70/6.61 (4), 12.14/9.16 (5). Note: 2-room is +3% in merkaz (size: 51.8 vs 44.9 sqm).
- price-ranges: cheap (<4M) overtook expensive (>10M) starting Q4 2025 (cheap 42 vs expensive 22) and stayed higher in Q1+Q2 2026.

### Stale numbers in current page text (need user updates):
1. "מחירה של דירת 4 חדרים בשדה דב עומד בממוצע על כ־9.5 מיליון שקלים" — actual is 8.58M aggregate (was 9.5M before merkaz data entered).
2. "המחיר למ"ר בדירות קטנות (2-3 חדרים) נמוך בכ-4% בהשוואה לדירות גדולות (4-5 חדרים)" — current gap is ~0.4% (merkaz pulled small-apt-ppm up and large-apt-ppm down to near-parity).
3. "דירות שמחירן מעל 10 מיליון שקלים מהוות כ-25% מסך הדירות שנמכרו" — actual is ~19% (160 of 825) because cheaper merkaz units shifted the distribution.
4. "ב־12 החודשים האחרונים נרשמה ירידה של כ־6% במחיר הממוצע למ"ר בדירות 2 חדרים" — still ~-7.7% at aggregate level, but the drop is driven by merkaz mix entering. Needs nuance.
5. "חלקן היחסי [של דירות 2 חדרים] בעסקאות עלה מ־30% ל־36%" — actual is 30% → 34%; close but slightly stale.

### Sections without explanatory copy (need user additions):
- "מחיר דירה ממוצע לפי מס' חדרים — השוואת מתחמים" and "מחיר ממוצע למ"ר לפי מס' חדרים — השוואת מתחמים" — only have the small footnote "האיכלוס במתחם המרכזי צפוי בממוצע כ-3-4 שנים לאחר מתחם אשכול". No introductory paragraph despite being the main new insight in this revision.
- The monthly-ppm time-series chart was split into two compound lines (אשכול / מרכז) in iteration 4, but the narrative above the chart still talks about "המחיר הממוצע למ״ר... שומר על יציבות יחסית" — needs to acknowledge the two-line view.

### Suggested edits delivered to the user (delivered in chat, not in code):
- KPI block: no copy changes (numbers are dynamic per compound).
- Rooms section: replace 9.5M→8.6M (or rephrase to mention compound difference), drop the 4% small/large claim, update 25%→~19% for >10M apartments, and add nuance to the "-6% in 2-room ppm" claim.
- New paragraph above the comparison charts: highlight (a) ~21% ppm discount in merkaz vs eshkol, (b) flat ppm-by-rooms in merkaz vs sloped in eshkol, (c) 2-room counter-example where merkaz is +3% (driven by larger 2-room sizes ~52 vs 45 sqm), (d) connect to the existing הסכמי-אופציה/discounting paragraph as empirical support.
- Time-series section: update the "כמות דירות שנמכרו ומחיר ממוצע למ"ר" preamble to mention the new two-line ppm view (separate lines for eshkol/merkaz, with merkaz starting July 2025).

### Files touched
- PROJECT_STATE.md (this section).

---

## 7. Next Step

**Session 4 has been deployed and is live on Railway and Elementor.** Latest pushed iterations: 1–10 (compound classification → OOM fix → height alignment → mobile-responsive → Jinja `{#` gotcha fix). **Session 5 was content-only — see section 2e.**

When new Excel data arrives (e.g. May 2026):
1. Upload it via the dashboard at `/` — no code changes required, generates the full new schema automatically.
2. Verify the dashboard renders correctly (open `/`, switch compound filters per widget, confirm comparison section).
3. Download `sdedov-data.zip` from `/export/json`, upload contents to WordPress `/wp-content/uploads/data/`. JSON files are:
   - `shadeh-dov-kpi.json` — `{compound: {...}}` per compound
   - `shadeh-dov-charts.json` — `count`/`cumulative` are plain arrays, `price` uses `.series` (2-line)
   - `shadeh-dov-pie-charts.json` — `data[compound][time]`
   - `shadeh-dov-rooms-charts.json` — same shape as pie
   - `shadeh-dov-price-ranges.json` — plain arrays
   - `shadeh-dov-transactions.json` — `{compound: {expensive, cheap}}`
   - `shadeh-dov-comparison.json` — `{ppm_by_rooms, price_by_rooms}`
   - `shadeh-dov-meta.json` — `total_count`, `total_real`, `compounds`, `by_type`, `date_range`
4. If anything has changed in the widget templates since the last paste, re-copy the HTML from `/export/copy` into the corresponding Elementor HTML widgets.

**Open questions / future work**: see TODO list below.

---

## 8. Short TODO List

- [ ] Delete `templates/widgets/pie_rooms.html` (replaced by `pie.html` + `rooms_bar.html`, still an unused file)
- [ ] Delete or archive `generate.py` and `serve.py` (legacy, not used by Flask)
- [ ] Add `projects_count` editing UI (now per-compound via `COMPOUND_PROJECTS_COUNT` inline constant; ideally editable without code change)
- [ ] Delete unused `templates/widgets/comparison_summary.html` (replaced by `comparison_price_bars.html` in iteration 5)
- [ ] Delete unused `templates/widgets/pie_rooms.html` (replaced earlier in session 2)
- [ ] Delete or archive `generate.py` and `serve.py` (legacy, not used by Flask)
- [ ] Remove debug `.error.txt` logic from `/export/html` route (or gate behind `DEBUG` flag)
- [x] ~~Consider fixing gunicorn to 1 worker~~ — done in iteration 6
- [ ] Add column-name validation in `generate_all_data()` with a clear error message listing missing columns (including new `גוש`/`חלקה` requirement)
- [ ] Test land widget appearance in actual Elementor (confirm tooltip CSS, SVG legend, toggle behavior match live site)
- [ ] Consider `.gitignore`-ing the `preview/` folder — currently committed copies (~300KB each with Chart.js inlined) bloat the repo
- [ ] Consider extracting `COMPOUND_MAP`, `COMPOUND_TOTAL_UNITS`, `COMPOUND_PROJECTS_COUNT` to a config file so they're easier to maintain

---

## 9. Notes for Future Sessions

### How to resume:
1. Read this file first
2. Check `git log --oneline -10` to see recent commits
3. The app is live on Railway — just push to `main` branch to deploy
4. Password: set via `APP_PASSWORD` env var on Railway (default: `sdedov2024`)

### Watch flags (re-evaluate when triggered):
- **6896/204 compound assignment** (currently 100% מרכז in `COMPOUND_MAP`):
  Plot 6896/204 actually contains projects from multiple compounds — 5 are מרכז (גינדי, חג׳ג׳, א.א.י, האחים ישראל) and 1 is אשכול (אוטופיה). We classify the entire plot as מרכז because verification at session-4 time showed: (a) all 80 transactions in this plot started **July 2025 or later** — exactly aligned with the central-compound selling onset, with **zero pre-June-2025 transactions**; (b) all 80 rows have **build year 2034** (planning year of the central-compound projects), whereas other אוטופיה rows in the data (from גוש 6634) all have **build year 2029**. So no observable אוטופיה sales here yet.
  **Re-evaluation trigger**: if a future Excel upload shows transactions in 6896/204 with **build year ≠ 2034** (especially 2029), or with sale dates **before June 2025**, those are likely אוטופיה rows and the compound classification needs to become row-level (e.g., split 6896/204 by `שנת בניה`: 2034→מרכז, 2029→אשכול) rather than plot-level.

### Jinja2 gotcha (IMPORTANT):
- Widget templates use `{{ data.xxx | tojson }}` to embed data
- **Never let `{#` appear adjacent in CSS within widget templates** — Jinja2 parses `{#` as the start of a comment and `{# … #}` as the comment block. If it can't find a closing `#}`, render fails with `"Missing end of comment tag"` (see iteration 10).
- **The most common trap** is the one-liner media query: `@media (max-width:600px){#some-id{...}}` — the `){#` is fine but the `){` right before `#some-id` is NOT (it parses as `…){ #some-id …` which contains `{#`). Concretely the danger is **any opening brace immediately followed by `#`**.
- Example fixes:
  - Add a space: `{ #id-selector {`
  - Or split to multiple lines: `@media ... { \n  #id { ... } \n }`
  - Or for risky blocks: wrap in `{% raw %}` / `{% endraw %}` (Jinja ignores everything inside).

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
- Main DB: one row per transaction; columns in Hebrew. Required columns also include `גוש`, `חלקה` (used for compound classification — see section 2d).
- Land DB: one row per **winner** within a tender; grouped by `סדר כרונולוגי`
- `סוג עסקה` values:
  - `אופציה` — counted as transaction, but excluded from price/sqm/ppm analysis (no real values)
  - `דירה` — counted as transaction AND included in real-data analysis
  - `מימוש אופציה` — **NOT** counted as transaction (it's a re-classification of a prior `אופציה`), BUT included in real-data analysis (full price/sqm/ppm values)
- Rows whose `(גוש, חלקה)` is not in `COMPOUND_MAP` are dropped (treated as not Sde Dov)
- Land date format: `DD.M.YY` (e.g. `23.8.21`) — custom parser in `generate_land_chart_data`

### Elementor integration:
- `/export/copy` page now outputs **fragment HTML** (no `<!DOCTYPE>`, `<html>`, `<head>`, `<body>` wrappers) via `strip_to_fragment()` in `app.py`. This is required — Elementor HTML widgets are embedded directly in the page body, not in iframes.
- Fragment starts with `<style>@import url('...');</style>` then the widget content.
- The internal Flask widget templates (`templates/widgets/*.html`) remain full `<!DOCTYPE html>` documents (needed for the dashboard to work); `strip_to_fragment()` converts them at export time.
- **CRITICAL**: All widget JS must be wrapped in an IIFE `(function(){...})()` to avoid `const`/`let` redeclaration errors when multiple widgets share the same page scope.
- User copies HTML from `/export/copy` page and pastes into Elementor HTML widget.
- Live site dynamic JSON fetch: widgets on the live Elementor site also fetch JSON from `https://sdedov.co.il/wp-content/uploads/data/`. The baked-in (Flask-exported) version and the dynamic (live) version are functionally equivalent but different codebases.
- All fonts/CDN resources load from external URLs (Chart.js CDN, Google Fonts)
- **When Elementor override CSS causes visual bugs**: use `!important` on `border`, `background`, `outline`, `box-shadow` in both base and `:focus`/`.active` states.

---

*This file was generated and should be updated at the end of every dev session.*
