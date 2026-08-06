# Bill & Savings Tracker

A small Streamlit app that projects your monthly bills and savings, and checks
whether a new purchase — on installment or in cash — still fits your budget:
the same check as the handwritten "Payments Schedule" table, automated.

The whole app sits behind a single shared password (`APP_PASSWORD` in
secrets — see setup below) — there's no per-user account system, just a
login gate, since this is built for one person.

## Pages

- **Dashboard** — KPI cards, a credit-card visual per card tag (RCBC/BDO/…)
  showing what's due on that card **this month**, a "card payments due by
  month" chart + table (same idea, projected forward, alongside the
  projected savings balance), an income vs. bills vs. savings chart, an
  "upcoming payments" list, and the full payments schedule split into
  **Installments / Recurring / One-time / Pakaskas** tables (each with a
  Total row, sized to show every month with no inner scrollbar), filterable
  by card/tag. The "Monthly income" KPI relabels to "(incl. bonus)" for any
  month a one-time income entry (see Settings) lands in.
- **Manage bills** — the "Current bills" table is directly editable: change
  any cell, delete a row from its ⋮ menu, or fill in the blank bottom row to
  add one — Save commits everything at once (or Undo discards it). The
  "Card / tag" column is a dropdown built from RCBC/BDO plus every tag
  you've used or registered; the box above the table registers a brand-new
  tag so it's pickable there without needing a bill on it yet first. Each
  bill also has a **due day of month**, used by the Weekly income page, and
  an optional card/tag regardless of type.
- **Affordability checker** — model a prospective purchase either as a
  **card installment** or as **cash paid straight from savings**, and see
  whether it still fits:
  - *Card*: is your monthly leftover (income minus bills) staying at or
    above your buffer for the length of the term?
  - *Cash*: does your current savings, minus this price, stay at or above
    your buffer *right now*?
  One button saves it as a real bill once you decide to buy.
- **Weekly income** — for a variable, weekly-paid income stream: log what a
  given week's paycheck was (per month, 1st–4th week — the common "sweldo"
  payroll split, not calendar weeks), and see it checked against whichever
  bills have their due day inside that same week, before the next paycheck
  lands. Logging the same week again edits that figure in place.
- **Settings** — one row per **income source** (day job, side gig, …; the
  total is what every other page calls "monthly income"), plus **one-time
  income** (a December bonus, 13th month pay, a tax refund, …) that adds on
  top of that total for just the month it's logged against, current
  savings, and the minimum leftover/savings buffer.

## Data model

Four bill types, matching how the original table actually behaved:

| Type | Behavior |
|---|---|
| `recurring` | Same amount every month from a start month, forever or for a fixed number of months (e.g. a subscription). |
| `installment` | A monthly amount for N months; the **first month adds a one-time conversion fee** on top (e.g. the shoes/glasses/appliance rows). Optionally tagged with the `card` it's on (RCBC, BDO, or a custom tag). |
| `onetime` | A single charge in a single month (e.g. groceries, or a cash purchase from the affordability checker). |
| `pakaskas` | Money you're lending out or fronting for reimbursement — same monthly-amount-for-N-months shape as `installment`, tracked in its own table, with a per-row **"count against my leftover/savings"** checkbox (`include_in_projection`) since it's sometimes not really your money. Unchecking it removes it from the leftover/savings math but **not** from a card's "due this month" figure — the card bill is still due either way, regardless of whose money is paying it. |

Every bill also has a `due_day` (1–31, defaults to 1) used only by the
Weekly income page to bucket it into that month's 1st/2nd/3rd/4th week.

Income entries are a separate table: one row per `(month, week_number)`,
matching the handwritten weekly income log directly. Income *sources* are
yet another table — one row per stream (name + monthly amount); "monthly
income" everywhere else in the app is just their sum. Upgrading from an
older version of this app that had a single monthly-income number carries
that number over automatically as one source, the first time the app
connects to the database — see `lib/db.py`. Income *bonuses* are a fourth
table — one row per one-time amount tied to a specific month; more than one
landing in the same month (e.g. a bonus and 13th month pay both in
December) just sum together for that month.

Everything is computed on the fly from these rows — there's no separate
"schedule" table to keep in sync.

## 1. Set up a free Postgres database

Data is stored in Postgres so it survives restarts once this is deployed
(a local SQLite file would reset every time Streamlit Community Cloud
redeploys or restarts the app). Either free tier works, nothing in the code
is provider-specific:

- **Supabase** (recommended, generous free tier): create a project at
  [supabase.com](https://supabase.com) → Project Settings → Database →
  Connection string → **URI**. If your network is IPv4-only, use the
  "Session pooler" connection string instead of the direct one.

You get something like:

```
postgresql://USER:PASSWORD@HOST:PORT/DBNAME
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and paste
your connection string in as `DB_URL`, plus pick a value for `APP_PASSWORD`
(the login gate — see `lib/auth.py`). **That file only** is gitignored —
never paste a real password anywhere else in the repo (a README, a comment,
a commit message); anything outside `secrets.toml` is fair game to end up on
a public GitHub repo once you deploy.

Tables (and any new columns, like the `card` tag) are created/migrated
automatically the first time the app connects (see `lib/db.py`) — there's no
migration step to run by hand.

## 2. Run it locally

```bash
cd financial-tracker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`. Add a couple of bills, set your income and
current savings on **Settings**, then check the Dashboard.

## 3. Deploy for free (when you're ready)

Streamlit Community Cloud hosts apps for free from a GitHub repo — **public
or private**. The free tier allows unlimited public apps but only **one**
private app; given this holds real financial data, private is the right
call, and one is all you need.

1. Commit everything except `.streamlit/secrets.toml` (already gitignored —
   double check `git status` doesn't show it before pushing), push to a new
   **private** GitHub repo.
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app → point
   it at the repo, branch, and `app.py`. The first time you connect a
   private repo, GitHub will prompt you to grant Streamlit's app access to
   it specifically (it reads the repo via a read-only deploy key, not full
   account access).
3. In the app's **Settings → Secrets**, paste the same `DB_URL` and
   `APP_PASSWORD` lines you put in your local `secrets.toml`. This is how
   the hosted app reaches your Supabase/Neon database and gates access —
   the file itself never leaves your machine.
4. Deploy. The app's filesystem resets on every redeploy/restart, but since
   all your data lives in Postgres, that's harmless.

## Project layout

```
app.py                                # Navigation router + global theme/CSS
views/dashboard.py                    # Dashboard
views/manage_bills.py                 # Add/edit/delete bills
views/affordability_checker.py        # Card vs. cash affordability check
views/weekly_income.py                # Weekly income vs. bills-due-that-week check
views/settings.py                     # Income sources, savings, buffer
lib/auth.py                           # single-user password gate
lib/db.py                             # Postgres connection + CRUD
lib/calculations.py                   # schedule/projection/affordability math (pure functions)
lib/bill_edits.py                     # diffing logic for the editable bills table (unit-testable, no Streamlit)
lib/theme.py                          # dark color palette constants
lib/style.py                          # card CSS + credit-card visual + pill/loader helpers
.streamlit/config.toml                # pinned dark theme
.streamlit/secrets.toml.example
```
