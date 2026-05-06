import sqlite3  # Importa o módulo sqlite3, usado para trabalhar com banco de dados SQLite.
import os  # Importa o módulo os, usado para montar caminhos de arquivos no sistema.
from flask import g  # Importa o objeto g, usado pelo Flask para guardar dados durante uma requisição.

DATABASE = 'esmalteria.db'  # Define o nome do arquivo do banco de dados SQLite.

SERVICOS_INICIAIS = [  # Cria uma lista com serviços iniciais para popular o banco se ele estiver vazio.
    ('Pedicure', 35.0, 60),  # Define o serviço Pedicure com preço e duração.
    ('Manicure', 25.0, 45),  # Define o serviço Manicure com preço e duração.
    ('Unhas de gel', 80.0, 90),  # Define o serviço Unhas de gel com preço e duração.
    ('Alongamentos', 120.0, 120),  # Define o serviço Alongamentos com preço e duração.
]  # Fecha a lista de serviços iniciais.


def get_db():  # Cria uma função para abrir ou reutilizar a conexão com o banco.
    if 'db' not in g:  # Verifica se ainda não existe conexão salva para esta requisição.
        g.db = sqlite3.connect(  # Cria a conexão com o banco e guarda dentro do objeto g.
            DATABASE,  # Informa o nome do arquivo do banco que será aberto.
            detect_types=sqlite3.PARSE_DECLTYPES  # Permite que o sqlite3 interprete alguns tipos de dados automaticamente.
        )  # Fecha a criação da conexão.
        g.db.row_factory = sqlite3.Row  # Permite acessar colunas pelo nome, como registro['nome'].
    return g.db  # Retorna a conexão do banco para quem chamou a função.


def init_db():  # Cria uma função para iniciar o banco e criar tabelas.
    db = sqlite3.connect(DATABASE)  # Abre uma conexão direta com o banco de dados.
    db.row_factory = sqlite3.Row  # Permite acessar resultados pelo nome das colunas.

    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')  # Monta o caminho do arquivo schema.sql na mesma pasta deste arquivo.
    with open(schema_path, 'r', encoding='utf-8') as f:  # Abre o arquivo schema.sql para leitura com acentos funcionando.
        db.executescript(f.read())  # Executa todos os comandos SQL do arquivo para criar as tabelas.

    count = db.execute('SELECT COUNT(*) FROM servicos').fetchone()[0]  # Conta quantos serviços existem na tabela servicos.
    if count == 0:  # Verifica se a tabela está vazia.
        db.executemany(  # Executa vários INSERTs de uma vez para cadastrar os serviços iniciais.
            'INSERT INTO servicos (nome, preco, duracao_min) VALUES (?, ?, ?)',  # SQL para inserir nome, preço e duração.
            SERVICOS_INICIAIS  # Lista de serviços que será inserida no banco.
        )  # Fecha o comando executemany.
        db.commit()  # Salva os serviços iniciais no banco.

    db.close()  # Fecha a conexão com o banco.
