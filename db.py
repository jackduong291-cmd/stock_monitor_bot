import os
import sqlite3
from pathlib import Path
from models import Position

class Database:
    def __init__(self, path: str):
        self.db_url = os.environ.get('DATABASE_URL')
        self.is_pg = bool(self.db_url)
        if not self.is_pg:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.path = path
        else:
            import psycopg2
            self.psycopg2 = psycopg2
        self.init()

    def _execute(self, query: str, args=()):
        if self.is_pg:
            query = query.replace('?', '%s')
            conn = self.psycopg2.connect(self.db_url)
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(query, args)
                        if query.strip().upper().startswith('SELECT'):
                            return cur.fetchall()
                        return None
            finally:
                conn.close()
        else:
            conn = sqlite3.connect(self.path)
            try:
                with conn:
                    cur = conn.execute(query, args)
                    if query.strip().upper().startswith('SELECT'):
                        return cur.fetchall()
                    return cur.lastrowid
            finally:
                conn.close()

    def init(self):
        if self.is_pg:
            self._execute('''CREATE TABLE IF NOT EXISTS positions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                entry_price REAL NOT NULL,
                bought_at TEXT NOT NULL,
                note TEXT DEFAULT '',
                tracking INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )''')
        else:
            self._execute('''CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                entry_price REAL NOT NULL,
                bought_at TEXT NOT NULL,
                note TEXT DEFAULT '',
                tracking INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )''')

    def add_position(self, user_id, symbol, quantity, entry_price, bought_at, note=''):
        args = (user_id, symbol.upper(), quantity, entry_price, bought_at, note)
        if self.is_pg:
            query = '''INSERT INTO positions
                (user_id,symbol,quantity,entry_price,bought_at,note)
                VALUES (%s,%s,%s,%s,%s,%s) RETURNING id'''
            conn = self.psycopg2.connect(self.db_url)
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(query, args)
                        return cur.fetchone()[0]
            finally:
                conn.close()
        else:
            query = '''INSERT INTO positions
                (user_id,symbol,quantity,entry_price,bought_at,note)
                VALUES (?,?,?,?,?,?)'''
            return self._execute(query, args)

    def get(self, position_id):
        rows = self._execute('SELECT * FROM positions WHERE id=?', (position_id,))
        return Position(*rows[0][:8]) if rows else None

    def tracked(self, user_id=None):
        sql = 'SELECT * FROM positions WHERE tracking=1'
        args = []
        if user_id is not None:
            sql += ' AND user_id=?'
            args.append(user_id)
        rows = self._execute(sql, tuple(args))
        return [Position(*r[:8]) for r in rows]

    def set_tracking(self, position_id, value):
        self._execute('UPDATE positions SET tracking=? WHERE id=?', (int(value), position_id))

    def delete(self, position_id):
        self._execute('DELETE FROM positions WHERE id=?', (position_id,))
