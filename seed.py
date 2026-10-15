"""
Seed script for PaisaPal.
Creates 3 users, default categories, 60+ transactions over last 2 months,
and budgets for at least 4 categories.
Run after schema.sql.
"""

import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = "paisapal.db"

CATEGORIES = [
    "Food", "Travel", "Rent", "Shopping", "Bills", "Entertainment", "Other"
]

USERS = [
    ("Rahul Sharma", 25000),
    ("Priya Singh", 18000),
    ("Amit Kumar", 32000),
]

def seed():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for name in CATEGORIES:
        cur.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))
    conn.commit()

    for name, income in USERS:
        cur.execute(
            "INSERT INTO users (name, monthly_income) VALUES (?, ?)",
            (name, income)
        )
    conn.commit()

    cur.execute("SELECT category_id, name FROM categories")
    cat_map = {name: cid for cid, name in cur.fetchall()}

    today = datetime.now().date()
    notes_map = {
        "Food": ["pizza", "biryani", "coffee", "groceries", "lunch", "snacks"],
        "Travel": ["auto", "metro", "uber", "bus"],
        "Shopping": ["clothes", "shoes", "amazon", "stationery"],
        "Entertainment": ["movie", "netflix", "party", "game"],
        "Bills": ["electricity", "wifi", "mobile recharge"],
        "Other": ["misc", "gift", "medicine"],
    }

    txn_count = 0
    for user_id in range(1, 4):
        for day_offset in range(60, 0, -1):
            date = today - timedelta(days=day_offset)
            if random.random() < 0.7:
                for _ in range(random.randint(1, 2)):
                    cat_name = random.choice(list(notes_map.keys()))
                    amount = round(random.uniform(50, 800), 2)
                    note = random.choice(notes_map[cat_name])
                    txn_type = "EXPENSE" if random.random() > 0.1 else "INCOME"
                    if txn_type == "INCOME":
                        amount = round(random.uniform(500, 5000), 2)
                        cat_name = None
                        note = "salary / allowance"

                    cur.execute(
                        """INSERT INTO transactions
                           (user_id, amount, type, category_id, note, txn_date)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (user_id, amount, txn_type,
                         cat_map.get(cat_name), note, date.isoformat())
                    )
                    txn_count += 1

    current_month = today.strftime("%Y-%m")
    budget_data = [
        (1, cat_map["Food"], current_month, 4000),
        (1, cat_map["Shopping"], current_month, 3000),
        (1, cat_map["Entertainment"], current_month, 2000),
        (1, cat_map["Travel"], current_month, 2500),
        (2, cat_map["Food"], current_month, 3500),
        (3, cat_map["Shopping"], current_month, 5000),
    ]
    for uid, cid, month, limit in budget_data:
        cur.execute(
            """INSERT OR REPLACE INTO budgets
               (user_id, category_id, month, limit_amount)
               VALUES (?, ?, ?, ?)""",
            (uid, cid, month, limit)
        )

    conn.commit()
    conn.close()
    print(f"Seed complete. Inserted ~{txn_count} transactions.")

if __name__ == "__main__":
    seed()
