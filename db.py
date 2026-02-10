from sqlalchemy import (
    create_engine, Table, Column,
    Integer, Float, String, MetaData, DateTime, select
)
from datetime import datetime, timedelta

engine = create_engine("sqlite:///expenses.db")
metadata = MetaData()

expenses = Table(
    "expenses",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer),
    Column("amount", Float),
    Column("category", String),
    Column("created_at", DateTime, default=datetime.utcnow),
)

balances = Table(
    "balances",
    metadata,
    Column("user_id", Integer, primary_key=True),
    Column("balance", Float, default=0),
)


def init_db():
    metadata.create_all(engine)


def add_expense(user_id, amount, category):
    with engine.begin() as conn:
        conn.execute(
            expenses.insert().values(
                user_id=user_id,
                amount=amount,
                category=category,
                created_at=datetime.utcnow(),
            )
        )


def get_stats(user_id, days):
    since = datetime.utcnow() - timedelta(days=days)

    with engine.begin() as conn:
        rows = conn.execute(
            select(expenses.c.category, expenses.c.amount)
            .where(expenses.c.user_id == user_id)
            .where(expenses.c.created_at >= since)
        ).fetchall()

    if not rows:
        return None

    stats = {}
    for cat, amt in rows:
        stats[cat] = stats.get(cat, 0) + amt

    return stats


def get_balance(user_id):
    with engine.begin() as conn:
        row = conn.execute(
            select(balances.c.balance).where(balances.c.user_id == user_id)
        ).fetchone()
    return row[0] if row else 0.0


def set_balance(user_id, amount):
    with engine.begin() as conn:
        conn.execute(balances.delete().where(balances.c.user_id == user_id))
        conn.execute(balances.insert().values(user_id=user_id, balance=amount))


def add_to_balance(user_id, amount):
    current = get_balance(user_id)
    set_balance(user_id, current + amount)