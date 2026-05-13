CREATE TABLE IF NOT EXISTS clientes (
    -- Cria a tabela de clientes se ela ainda não existir.
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Cria o identificador automático do cliente.
    nome TEXT NOT NULL,
    -- Guarda o nome do cliente e obriga preenchimento.
    telefone TEXT NOT NULL
    -- Guarda o telefone do cliente e obriga preenchimento.
);
-- Finaliza a tabela clientes.

CREATE TABLE IF NOT EXISTS servicos (
    -- Cria a tabela de serviços se ela ainda não existir.
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Cria o identificador automático do serviço.
    nome TEXT NOT NULL,
    -- Guarda o nome do serviço.
    preco REAL NOT NULL,
    -- Guarda o preço do serviço.
    duracao_min INTEGER NOT NULL
    -- Guarda a duração do serviço em minutos.
);
-- Finaliza a tabela servicos.

CREATE TABLE IF NOT EXISTS profissionais (
    -- Cria a tabela de profissionais disponíveis para atendimento.
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Cria o identificador automático da profissional.
    nome TEXT NOT NULL,
    -- Guarda o nome da profissional.
    especialidade TEXT NOT NULL,
    -- Guarda a especialidade principal da profissional.
    foto TEXT NOT NULL,
    -- Guarda o nome do arquivo de imagem usado no card.
    ativo INTEGER NOT NULL DEFAULT 1
    -- Controla se a profissional aparece ou não no agendamento.
);
-- Finaliza a tabela profissionais.



CREATE TABLE IF NOT EXISTS profissionais_servicos (
    -- Cria a tabela que liga cada profissional aos serviços que ela atende.
    profissional_id INTEGER NOT NULL,
    -- Guarda o id da profissional vinculada ao serviço.
    servico_id INTEGER NOT NULL,
    -- Guarda o id do serviço que a profissional consegue realizar.
    PRIMARY KEY (profissional_id, servico_id),
    -- Impede repetir o mesmo vínculo entre profissional e serviço.
    FOREIGN KEY (profissional_id) REFERENCES profissionais(id),
    -- Liga o vínculo à tabela de profissionais.
    FOREIGN KEY (servico_id) REFERENCES servicos(id)
    -- Liga o vínculo à tabela de serviços.
);
-- Finaliza a tabela profissionais_servicos.

CREATE TABLE IF NOT EXISTS agendamentos (
    -- Cria a tabela de agendamentos se ela ainda não existir.
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Cria o identificador automático do agendamento.
    cliente_id INTEGER NOT NULL,
    -- Guarda qual cliente fez o agendamento.
    servico_id INTEGER NOT NULL,
    -- Guarda qual serviço foi escolhido.
    profissional_id INTEGER NOT NULL DEFAULT 1,
    -- Guarda qual profissional foi escolhida e permite agenda separada.
    data TEXT NOT NULL,
    -- Guarda a data do atendimento.
    horario TEXT NOT NULL,
    -- Guarda o horário do atendimento.
    status TEXT NOT NULL,
    -- Guarda o status do agendamento.
    arquivado INTEGER NOT NULL DEFAULT 0,
    -- Marca como 1 quando o atendimento foi movido para o histórico (limpa o dashboard).
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    -- Liga o agendamento ao cliente.
    FOREIGN KEY (servico_id) REFERENCES servicos(id),
    -- Liga o agendamento ao serviço.
    FOREIGN KEY (profissional_id) REFERENCES profissionais(id)
    -- Liga o agendamento à profissional.
);
-- Finaliza a tabela agendamentos.

CREATE TABLE IF NOT EXISTS bloqueios_agenda (
    -- Cria a tabela de bloqueios administrativos da agenda.
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Cria o identificador automático do bloqueio.
    profissional_id INTEGER NOT NULL,
    -- Guarda qual profissional terá o horário ou dia bloqueado.
    data TEXT NOT NULL,
    -- Guarda a data bloqueada.
    horario TEXT,
    -- Guarda o horário bloqueado; vazio significa dia inteiro.
    motivo TEXT NOT NULL,
    -- Guarda o motivo, como feriado, folga ou compromisso interno.
    FOREIGN KEY (profissional_id) REFERENCES profissionais(id)
    -- Liga o bloqueio à profissional.
);
-- Finaliza a tabela bloqueios_agenda.
