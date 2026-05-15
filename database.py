import sqlite3
# Importa a biblioteca SQLite para criar e manipular o banco de dados.

import os
# Importa a biblioteca os para trabalhar com caminhos de arquivos.

from flask import g
# Importa o objeto g do Flask para guardar a conexão do banco durante a requisição.

DATABASE = 'esmalteria.db'
# Define o nome do arquivo do banco SQLite local.

SERVICOS_INICIAIS = [
    # Cria uma lista de serviços iniciais para popular o banco.
    ('Pedicure', 35.0, 60),
    # Define serviço, preço e duração.
    ('Manicure', 25.0, 45),
    # Define serviço, preço e duração.
    ('Unhas de gel', 80.0, 90),
    # Define serviço, preço e duração.
    ('Alongamentos', 120.0, 120),
    # Define serviço, preço e duração.
]
# Fecha a lista de serviços iniciais.

PROFISSIONAIS_INICIAIS = [
    # Cria uma lista de profissionais iniciais para o agendamento.
    ('Pamela Francisco', 'Manicure e nail designer', 'pamela_francisco.png', 1),
    # Define a profissional principal com foto real.
    ('Equipe Refúgio 1', 'Esmaltação e pedicure', 'trabalho2.png', 1),
    # Define uma profissional/equipe para demonstrar agenda separada.
    ('Equipe Refúgio 2', 'Alongamento e banho em gel', 'trabalho3.png', 1),
    # Define outra profissional/equipe para demonstrar agenda separada.
]
# Fecha a lista de profissionais iniciais.


PROFISSIONAIS_SERVICOS_INICIAIS = {
    # Cria um dicionário que indica quais serviços cada profissional atende.
    'Pamela Francisco': ['Pedicure', 'Manicure', 'Unhas de gel', 'Alongamentos'],
    # Define que Pamela aparece para todos os serviços principais.
    'Equipe Refúgio 1': ['Pedicure', 'Manicure'],
    # Define que a Equipe Refúgio 1 aparece apenas para serviços básicos.
    'Equipe Refúgio 2': ['Unhas de gel', 'Alongamentos'],
    # Define que a Equipe Refúgio 2 aparece apenas para gel e alongamentos.
}
# Fecha o dicionário de vínculos entre profissionais e serviços.


def get_db():
    # Cria uma função para abrir ou reutilizar a conexão com o banco.
    if 'db' not in g:
        # Verifica se ainda não existe conexão aberta nesta requisição.
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        # Abre a conexão com o banco SQLite.
        g.db.row_factory = sqlite3.Row
        # Permite acessar as colunas pelo nome, como row['nome'].
    return g.db
    # Retorna a conexão aberta.


def _colunas_da_tabela(db, tabela):
    # Cria uma função auxiliar para listar as colunas existentes em uma tabela.
    linhas = db.execute(f'PRAGMA table_info({tabela})').fetchall()
    # Executa o comando PRAGMA para obter informações da tabela.
    return {linha[1] for linha in linhas}
    # Retorna um conjunto com os nomes das colunas.



def popular_profissionais_servicos(db):
    # Cria uma função para preencher os vínculos entre profissionais e serviços.
    total_vinculos = db.execute('SELECT COUNT(*) FROM profissionais_servicos').fetchone()[0]
    # Conta quantos vínculos já existem na tabela profissionais_servicos.
    if total_vinculos > 0:
        # Verifica se os vínculos já foram cadastrados antes.
        return
        # Sai da função para não duplicar dados.
    for nome_profissional, nomes_servicos in PROFISSIONAIS_SERVICOS_INICIAIS.items():
        # Percorre cada profissional e sua lista de serviços permitidos.
        profissional = db.execute('SELECT id FROM profissionais WHERE nome = ?', (nome_profissional,)).fetchone()
        # Busca o id da profissional pelo nome.
        if profissional is None:
            # Verifica se a profissional não foi encontrada.
            continue
            # Pula para a próxima profissional.
        for nome_servico in nomes_servicos:
            # Percorre cada serviço que a profissional atende.
            servico = db.execute('SELECT id FROM servicos WHERE nome = ?', (nome_servico,)).fetchone()
            # Busca o id do serviço pelo nome.
            if servico is None:
                # Verifica se o serviço não foi encontrado.
                continue
                # Pula para o próximo serviço.
            db.execute(
                # Insere o vínculo entre profissional e serviço.
                'INSERT OR IGNORE INTO profissionais_servicos (profissional_id, servico_id) VALUES (?, ?)',
                # Usa OR IGNORE para evitar repetição caso o vínculo já exista.
                (profissional['id'], servico['id'])
                # Envia os ids encontrados para o SQLite.
            )
            # Finaliza a inserção do vínculo atual.
    db.commit()
    # Salva os vínculos no banco.

