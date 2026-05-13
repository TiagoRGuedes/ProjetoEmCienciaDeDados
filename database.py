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

PROFISSIONAIS_INICIAIS = [
    ('Pamela Francisco', 'Manicure e nail designer', 'pamela_francisco.png', 1),
    ('Equipe Refúgio 1', 'Esmaltação e pedicure', 'trabalho2.png', 1),
    ('Equipe Refúgio 2', 'Alongamento e banho em gel', 'trabalho3.png', 1),
]

PROFISSIONAIS_SERVICOS_INICIAIS = {
    'Pamela Francisco': ['Pedicure', 'Manicure', 'Unhas de gel', 'Alongamentos'],
    'Equipe Refúgio 1': ['Pedicure', 'Manicure'],
    'Equipe Refúgio 2': ['Unhas de gel', 'Alongamentos'],
}


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row  # permite acesso às colunas por nome
    return g.db


def _colunas_da_tabela(db, tabela):
    linhas = db.execute(f'PRAGMA table_info({tabela})').fetchall()
    return {linha[1] for linha in linhas}


def popular_profissionais_servicos(db):
    total_vinculos = db.execute('SELECT COUNT(*) FROM profissionais_servicos').fetchone()[0]
    if total_vinculos > 0:
        return
    for nome_profissional, nomes_servicos in PROFISSIONAIS_SERVICOS_INICIAIS.items():
        profissional = db.execute('SELECT id FROM profissionais WHERE nome = ?', (nome_profissional,)).fetchone()
        if profissional is None:
            continue
        for nome_servico in nomes_servicos:
            servico = db.execute('SELECT id FROM servicos WHERE nome = ?', (nome_servico,)).fetchone()
            if servico is None:
                continue
            db.execute(
                'INSERT OR IGNORE INTO profissionais_servicos (profissional_id, servico_id) VALUES (?, ?)',
                (profissional['id'], servico['id'])
            )
    db.commit()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row

    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        db.executescript(f.read())

    colunas_agendamentos = _colunas_da_tabela(db, 'agendamentos')
    # Migração: adiciona coluna ausente em bancos criados antes de múltiplas profissionais
    if 'profissional_id' not in colunas_agendamentos:
        db.execute('ALTER TABLE agendamentos ADD COLUMN profissional_id INTEGER DEFAULT 1')
        db.commit()

    total_servicos = db.execute('SELECT COUNT(*) FROM servicos').fetchone()[0]
    if total_servicos == 0:
        db.executemany('INSERT INTO servicos (nome, preco, duracao_min) VALUES (?, ?, ?)', SERVICOS_INICIAIS)
        db.commit()

    total_profissionais = db.execute('SELECT COUNT(*) FROM profissionais').fetchone()[0]
    if total_profissionais == 0:
        db.executemany('INSERT INTO profissionais (nome, especialidade, foto, ativo) VALUES (?, ?, ?, ?)', PROFISSIONAIS_INICIAIS)
        db.commit()

    popular_profissionais_servicos(db)

    db.close()
