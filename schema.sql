-- Cria a tabela de clientes somente se ela ainda não existir.
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    telefone TEXT NOT NULL,
    email TEXT
);

-- Cria a tabela de serviços somente se ela ainda não existir.
CREATE TABLE IF NOT EXISTS servicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    preco REAL NOT NULL,
    duracao_min INTEGER NOT NULL
);

-- Cria a tabela de agendamentos somente se ela ainda não existir.
CREATE TABLE IF NOT EXISTS agendamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    servico_id INTEGER NOT NULL,
    data TEXT NOT NULL,
    horario TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (servico_id) REFERENCES servicos(id)
);
-- Cria a tabela de clientes somente se ela ainda não existir.
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    telefone TEXT NOT NULL,
    email TEXT
);

-- Cria a tabela de serviços somente se ela ainda não existir.
CREATE TABLE IF NOT EXISTS servicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    preco REAL NOT NULL,
    duracao_min INTEGER NOT NULL
);

-- Cria a tabela de agendamentos somente se ela ainda não existir.
CREATE TABLE IF NOT EXISTS agendamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    servico_id INTEGER NOT NULL,
    data TEXT NOT NULL,
    horario TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (servico_id) REFERENCES servicos(id)
);