def init_db():
    # Cria a função que inicializa e atualiza o banco de dados.
    db = sqlite3.connect(DATABASE)
    # Abre uma conexão direta com o arquivo do banco.
    db.row_factory = sqlite3.Row
    # Permite acessar colunas pelo nome.

    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    # Monta o caminho completo até o arquivo schema.sql.
    with open(schema_path, 'r', encoding='utf-8') as f:
        # Abre o arquivo schema.sql com suporte a acentos.
        db.executescript(f.read())
        # Executa todos os comandos SQL do arquivo.

    colunas_agendamentos = _colunas_da_tabela(db, 'agendamentos')
    # Busca as colunas atuais da tabela agendamentos.
    if 'profissional_id' not in colunas_agendamentos:
        # Verifica se a coluna profissional_id ainda não existe em banco antigo.
        db.execute('ALTER TABLE agendamentos ADD COLUMN profissional_id INTEGER DEFAULT 1')
        # Adiciona a coluna para permitir agenda separada por profissional.
        db.commit()
        # Salva a alteração estrutural do banco.
    if 'arquivado' not in colunas_agendamentos:
        # Verifica se a coluna arquivado ainda não existe em banco antigo.
        db.execute('ALTER TABLE agendamentos ADD COLUMN arquivado INTEGER NOT NULL DEFAULT 0')
        # Adiciona a coluna para suportar a área de Histórico (limpeza do dashboard).
        db.commit()
        # Salva a alteração estrutural do banco.

    colunas_profissionais = _colunas_da_tabela(db, 'profissionais')
    # Busca as colunas atuais da tabela profissionais.
    if 'senha' not in colunas_profissionais:
        # Verifica se a coluna senha ainda não existe em banco antigo.
        db.execute('ALTER TABLE profissionais ADD COLUMN senha TEXT')
        # Adiciona a coluna para suportar o login da área restrita das profissionais.
        db.commit()
        # Salva a alteração estrutural do banco.

    configuracoes_iniciais = [
        # Define os valores padrão das preferências visuais.
        ('fonte', 'Arial, Helvetica, sans-serif'),
        # Família tipográfica usada em todo o site.
        ('cor_texto', '#3f2d25'),
        # Cor principal do texto.
        ('cor_fundo', '#efe0d1'),
        # Cor de fundo geral do site.
        ('cor_destaque', '#6f4f3f'),
        # Cor dos botões e elementos de destaque.
    ]
    # Lista padrão a ser inserida se a tabela estiver vazia.
    for chave, valor in configuracoes_iniciais:
        # Percorre cada par chave/valor padrão.
        db.execute('INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES (?, ?)', (chave, valor))
        # Insere somente se a chave ainda não existir.
    db.commit()
    # Salva as configurações padrão.

    total_servicos = db.execute('SELECT COUNT(*) FROM servicos').fetchone()[0]
    # Conta quantos serviços existem no banco.
    if total_servicos == 0:
        # Verifica se ainda não há serviços cadastrados.
        db.executemany('INSERT INTO servicos (nome, preco, duracao_min) VALUES (?, ?, ?)', SERVICOS_INICIAIS)
        # Insere todos os serviços iniciais.
        db.commit()
        # Salva os serviços no banco.

    total_profissionais = db.execute('SELECT COUNT(*) FROM profissionais').fetchone()[0]
    # Conta quantas profissionais existem no banco.
    if total_profissionais == 0:
        # Verifica se ainda não há profissionais cadastradas.
        db.executemany('INSERT INTO profissionais (nome, especialidade, foto, ativo) VALUES (?, ?, ?, ?)', PROFISSIONAIS_INICIAIS)
        # Insere todas as profissionais iniciais.
        db.commit()
        # Salva as profissionais no banco.

    popular_profissionais_servicos(db)
    # Garante que cada profissional apareça somente nos serviços que ela atende.

    db.close()
    # Fecha a conexão direta usada na inicialização.
