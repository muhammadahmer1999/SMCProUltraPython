import sqlite3
import os
from datetime import datetime

class HistoryManager:
    def __init__(self, db_path="trade_history.db"):
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    quantity REAL NOT NULL,
                    pnl REAL,
                    entry_time DATETIME NOT NULL,
                    exit_time DATETIME,
                    is_closed INTEGER DEFAULT 0
                )
            ''')
            conn.commit()

    def log_entry(self, symbol, side, entry_price, quantity):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO trades (symbol, side, entry_price, quantity, entry_time, is_closed)
                VALUES (?, ?, ?, ?, ?, 0)
            ''', (symbol, side, entry_price, quantity, datetime.now()))
            conn.commit()

    def get_open_trades(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM trades WHERE is_closed = 0')
            rows = cursor.fetchall()
            trades = []
            for row in rows:
                trades.append({
                    'id': row[0],
                    'symbol': row[1],
                    'side': row[2],
                    'entry_price': row[3],
                    'quantity': row[5],
                    'entry_time': row[7]
                })
            return trades

    def close_trade(self, id, exit_price, pnl):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE trades 
                SET exit_price = ?, pnl = ?, exit_time = ?, is_closed = 1 
                WHERE id = ?
            ''', (exit_price, pnl, datetime.now(), id))
            conn.commit()

    def get_stats(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT pnl FROM trades WHERE is_closed = 1')
            pnls = [row[0] for row in cursor.fetchall()]
            
            total_pnl = sum(pnls) if pnls else 0
            wins = len([p for p in pnls if p > 0])
            losses = len([p for p in pnls if p <= 0])
            
            return total_pnl, wins, losses
