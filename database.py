import sqlite3
import os
from flask import g

DATABASE = 'esmalteria.db'

SERVICOS_INICIAIS = [
    ('Pedicure', 35.0, 60),
    ('Manicure', 25.0, 45),
    ('Unhas de gel', 80.0, 90),
    ('Alongamentos', 120.0, 120),
]


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row  # permite acessar colunas pelo nome: row['campo']
    return g.db


def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row

    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        db.executescript(f.read())

    count = db.execute('SELECT COUNT(*) FROM servicos').fetchone()[0]
    if count == 0:
        db.executemany(
            'INSERT INTO servicos (nome, preco, duracao_min) VALUES (?, ?, ?)',
            SERVICOS_INICIAIS
        )
        db.commit()

    db.close()
