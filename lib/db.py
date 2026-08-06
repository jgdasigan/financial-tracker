"""Postgres access layer.

Works against any plain Postgres connection string, so the same code targets
a free Supabase or Neon database — nothing here is provider-specific. Point
DB_URL (via st.secrets or the DB_URL env var) at whichever one you created.
"""
from __future__ import annotations

import os
from datetime import date

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bills (
    id                      SERIAL PRIMARY KEY,
    name                    TEXT NOT NULL,
    bill_type               TEXT NOT NULL CHECK (bill_type IN ('recurring', 'installment', 'onetime', 'pakaskas')),
    base_amount             NUMERIC NOT NULL,
    conversion_fee          NUMERIC NOT NULL DEFAULT 0,
    start_month             DATE NOT NULL,
    duration_months         INTEGER,
    card                    TEXT,
    due_day                 INTEGER NOT NULL DEFAULT 1 CHECK (due_day BETWEEN 1 AND 31),
    -- Pakaskas (lending to someone else / a payment you're fronting that
    -- gets reimbursed) still gets tracked and shown, but sometimes it's
    -- money that was never really yours to begin with, so this lets it opt
    -- out of the leftover/savings math while staying visible everywhere else.
    include_in_projection   BOOLEAN NOT NULL DEFAULT true,
    notes                   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS income_entries (
    id           SERIAL PRIMARY KEY,
    month        DATE NOT NULL,
    week_number  INTEGER NOT NULL CHECK (week_number BETWEEN 1 AND 4),
    amount       NUMERIC NOT NULL,
    notes        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Monthly income can be more than one stream (day job + side gig, etc.) —
-- "monthly income" everywhere else in the app is the sum of these.
CREATE TABLE IF NOT EXISTS income_sources (
    id           SERIAL PRIMARY KEY,
    name         TEXT NOT NULL,
    amount       NUMERIC NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Card/tag names a user has explicitly registered, so a new tag can be
-- picked from the Manage bills table's dropdown before any bill uses it —
-- distinct from list_card_tags(), which only sees tags already in use.
CREATE TABLE IF NOT EXISTS tags (
    id    SERIAL PRIMARY KEY,
    name  TEXT UNIQUE NOT NULL
);

-- One-off income landing in a specific month (13th month pay, a bonus, a
-- tax refund, ...) — added on top of the recurring income_sources total for
-- that month only, so the projection actually shows the bump.
CREATE TABLE IF NOT EXISTS income_bonuses (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    month       DATE NOT NULL,
    amount      NUMERIC NOT NULL,
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

# Run against every existing table too, so a database created before a given
# column existed (card tags, due-day, ...) picks it up without losing rows.
MIGRATIONS = [
    "ALTER TABLE bills ADD COLUMN IF NOT EXISTS card TEXT;",
    "ALTER TABLE bills ADD COLUMN IF NOT EXISTS due_day INTEGER NOT NULL DEFAULT 1;",
    "ALTER TABLE bills ADD COLUMN IF NOT EXISTS include_in_projection BOOLEAN NOT NULL DEFAULT true;",
    # CHECK constraints can't be altered in place — drop and recreate with
    # the new allowed value. Uses Postgres's default auto-generated name for
    # an unnamed column CHECK, which is what CREATE TABLE above produces.
    "ALTER TABLE bills DROP CONSTRAINT IF EXISTS bills_bill_type_check;",
    "ALTER TABLE bills ADD CONSTRAINT bills_bill_type_check "
    "CHECK (bill_type IN ('recurring', 'installment', 'onetime', 'pakaskas'));",
    # One income figure per (month, week) — logging the same week again edits
    # it in place instead of piling up duplicate rows.
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_income_entries_month_week "
    "ON income_entries (month, week_number);",
]

# Cards the affordability checker and manage-bills form offer by name; users
# can still type a custom tag via the "Other" option in the UI.
KNOWN_CARDS = ["RCBC", "BDO"]

DEFAULT_SETTINGS = {
    "monthly_income": "0",
    "current_savings": "0",
    "safety_buffer": "0",
}


def _connection_string() -> str:
    url = None
    try:
        url = st.secrets["DB_URL"]
    except Exception:
        pass
    url = url or os.environ.get("DB_URL")
    if not url:
        raise RuntimeError(
            "No database connection string found. Add DB_URL to "
            ".streamlit/secrets.toml (see secrets.toml.example) or set the "
            "DB_URL environment variable."
        )
    # SQLAlchemy wants the psycopg2 dialect explicitly.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


@st.cache_resource(show_spinner=False)
def get_engine() -> Engine:
    engine = create_engine(_connection_string(), pool_pre_ping=True)
    with engine.begin() as conn:
        for statement in SCHEMA.strip().split(";\n\n"):
            if statement.strip():
                conn.execute(text(statement))
        for statement in MIGRATIONS:
            conn.execute(text(statement))
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                text(
                    "INSERT INTO settings (key, value) VALUES (:k, :v) "
                    "ON CONFLICT (key) DO NOTHING"
                ),
                {"k": key, "v": value},
            )
        # One-time upgrade path: monthly income used to be a single settings
        # value. If nobody has logged any income source yet but an old
        # single-value setting exists, carry it over instead of silently
        # resetting income to zero.
        source_count = conn.execute(text("SELECT COUNT(*) FROM income_sources")).scalar()
        if source_count == 0:
            legacy = conn.execute(
                text("SELECT value FROM settings WHERE key = 'monthly_income'")
            ).scalar()
            if legacy and float(legacy) > 0:
                conn.execute(
                    text("INSERT INTO income_sources (name, amount) VALUES ('Income', :amt)"),
                    {"amt": float(legacy)},
                )
    return engine


# ---------------------------------------------------------------- settings --

def get_settings() -> dict:
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT key, value FROM settings")).fetchall()
    values = {k: v for k, v in rows}
    return {
        "monthly_income": total_income(),  # sum of income_sources — see below
        "current_savings": float(values.get("current_savings", 0) or 0),
        "safety_buffer": float(values.get("safety_buffer", 0) or 0),
    }


def save_settings(current_savings: float, safety_buffer: float) -> None:
    engine = get_engine()
    updates = {
        "current_savings": current_savings,
        "safety_buffer": safety_buffer,
    }
    with engine.begin() as conn:
        for key, value in updates.items():
            conn.execute(
                text(
                    "INSERT INTO settings (key, value) VALUES (:k, :v) "
                    "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
                ),
                {"k": key, "v": str(value)},
            )


# --------------------------------------------------------------- income sources --
# Monthly income can come from more than one stream (day job, side gig, …);
# the single "monthly income" figure used everywhere else is their sum.

def list_income_sources() -> pd.DataFrame:
    engine = get_engine()
    with engine.begin() as conn:
        return pd.read_sql(
            text("SELECT id, name, amount FROM income_sources ORDER BY id"), conn,
        )


def total_income() -> float:
    engine = get_engine()
    with engine.begin() as conn:
        total = conn.execute(text("SELECT COALESCE(SUM(amount), 0) FROM income_sources")).scalar()
    return float(total or 0)


def add_income_source(name: str, amount: float) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO income_sources (name, amount) VALUES (:name, :amount)"),
            {"name": name, "amount": amount},
        )


def delete_income_source(source_id: int) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM income_sources WHERE id = :id"), {"id": source_id})


# --------------------------------------------------------------- income bonuses --
# One-off income tied to a specific month (a December bonus, a tax refund, …)
# — separate from the recurring income_sources total, added on top of it
# only for the month it lands in.

def list_income_bonuses() -> pd.DataFrame:
    engine = get_engine()
    with engine.begin() as conn:
        return pd.read_sql(
            text("SELECT id, name, month, amount, notes FROM income_bonuses ORDER BY month, id"), conn,
        )


def add_income_bonus(name: str, month: date, amount: float, notes: str = "") -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO income_bonuses (name, month, amount, notes) "
                "VALUES (:name, :month, :amount, :notes)"
            ),
            {"name": name, "month": month, "amount": amount, "notes": notes},
        )


