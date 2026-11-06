"""
Database module for Hostel Management System
Handles SQLite connection, schema execution, and common helpers.
"""

import sqlite3
import os
from flask import g

DATABASE = os.path.join(os.path.dirname(__file__), 'hostel.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')


def get_db():
    """Get or create database connection for the current request context."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db


def close_connection(exception):
    """Closes database connection at request end."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    """Execute a query and fetch results."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def modify_db(query, args=()):
    """Execute INSERT/UPDATE/DELETE query and commit."""
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id


def init_db():
    """Initialize database from schema.sql."""
    conn = sqlite3.connect(DATABASE)
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print("Database initialized successfully.")


if __name__ == '__main__':
    init_db()
