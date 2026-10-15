import sqlite3
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import re

DB_PATH = "paisapal.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- Helpers ----------

def parse_relative_date(text: str, today=None) -> str:
    """Convert 'yesterday', 'today', 'last Monday', etc. to YYYY-MM-DD."""
    if today is None:
        today = datetime.now().date()
    text = text.lower().strip()

    if text in ("today", "aaj"):
        return today.isoformat()
    if text in ("yesterday", "kal"):
        return (today - timedelta(days=1)).isoformat()
    if text in ("tomorrow", "kal"):
        return (today + timedelta(days=1)).isoformat()

    # last Monday and last Friday type stuff.
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, d in enumerate(days):
        if f"last {d}" in text or f"last {d[:3]}" in text:
            target = (today.weekday() - i) % 7
            if target == 0:
                target = 7
            return (today - timedelta(days=target)).isoformat()

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b", "%d %B"):
        try:
            parsed = datetime.strptime(text, fmt).date()
            if parsed.year == 1900:
                parsed = parsed.replace(year=today.year)
            return parsed.isoformat()
        except ValueError:
            continue

    return today.isoformat() 


def get_category_id(name: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT category_id FROM categories WHERE lower(name) = lower(?)",
        (name.strip(),)
    )
    row = cur.fetchone()
    conn.close()
    return row["category_id"] if row else None


# ---------- Required Tools ----------

def add_transaction(user_id: int, amount: float, category: str, note: str, date_text: str, txn_type: str = "EXPENSE"):
    """Insert a transaction. Agent should extract fields first."""
    if amount <= 0:
        return {"error": "Amount must be positive."}

    date_iso = parse_relative_date(date_text)
    cat_id = get_category_id(category) if category else None

    if txn_type == "EXPENSE" and not cat_id:
        return {"error": f"Unknown category '{category}'. Available: Food, Travel, Rent, Shopping, Bills, Entertainment, Other."}

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO transactions
           (user_id, amount, type, category_id, note, txn_date)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, amount, txn_type.upper(), cat_id, note, date_iso)
    )
    txn_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Check budget warning
    warning = None
    if txn_type.upper() == "EXPENSE" and cat_id:
        status = check_budget_status(user_id)
        for s in status.get("categories", []):
            if s["category"].lower() == category.lower() and s["percent"] >= 80:
                warning = s["message"]

    return {
        "success": True,
        "txn_id": txn_id,
        "message": f"Added {txn_type.lower()} of ₹{amount} on {date_iso}.",
        "budget_warning": warning
    }


def list_transactions(user_id: int, start_date: str = None, end_date: str = None,
                      category: str = None, txn_type: str = None, limit: int = 20):
    conn = get_conn()
    cur = conn.cursor()

    query = """
        SELECT t.txn_id, t.amount, t.type, c.name as category, t.note, t.txn_date
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.category_id
        WHERE t.user_id = ?
    """
    params = [user_id]

    if start_date:
        query += " AND t.txn_date >= ?"
        params.append(parse_relative_date(start_date))
    if end_date:
        query += " AND t.txn_date <= ?"
        params.append(parse_relative_date(end_date))
    if category:
        query += " AND lower(c.name) = lower(?)"
        params.append(category)
    if txn_type:
        query += " AND t.type = ?"
        params.append(txn_type.upper())

    query += " ORDER BY t.txn_date DESC LIMIT ?"
    params.append(limit)

    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"transactions": rows, "count": len(rows)}


def get_spending_summary(user_id: int, month: str = None):
    """Total per category for a month, with % of total."""
    if not month:
        month = datetime.now().strftime("%Y-%m")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.name as category, SUM(t.amount) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.category_id
        WHERE t.user_id = ? AND t.type = 'EXPENSE'
          AND strftime('%Y-%m', t.txn_date) = ?
        GROUP BY c.category_id
        ORDER BY total DESC
        """,
        (user_id, month)
    )
    rows = cur.fetchall()
    conn.close()

    grand_total = sum(r["total"] for r in rows) or 1
    summary = []
    for r in rows:
        pct = round((r["total"] / grand_total) * 100, 1)
        summary.append({
            "category": r["category"],
            "total": round(r["total"], 2),
            "percent": pct
        })

    return {"month": month, "total_spent": round(grand_total, 2), "by_category": summary}


def set_budget(user_id: int, category: str, month: str, limit_amount: float):
    cat_id = get_category_id(category)
    if not cat_id:
        return {"error": f"Unknown category '{category}'."}
    if limit_amount <= 0:
        return {"error": "Budget limit must be positive."}

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO budgets (user_id, category_id, month, limit_amount)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id, category_id, month)
           DO UPDATE SET limit_amount = excluded.limit_amount""",
        (user_id, cat_id, month, limit_amount)
    )
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Budget for {category} in {month} set to ₹{limit_amount}."}


def check_budget_status(user_id: int, month: str = None):
    if not month:
        month = datetime.now().strftime("%Y-%m")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.name as category, b.limit_amount,
               COALESCE(SUM(t.amount), 0) as spent
        FROM budgets b
        JOIN categories c ON b.category_id = c.category_id
        LEFT JOIN transactions t ON t.user_id = b.user_id
            AND t.category_id = b.category_id
            AND t.type = 'EXPENSE'
            AND strftime('%Y-%m', t.txn_date) = b.month
        WHERE b.user_id = ? AND b.month = ?
        GROUP BY b.budget_id
        """,
        (user_id, month)
    )
    rows = cur.fetchall()
    conn.close()

    result = []
    for r in rows:
        spent = r["spent"]
        limit = r["limit_amount"]
        pct = round((spent / limit) * 100, 1) if limit else 0
        msg = None
        if pct >= 100:
            msg = f"ALERT: {r['category']} is OVER budget (₹{spent:.0f} / ₹{limit:.0f})."
        elif pct >= 80:
            msg = f"Warning: {r['category']} is at {pct}% of budget."
        result.append({
            "category": r["category"],
            "spent": round(spent, 2),
            "limit": limit,
            "percent": pct,
            "message": msg
        })

    return {"month": month, "categories": result}


def delete_transaction(txn_id: int, user_id: int):
    """Delete only after agent has confirmed with user."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM transactions WHERE txn_id = ? AND user_id = ?",
        (txn_id, user_id)
    )
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    if deleted:
        return {"success": True, "message": f"Transaction {txn_id} deleted."}
    return {"error": "Transaction not found or not yours."}


# ----- all utility for mr agent ----------

def get_or_create_user(name: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE lower(name) = lower(?)", (name,))
    row = cur.fetchone()
    if row:
        uid = row["user_id"]
    else:
        cur.execute("INSERT INTO users (name) VALUES (?)", (name,))
        uid = cur.lastrowid
        conn.commit()
    conn.close()
    return uid
