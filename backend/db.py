import os
import psycopg2
import psycopg2.extras
from flask import g

_cfg = {}

def init_db(app):
    global _cfg
    database_url = os.getenv('DATABASE_URL')

    if database_url:
        _cfg = {'dsn': database_url, 'sslmode': 'require'}
    else:
        _cfg = {
            'host':     os.getenv('DB_HOST', '127.0.0.1'),
            'port':     int(os.getenv('DB_PORT', 5432)),
            'user':     os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'dbname':   os.getenv('DB_NAME', 'vaultkey'),
        }

    @app.teardown_appcontext
    def close(e):
        db = g.pop('db', None)
        if db: db.close()

def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(**_cfg)
    else:
        try:
            g.db.cursor().execute('SELECT 1')
        except Exception:
            g.db = psycopg2.connect(**_cfg)
    return g.db

def query(sql, args=(), one=False, commit=False):
    db = get_db()
    try:
        with db.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, args)
            if commit:
                db.commit()
                return cur.fetchone()
            return cur.fetchone() if one else cur.fetchall()
    except Exception as e:
        if commit: db.rollback()
        raise e