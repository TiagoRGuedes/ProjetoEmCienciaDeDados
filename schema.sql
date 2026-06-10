CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    telefone TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS servicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    preco REAL NOT NULL,
    duracao_min INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS profissionais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    especialidade TEXT NOT NULL,
    foto TEXT NOT NULL,
    ativo INTEGER NOT NULL DEFAULT 1,
    senha TEXT
);

CREATE TABLE IF NOT EXISTS profissionais_servicos (
    profissional_id INTEGER NOT NULL,
    servico_id INTEGER NOT NULL,
    PRIMARY KEY (profissional_id, servico_id),
    FOREIGN KEY (profissional_id) REFERENCES profissionais(id),
    FOREIGN KEY (servico_id) REFERENCES servicos(id)
);

CREATE TABLE IF NOT EXISTS agendamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    servico_id INTEGER NOT NULL,
    profissional_id INTEGER NOT NULL DEFAULT 1,
    data TEXT NOT NULL,
    horario TEXT NOT NULL,
    status TEXT NOT NULL,
    arquivado INTEGER NOT NULL DEFAULT 0,
    pago INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (servico_id) REFERENCES servicos(id),
    FOREIGN KEY (profissional_id) REFERENCES profissionais(id)
);

CREATE TABLE IF NOT EXISTS bloqueios_agenda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profissional_id INTEGER NOT NULL,
    data TEXT NOT NULL,
    horario TEXT,
    motivo TEXT NOT NULL,
    FOREIGN KEY (profissional_id) REFERENCES profissionais(id)
);

CREATE TABLE IF NOT EXISTS configuracoes (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fotos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    local TEXT NOT NULL,
    arquivo TEXT NOT NULL,
    titulo TEXT NOT NULL DEFAULT '',
    ordem INTEGER NOT NULL DEFAULT 0
);
