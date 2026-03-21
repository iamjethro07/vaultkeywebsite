import os
import psycopg2
import psycopg2.extras
from flask import g

_db_url = None

def init_db(app):
    global _db_url
    _db_url = os.getenv('DATABASE_URL')
    if not _db_url:
        raise RuntimeError("DATABASE_URL environment variable not set")

    @app.teardown_appcontext
    def close(e):
        db = g.pop('db', None)
        if db:
            db.close()

def get_db():
    if 'db' not in g:
        conn = psycopg2.connect(_db_url, sslmode='require')
        conn.autocommit = False
        g.db = conn
    return g.db

def query(sql, args=(), one=False, commit=False):
    db = get_db()
    try:
        with db.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, args or None)
            if commit:
                db.commit()
                # If query has RETURNING, fetch the id
                try:
                    row = cur.fetchone()
                    return row['id'] if row else None
                except Exception:
                    return None
            return cur.fetchone() if one else cur.fetchall()
    except Exception as e:
        if commit:
            db.rollback()
        raise e