def delete_income_bonus(bonus_id: int) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM income_bonuses WHERE id = :id"), {"id": bonus_id})


# -------------------------------------------------------------------- bills --

def list_bills() -> pd.DataFrame:
    engine = get_engine()
    with engine.begin() as conn:
        df = pd.read_sql(
            text(
                "SELECT id, name, bill_type, base_amount, conversion_fee, "
                "start_month, duration_months, card, due_day, include_in_projection, notes "
                "FROM bills ORDER BY start_month, name"
            ),
            conn,
        )
    return df


def list_card_tags() -> list[str]:
    """Distinct card tags already used on any bill, including custom ones the
    user has typed before — so they show up again as pickable options."""
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT DISTINCT card FROM bills WHERE card IS NOT NULL ORDER BY card")
        ).fetchall()
    return [r[0] for r in rows]


def add_tag(name: str) -> None:
    """Register a new card/tag name so it's pickable even before any bill
    uses it — e.g. from the Manage bills table's dropdown."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO tags (name) VALUES (:name) ON CONFLICT (name) DO NOTHING"),
            {"name": name},
        )


def list_all_tags() -> list[str]:
    """Every card/tag a user could pick: the built-ins, anything explicitly
    registered via add_tag, and anything already in use on a bill."""
    return sorted(set(KNOWN_CARDS) | set(_list_registered_tags()) | set(list_card_tags()))


def _list_registered_tags() -> list[str]:
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT name FROM tags ORDER BY name")).fetchall()
    return [r[0] for r in rows]


def add_bill(
    name: str,
    bill_type: str,
    base_amount: float,
    conversion_fee: float,
    start_month: date,
    duration_months: int | None,
    card: str | None = None,
    due_day: int = 1,
    include_in_projection: bool = True,
    notes: str = "",
) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO bills (name, bill_type, base_amount, conversion_fee, "
                "start_month, duration_months, card, due_day, include_in_projection, notes) "
                "VALUES (:name, :bill_type, :base_amount, :conversion_fee, "
                ":start_month, :duration_months, :card, :due_day, :include_in_projection, :notes)"
            ),
            {
                "name": name,
                "bill_type": bill_type,
                "base_amount": base_amount,
                "conversion_fee": conversion_fee,
                "start_month": start_month,
                "duration_months": duration_months,
                "card": card,
                "due_day": due_day,
                "include_in_projection": include_in_projection,
                "notes": notes,
            },
        )


def update_bill(bill_id: int, **fields) -> None:
    if not fields:
        return
    engine = get_engine()
    set_clause = ", ".join(f"{col} = :{col}" for col in fields)
    fields["id"] = bill_id
    with engine.begin() as conn:
        conn.execute(text(f"UPDATE bills SET {set_clause} WHERE id = :id"), fields)


def delete_bill(bill_id: int) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM bills WHERE id = :id"), {"id": bill_id})


# ------------------------------------------------------------ income entries --
# One row per paycheck: "which week of which month did this land in, and how
# much was it" — mirrors the handwritten weekly income log directly.

def list_income_entries() -> pd.DataFrame:
    engine = get_engine()
    with engine.begin() as conn:
        df = pd.read_sql(
            text(
                "SELECT id, month, week_number, amount, notes FROM income_entries "
                "ORDER BY month, week_number"
            ),
            conn,
        )
    return df


def upsert_income_entry(month: date, week_number: int, amount: float, notes: str = "") -> None:
    """Logging the same (month, week) again edits that week's figure in
    place, rather than creating a second row for it."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO income_entries (month, week_number, amount, notes) "
                "VALUES (:month, :week_number, :amount, :notes) "
                "ON CONFLICT (month, week_number) DO UPDATE "
                "SET amount = EXCLUDED.amount, notes = EXCLUDED.notes"
            ),
            {"month": month, "week_number": week_number, "amount": amount, "notes": notes},
        )


def delete_income_entry(entry_id: int) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM income_entries WHERE id = :id"), {"id": entry_id})
