from flask import Flask, Blueprint, render_template, request, redirect, url_for, jsonify, session, flash
# Importa do Flask as ferramentas usadas para criar o site, rotas, páginas HTML, formulários, JSON, sessão e mensagens.

from database import init_db, get_db
# Importa do arquivo database.py as funções responsáveis por criar e acessar o banco SQLite.

from datetime import date, datetime, timedelta
# Importa date para validar dias de funcionamento, datetime para combinar dia/horário e timedelta para janelas no dashboard.

import calendar
# Importa calendar para descobrir quantos dias existem em cada mês.

app = Flask(__name__)
# Cria a aplicação Flask, que funciona como o servidor principal do projeto.

app.config['SECRET_KEY'] = 'esmalteria-secret-key'
# Define uma chave secreta para proteger a sessão de login do painel administrativo.

publico = Blueprint('publico', __name__)
# Cria o grupo de rotas públicas, usadas pelas clientes no site.

admin = Blueprint('admin', __name__, url_prefix='/admin')
# Cria o grupo de rotas administrativas, todas começando com /admin.

EMPRESA = {
    # Cria um dicionário com as informações fixas da empresa.
    'nome': 'Refúgio da Preta',
    # Define o nome da empresa que aparece no site.
    'dona': 'Pamela Francisco',
    # Define o nome da dona/profissional principal.
    'telefone': '(11) 99220-4706',
    # Define o telefone de contato da empresa.
    'endereco': 'Rua Carapicuíba, 143 - BNH Grajaú',
    # Define o endereço físico da empresa.
    'horarios': 'Terça a sábado, das 10h às 19h',
    # Define o horário de funcionamento exibido para as clientes.
    'instagram_nome': '@refugiodapreta',
    # Define o nome do Instagram da empresa.
    'instagram_url': 'https://www.instagram.com/refugiodapreta/',
    # Define o link do Instagram da empresa.
    'foto_dona': 'pamela_francisco.png',
    # Define o arquivo da foto da profissional principal.
    'slogan': 'Beleza, cuidado e acolhimento.',
    # Define uma frase curta de identidade da empresa.
}
# Fecha o dicionário de informações da empresa.

HORARIOS = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00']
# Cria a lista de horários padrão que podem aparecer no agendamento.

DIAS_FUNCIONAMENTO = {1, 2, 3, 4, 5}
# Define os dias de funcionamento pelo padrão do Python: terça=1, quarta=2, quinta=3, sexta=4 e sábado=5.

ADMIN_USUARIO = 'admin'
# Define o usuário padrão do painel administrativo.

ADMIN_SENHA = 'esmalteria123'
# Define a senha padrão do painel administrativo.


def esta_logado():
    # Cria uma função simples para verificar se o administrador está logado.
    return session.get('logado') is True
    # Retorna True quando a sessão possui a chave logado marcada como verdadeira.


def buscar_servicos():
    # Cria uma função para buscar todos os serviços cadastrados.
    db = get_db()
    # Abre uma conexão com o banco de dados.
    return db.execute('SELECT * FROM servicos ORDER BY id').fetchall()
    # Retorna todos os serviços ordenados pelo id.


def buscar_profissionais(apenas_ativas=True):
    # Cria uma função para buscar profissionais cadastradas.
    db = get_db()
    # Abre uma conexão com o banco de dados.
    if apenas_ativas:
        # Verifica se a busca deve retornar somente profissionais ativas.
        return db.execute('SELECT * FROM profissionais WHERE ativo = 1 ORDER BY id').fetchall()
        # Retorna apenas profissionais ativas para aparecerem no agendamento.
    return db.execute('SELECT * FROM profissionais ORDER BY id').fetchall()
    # Retorna todas as profissionais para uso administrativo.


def buscar_vinculos_profissionais_servicos():
    # Cria uma função para buscar quais serviços cada profissional atende.
    db = get_db()
    # Abre uma conexão com o banco de dados.
    linhas = db.execute('SELECT profissional_id, servico_id FROM profissionais_servicos').fetchall()
    # Busca todos os vínculos cadastrados entre profissionais e serviços.
    mapa = {}
    # Cria um dicionário vazio para organizar os vínculos.
    for linha in linhas:
        # Percorre cada vínculo encontrado no banco.
        profissional_id = str(linha['profissional_id'])
        # Converte o id da profissional para texto, facilitando o uso no JavaScript.
        servico_id = str(linha['servico_id'])
        # Converte o id do serviço para texto, facilitando comparação com o select.
        if profissional_id not in mapa:
            # Verifica se a profissional ainda não existe no dicionário.
            mapa[profissional_id] = []
            # Cria uma lista vazia para guardar serviços dessa profissional.
        mapa[profissional_id].append(servico_id)
        # Adiciona o serviço à lista da profissional.
    return mapa
    # Retorna o mapa final para o template usar na filtragem.


def profissional_atende_servico(profissional_id, servico_id):
    # Cria uma função para validar se a profissional atende o serviço selecionado.
    if profissional_id == '' or servico_id == '':
        # Verifica se algum dos campos está vazio.
        return False
        # Retorna falso porque não é possível validar sem os dois dados.
    db = get_db()
    # Abre uma conexão com o banco de dados.
    vinculo = db.execute(
        # Executa a consulta que procura o vínculo entre profissional e serviço.
        'SELECT 1 FROM profissionais_servicos WHERE profissional_id = ? AND servico_id = ?',
        # Usa parâmetros para evitar erro e manter segurança.
        (profissional_id, servico_id)
        # Envia o id da profissional e do serviço para consulta.
    ).fetchone()
    # Busca apenas uma linha, pois basta saber se o vínculo existe.
    return vinculo is not None
    # Retorna verdadeiro se a profissional atende o serviço.


def dia_funciona(data_texto):
    # Cria uma função para verificar se a empresa funciona na data escolhida.
    try:
        # Tenta converter o texto da data para o formato de data do Python.
        data_objeto = date.fromisoformat(data_texto)
        # Converte uma data no formato AAAA-MM-DD para objeto date.
    except ValueError:
        # Entra aqui se a data estiver vazia ou inválida.
        return False
        # Retorna False porque a data não pode ser usada.
    return data_objeto.weekday() in DIAS_FUNCIONAMENTO
    # Retorna True somente para terça a sábado.


def buscar_bloqueios(data_texto, profissional_id):
    # Cria uma função para buscar folgas, feriados ou horários bloqueados pela administração.
    if data_texto == '' or profissional_id == '':
        # Verifica se falta data ou profissional.
        return []
        # Retorna lista vazia porque não há como consultar disponibilidade.
    db = get_db()
    # Abre uma conexão com o banco de dados.
    return db.execute(
        # Executa consulta de bloqueios do dia e da profissional.
        'SELECT * FROM bloqueios_agenda WHERE data = ? AND profissional_id = ? ORDER BY horario',
        # Busca bloqueios exatamente da data e profissional selecionadas.
        (data_texto, profissional_id)
        # Envia os valores com segurança para o SQLite.
    ).fetchall()
    # Retorna os bloqueios encontrados.


def buscar_horarios_indisponiveis(data_texto, profissional_id, ignorar_agendamento_id=None):
    # Cria uma função para calcular horários indisponíveis de uma profissional em uma data.
    if data_texto == '' or profissional_id == '':
        # Verifica se ainda não há data ou profissional.
        return set()
        # Retorna um conjunto vazio porque a agenda ainda não foi escolhida.
    indisponiveis = set()
    # Cria um conjunto vazio para guardar horários ocupados ou bloqueados.
    if not dia_funciona(data_texto):
        # Verifica se a data está fora dos dias de funcionamento.
        return set(HORARIOS)
        # Retorna todos os horários como indisponíveis.
    db = get_db()
    # Abre uma conexão com o banco.
    sql = 'SELECT horario FROM agendamentos WHERE data = ? AND profissional_id = ? AND status != ?'
    # Monta a consulta que busca horários já reservados e não cancelados.
    parametros = [data_texto, profissional_id, 'cancelado']
    # Cria a lista de parâmetros da consulta.
    if ignorar_agendamento_id is not None:
        # Verifica se existe um agendamento que deve ser ignorado durante remarcação.
        sql += ' AND id != ?'
        # Adiciona uma condição para não comparar o agendamento com ele mesmo.
        parametros.append(ignorar_agendamento_id)
        # Adiciona o id ignorado nos parâmetros.
    agendados = db.execute(sql, parametros).fetchall()
    # Executa a consulta de agendamentos que bloqueiam horários.
    for linha in agendados:
        # Percorre cada horário reservado.
        indisponiveis.add(linha['horario'])
        # Adiciona o horário reservado ao conjunto de indisponíveis.
    bloqueios = buscar_bloqueios(data_texto, profissional_id)
    # Busca os bloqueios manuais cadastrados pelo admin.
    for bloqueio in bloqueios:
        # Percorre cada bloqueio encontrado.
        if bloqueio['horario'] in (None, ''):
            # Verifica se o bloqueio foi cadastrado para o dia inteiro.
            indisponiveis.update(HORARIOS)
            # Bloqueia todos os horários daquele dia.
        else:
            # Entra aqui quando o bloqueio é apenas de um horário.
            indisponiveis.add(bloqueio['horario'])
            # Bloqueia somente o horário informado.
    return indisponiveis
    # Retorna o conjunto final de horários indisponíveis.


def montar_lista_horarios(data_texto, profissional_id, ignorar_agendamento_id=None):
    # Cria uma lista detalhada com cada horário e se ele está disponível.
    indisponiveis = buscar_horarios_indisponiveis(data_texto, profissional_id, ignorar_agendamento_id)
    # Calcula os horários indisponíveis para a data e profissional.
    lista = []
    # Cria uma lista vazia para montar o retorno.
    for horario in HORARIOS:
        # Percorre todos os horários padrão.
        disponivel = horario not in indisponiveis
        # Verifica se o horário está livre.
        lista.append({'horario': horario, 'disponivel': disponivel})
        # Adiciona um dicionário com horário e disponibilidade.
    return lista
    # Retorna a lista completa de horários.


def contar_horarios_disponiveis(data_texto, profissional_id):
    # Cria uma função para contar horários livres em uma data.
    lista = montar_lista_horarios(data_texto, profissional_id)
    # Monta a lista de horários do dia.
    return sum(1 for item in lista if item['disponivel'])
    # Soma quantos horários estão disponíveis.


def conflito_agenda(data_texto, horario, profissional_id, ignorar_agendamento_id=None):
    # Cria uma função para verificar se um horário pode ser usado.
    indisponiveis = buscar_horarios_indisponiveis(data_texto, profissional_id, ignorar_agendamento_id)
    # Busca horários indisponíveis para aquela profissional.
    return horario in indisponiveis
    # Retorna True se o horário já estiver bloqueado ou reservado.


@publico.route('/')
# Cria a rota da página inicial.
def index():
    # Define a função executada quando a cliente acessa a página inicial.
    servicos = buscar_servicos()
    # Busca os serviços para mostrar na seção de serviços.
    galeria = [
        # Cria a lista de fotos usadas na galeria.
        {'arquivo': 'trabalho1.png', 'titulo': 'Esmaltação marrom nude elegante'},
        # Define a primeira foto da galeria.
        {'arquivo': 'trabalho2.png', 'titulo': 'Atendimento com cuidado e técnica'},
        # Define a segunda foto da galeria.
        {'arquivo': 'trabalho3.png', 'titulo': 'Nude com brilho delicado'},
        # Define a terceira foto da galeria.
    ]
    # Fecha a lista da galeria.
    return render_template('index.html', servicos=servicos, empresa=EMPRESA, galeria=galeria)
    # Abre o template index.html e envia serviços, empresa e galeria para o HTML.


@publico.route('/agendar', methods=['GET'])
# Cria a rota GET da página de agendamento, usada para abrir o formulário.
def agendar_get():
    # Define a função que mostra a tela de agendamento.
    servicos = buscar_servicos()
    # Busca os serviços disponíveis.
    profissionais = buscar_profissionais()
    # Busca as profissionais disponíveis.
    profissionais_servicos = buscar_vinculos_profissionais_servicos()
    # Busca quais profissionais atendem cada serviço para filtrar os cards na tela.
    dados = {'nome': '', 'telefone': '', 'servico_id': '', 'profissional_id': '', 'data': '', 'horario': ''}
    # Cria um dicionário vazio para preencher o formulário sem erro.
    return render_template('agendamento.html', servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, empresa=EMPRESA, horarios=HORARIOS, horarios_ocupados=[], dados=dados, erro=None)
    # Renderiza a página de agendamento com dados iniciais vazios.


@publico.route('/agendar', methods=['POST'])
# Cria a rota POST da página de agendamento, usada quando a cliente envia o formulário.
def agendar_post():
    # Define a função que valida e salva o agendamento.
    db = get_db()
    # Abre uma conexão com o banco.
    nome = request.form.get('nome', '').strip()
    # Recebe o nome digitado e remove espaços extras.
    telefone = request.form.get('telefone', '').strip()
    # Recebe o telefone digitado e remove espaços extras.
    servico_id = request.form.get('servico_id', '').strip()
    # Recebe o serviço escolhido.
    profissional_id = request.form.get('profissional_id', '').strip()
    # Recebe a profissional escolhida.
    data_texto = request.form.get('data', '').strip()
    # Recebe a data escolhida pelo calendário.
    horario = request.form.get('horario', '').strip()
    # Recebe o horário escolhido.
    dados = {'nome': nome, 'telefone': telefone, 'servico_id': servico_id, 'profissional_id': profissional_id, 'data': data_texto, 'horario': horario}
    # Guarda todos os dados para devolver ao formulário caso exista erro.

    def erro_form(msg):
        # Cria uma função interna para recarregar o formulário com mensagem de erro.
        servicos = buscar_servicos()
        # Busca os serviços novamente.
        profissionais = buscar_profissionais()
        # Busca as profissionais novamente.
        profissionais_servicos = buscar_vinculos_profissionais_servicos()
        # Busca os vínculos para manter a filtragem por serviço na tela.
        horarios_ocupados = buscar_horarios_indisponiveis(data_texto, profissional_id)
        # Busca os horários ocupados conforme a profissional e a data escolhidas.
        return render_template('agendamento.html', servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, empresa=EMPRESA, horarios=HORARIOS, horarios_ocupados=horarios_ocupados, dados=dados, erro=msg)
        # Retorna a página com mensagem de erro.

    if len(nome) < 2:
        # Verifica se o nome é muito curto.
        return erro_form('Informe um nome válido.')
        # Volta para o formulário com erro de nome.
    if len(telefone) < 8:
        # Verifica se o telefone tem tamanho mínimo.
        return erro_form('Informe um telefone válido.')
        # Volta para o formulário com erro de telefone.
    if servico_id == '':
        # Verifica se o serviço foi escolhido.
        return erro_form('Selecione um serviço.')
        # Volta para o formulário pedindo o serviço.
    if profissional_id == '':
        # Verifica se a profissional foi escolhida.
        return erro_form('Selecione uma profissional.')
        # Volta para o formulário pedindo a profissional.
    if not profissional_atende_servico(profissional_id, servico_id):
        # Verifica se a profissional selecionada realmente atende o serviço escolhido.
        return erro_form('Selecione uma profissional disponível para esse serviço.')
        # Volta para o formulário impedindo combinação inválida.
    if data_texto == '':
        # Verifica se a data foi escolhida.
        return erro_form('Selecione uma data no calendário.')
        # Volta para o formulário pedindo a data.
    if not dia_funciona(data_texto):
        # Verifica se a data é terça a sábado.
        return erro_form('Selecione uma data entre terça e sábado.')
        # Volta para o formulário se a data não for dia de funcionamento.
    if horario == '':
        # Verifica se o horário foi escolhido.
        return erro_form('Selecione um horário disponível.')
        # Volta para o formulário pedindo o horário.
    if conflito_agenda(data_texto, horario, profissional_id):
        # Verifica se o horário já está reservado ou bloqueado.
        return erro_form('Horário indisponível para a profissional selecionada.')
        # Volta para o formulário informando conflito.

    cliente = db.execute('SELECT id FROM clientes WHERE telefone = ?', (telefone,)).fetchone()
    # Procura se já existe cliente com o mesmo telefone.
    if cliente:
        # Verifica se o cliente já foi encontrado.
        cliente_id = cliente['id']
        # Reutiliza o cliente existente.
    else:
        # Entra aqui se o cliente ainda não existe.
        cursor = db.execute('INSERT INTO clientes (nome, telefone) VALUES (?, ?)', (nome, telefone))
        # Insere cliente sem email, conforme solicitado.
        cliente_id = cursor.lastrowid
        # Pega o id do cliente recém-criado.

    db.execute('INSERT INTO agendamentos (cliente_id, servico_id, profissional_id, data, horario, status) VALUES (?, ?, ?, ?, ?, ?)', (cliente_id, servico_id, profissional_id, data_texto, horario, 'pendente'))
    # Salva o agendamento com profissional, data e horário.
    db.commit()
    # Confirma a gravação no banco.
    return redirect(url_for('publico.confirmacao'))
    # Redireciona para a página de confirmação.


@publico.route('/confirmacao')
# Cria a rota da página de confirmação.
def confirmacao():
    # Define a função que abre a página de confirmação.
    return render_template('confirmacao.html', empresa=EMPRESA)
    # Renderiza a página informando que o agendamento foi enviado.


@publico.route('/horarios-disponiveis')
# Cria uma rota JSON que retorna os horários disponíveis de uma data.
def horarios_disponiveis():
    # Define a função usada pelo JavaScript do calendário.
    data_texto = request.args.get('data', '').strip()
    # Recebe a data pela URL.
    profissional_id = request.args.get('profissional_id', '').strip()
    # Recebe a profissional pela URL.
    horarios = montar_lista_horarios(data_texto, profissional_id)
    # Monta a lista detalhada de horários.
    return jsonify({'data': data_texto, 'horarios': horarios})
    # Retorna a disponibilidade em formato JSON.


@publico.route('/disponibilidade-mes')
# Cria uma rota JSON para o calendário saber quais dias possuem horários livres.
def disponibilidade_mes():
    # Define a função chamada pelo JavaScript ao trocar de mês.
    ano = int(request.args.get('ano', date.today().year))
    # Recebe o ano pela URL ou usa o ano atual.
    mes = int(request.args.get('mes', date.today().month))
    # Recebe o mês pela URL ou usa o mês atual.
    profissional_id = request.args.get('profissional_id', '').strip()
    # Recebe a profissional selecionada.
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    # Descobre o último dia do mês.
    resposta = {}
    # Cria um dicionário para guardar a disponibilidade de cada dia.
    for dia in range(1, ultimo_dia + 1):
        # Percorre todos os dias do mês.
        data_texto = f'{ano:04d}-{mes:02d}-{dia:02d}'
        # Monta a data no formato usado pelo banco.
        aberto = dia_funciona(data_texto)
        # Verifica se a empresa funciona nesse dia.
        livres = contar_horarios_disponiveis(data_texto, profissional_id) if profissional_id and aberto else 0
        # Conta horários livres se houver profissional selecionada e o dia estiver aberto.
        resposta[data_texto] = {'aberto': aberto, 'livres': livres, 'total': len(HORARIOS)}
        # Salva as informações do dia para o JavaScript.
    return jsonify(resposta)
    # Retorna o calendário do mês em JSON.


@admin.route('/login', methods=['GET', 'POST'])
# Cria a rota de login do painel administrativo.
def login():
    # Define a função de login.
    if request.method == 'POST':
        # Verifica se o formulário foi enviado.
        usuario = request.form.get('usuario', '')
        # Recebe o usuário digitado.
        senha = request.form.get('senha', '')
        # Recebe a senha digitada.
        if usuario == ADMIN_USUARIO and senha == ADMIN_SENHA:
            # Confere se usuário e senha estão corretos.
            session['logado'] = True
            # Marca a sessão como logada.
            return redirect(url_for('admin.dashboard'))
            # Redireciona para o dashboard.
        return render_template('admin/login.html', erro='Usuário ou senha inválidos.', empresa=EMPRESA)
        # Reabre o login com erro se os dados estiverem incorretos.
    return render_template('admin/login.html', empresa=EMPRESA)
    # Mostra o formulário de login.


@admin.route('/logout')
# Cria a rota para sair do painel.
def logout():
    # Define a função de logout.
    session.clear()
    # Limpa os dados de sessão.
    return redirect(url_for('admin.login'))
    # Volta para a tela de login.


@admin.route('/dashboard')
# Cria a rota do dashboard administrativo.
def dashboard():
    # Define a função que lista agendamentos.
    if not esta_logado():
        # Verifica se o admin não está logado.
        return redirect(url_for('admin.login'))
        # Redireciona para login.
    filtro_status = request.args.get('status', '').strip()
    # Recebe o filtro de status.
    filtro_data = request.args.get('data', '').strip()
    # Recebe o filtro de data.
    filtro_profissional = request.args.get('profissional_id', '').strip()
    # Recebe o filtro de profissional.
    sql = '''SELECT a.id, a.data, a.horario, a.status,
                    c.nome AS cliente_nome, c.telefone,
                    s.nome AS servico_nome, s.preco, s.duracao_min,
                    p.nome AS profissional_nome
             FROM agendamentos a
             JOIN clientes c ON c.id = a.cliente_id
             JOIN servicos s ON s.id = a.servico_id
             JOIN profissionais p ON p.id = a.profissional_id'''
    # Monta a consulta principal juntando agendamentos, clientes, serviços e profissionais.
    where = []
    # Cria uma lista vazia de filtros SQL.
    params = []
    # Cria a lista de parâmetros da consulta.
    if filtro_status in ('pendente', 'confirmado', 'cancelado'):
        # Verifica se o filtro de status é válido.
        where.append('a.status = ?')
        # Adiciona condição de status.
        params.append(filtro_status)
        # Adiciona o valor do status.
    if filtro_data:
        # Verifica se há filtro de data.
        where.append('a.data = ?')
        # Adiciona condição de data.
        params.append(filtro_data)
        # Adiciona a data nos parâmetros.
    if filtro_profissional:
        # Verifica se há filtro de profissional.
        where.append('a.profissional_id = ?')
        # Adiciona condição de profissional.
        params.append(filtro_profissional)
        # Adiciona profissional nos parâmetros.
    if where:
        # Verifica se existe algum filtro.
        sql += ' WHERE ' + ' AND '.join(where)
        # Junta os filtros na consulta SQL.
    sql += ' ORDER BY a.data, a.horario'
    # Ordena a agenda por data e horário.
    db = get_db()
    # Abre a conexão com o banco.
    agendamentos = db.execute(sql, params).fetchall()
    # Executa a consulta final.
    profissionais = buscar_profissionais(False)
    # Busca profissionais para o filtro.
    kpis = calcular_kpis_dashboard(db)
    # Calcula indicadores rápidos para o admin acompanhar a operação.
    return render_template('admin/dashboard.html', agendamentos=agendamentos, profissionais=profissionais, filtro_status=filtro_status, filtro_data=filtro_data, filtro_profissional=filtro_profissional, empresa=EMPRESA, kpis=kpis)
    # Renderiza o dashboard com KPIs e lista filtrada.


def calcular_kpis_dashboard(db):
    # Cria função auxiliar que monta um pequeno painel de números do dia/semana.
    hoje = date.today().isoformat()
    # Pega a data de hoje no formato AAAA-MM-DD para usar nas consultas.
    inicio_semana = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    # Calcula a segunda-feira da semana corrente para servir de janela.
    fim_semana = (date.today() + timedelta(days=6 - date.today().weekday())).isoformat()
    # Calcula o domingo da semana corrente como fim da janela.
    total_hoje = db.execute(
        # Conta quantos agendamentos não cancelados estão marcados para hoje.
        "SELECT COUNT(*) AS n FROM agendamentos WHERE data = ? AND status != 'cancelado'",
        (hoje,)
    ).fetchone()['n']
    # Salva o número de atendimentos do dia para o KPI.
    confirmados_hoje = db.execute(
        # Conta apenas os agendamentos de hoje já confirmados.
        "SELECT COUNT(*) AS n FROM agendamentos WHERE data = ? AND status = 'confirmado'",
        (hoje,)
    ).fetchone()['n']
    # Salva o número de confirmados.
    pendentes = db.execute(
        # Conta quantos agendamentos futuros ainda estão pendentes (precisam de confirmação).
        "SELECT COUNT(*) AS n FROM agendamentos WHERE status = 'pendente' AND data >= ?",
        (hoje,)
    ).fetchone()['n']
    # Salva pendentes para o KPI.
    receita_semana = db.execute(
        # Soma a receita estimada da semana, considerando apenas agendamentos não cancelados.
        """SELECT COALESCE(SUM(s.preco), 0) AS total
           FROM agendamentos a
           JOIN servicos s ON s.id = a.servico_id
           WHERE a.data BETWEEN ? AND ? AND a.status != 'cancelado'""",
        (inicio_semana, fim_semana)
    ).fetchone()['total']
    # Salva a soma da receita prevista na semana.
    profissionais_ativas = db.execute(
        # Conta quantas profissionais estão ativas e podem receber agendamento.
        "SELECT COUNT(*) AS n FROM profissionais WHERE ativo = 1"
    ).fetchone()['n']
    # Salva o número de profissionais ativas.
    return {
        # Retorna os KPIs em um dicionário simples consumido pelo template.
        'hoje': total_hoje,
        # Total de atendimentos previstos para hoje.
        'confirmados_hoje': confirmados_hoje,
        # Quantos atendimentos de hoje já estão confirmados.
        'pendentes': pendentes,
        # Quantos agendamentos futuros aguardam confirmação.
        'receita_semana': receita_semana,
        # Receita prevista para a semana corrente.
        'profissionais_ativas': profissionais_ativas,
        # Quantas profissionais estão ativas na agenda.
    }
    # Encerra o cálculo dos KPIs.


@admin.route('/agendamento/<int:id>/status', methods=['POST'])
# Cria a rota que altera apenas o status do agendamento.
def atualizar_status(id):
    # Define a função de alteração rápida de status.
    if not esta_logado():
        # Verifica se o admin está logado.
        return redirect(url_for('admin.login'))
        # Redireciona para login se não estiver logado.
    novo_status = request.form.get('novo_status')
    # Recebe o novo status enviado pelo botão.
    if novo_status not in ('pendente', 'confirmado', 'cancelado'):
        # Verifica se o status enviado é permitido.
        flash('Status inválido.', 'error')
        # Mostra mensagem de erro.
        return redirect(url_for('admin.dashboard'))
        # Volta para o dashboard.
    db = get_db()
    # Abre a conexão com o banco.
    db.execute('UPDATE agendamentos SET status = ? WHERE id = ?', (novo_status, id))
    # Atualiza o status no banco; se for cancelado, o horário deixa de bloquear a agenda.
    db.commit()
    # Salva a alteração.
    flash('Status do agendamento atualizado.', 'success')
    # Mostra mensagem de sucesso.
    return redirect(url_for('admin.dashboard'))
    # Volta para o dashboard.


@admin.route('/agendamento/<int:id>/editar', methods=['GET', 'POST'])
# Cria a rota para editar/remarcar um agendamento.
def agendamento_editar(id):
    # Define a função de edição de agendamento.
    if not esta_logado():
        # Verifica se o admin está logado.
        return redirect(url_for('admin.login'))
        # Redireciona para login.
    db = get_db()
    # Abre conexão com banco.
    agendamento = db.execute('SELECT * FROM agendamentos WHERE id = ?', (id,)).fetchone()
    # Busca o agendamento pelo id.
    if agendamento is None:
        # Verifica se o agendamento existe.
        flash('Agendamento não encontrado.', 'error')
        # Mostra erro.
        return redirect(url_for('admin.dashboard'))
        # Volta ao dashboard.
    servicos = buscar_servicos()
    # Busca serviços para o formulário.
    profissionais = buscar_profissionais(False)
    # Busca profissionais para o formulário.
    profissionais_servicos = buscar_vinculos_profissionais_servicos()
    # Busca vínculos para filtrar profissionais por serviço no formulário do admin.
    if request.method == 'POST':
        # Verifica se o formulário de edição foi enviado.
        servico_id = request.form.get('servico_id', '').strip()
        # Recebe serviço editado.
        profissional_id = request.form.get('profissional_id', '').strip()
        # Recebe profissional editada.
        data_texto = request.form.get('data', '').strip()
        # Recebe data editada.
        horario = request.form.get('horario', '').strip()
        # Recebe horário editado.
        status = request.form.get('status', '').strip()
        # Recebe status editado.
        if servico_id == '' or profissional_id == '' or data_texto == '' or horario == '' or status == '':
            # Verifica campos obrigatórios.
            flash('Preencha todos os campos do agendamento.', 'error')
            # Mostra erro.
            lista_horarios = montar_lista_horarios(data_texto, profissional_id, ignorar_agendamento_id=id)
            # Recalcula a disponibilidade do horário para mostrar no formulário.
            return render_template('admin/agendamento_form.html', agendamento=agendamento, servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, lista_horarios=lista_horarios, empresa=EMPRESA)
            # Reabre formulário.
        if not profissional_atende_servico(profissional_id, servico_id):
            # Verifica se o serviço e a profissional combinam.
            flash('A profissional escolhida não atende esse serviço.', 'error')
            # Mostra mensagem de erro.
            lista_horarios = montar_lista_horarios(data_texto, profissional_id, ignorar_agendamento_id=id)
            # Recalcula a disponibilidade para devolver ao formulário.
            return render_template('admin/agendamento_form.html', agendamento=agendamento, servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, lista_horarios=lista_horarios, empresa=EMPRESA)
            # Reabre formulário.
        if status != 'cancelado' and conflito_agenda(data_texto, horario, profissional_id, id):
            # Verifica conflito ao remarcar, ignorando o próprio agendamento.
            flash('Este horário está indisponível para a profissional escolhida.', 'error')
            # Mostra erro.
            lista_horarios = montar_lista_horarios(data_texto, profissional_id, ignorar_agendamento_id=id)
            # Recalcula a disponibilidade do horário para mostrar no formulário.
            return render_template('admin/agendamento_form.html', agendamento=agendamento, servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, lista_horarios=lista_horarios, empresa=EMPRESA)
            # Reabre formulário.
        db.execute('UPDATE agendamentos SET servico_id = ?, profissional_id = ?, data = ?, horario = ?, status = ? WHERE id = ?', (servico_id, profissional_id, data_texto, horario, status, id))
        # Atualiza o agendamento; a vaga antiga volta automaticamente porque a linha mudou.
        db.commit()
        # Salva a edição.
        flash('Agendamento atualizado com sucesso.', 'success')
        # Mostra sucesso.
        return redirect(url_for('admin.dashboard'))
        # Volta para o dashboard.
    lista_horarios = montar_lista_horarios(agendamento['data'], str(agendamento['profissional_id']), ignorar_agendamento_id=id)
    # Calcula horários disponíveis para a combinação data/profissional do agendamento atual, ignorando ele mesmo.
    return render_template('admin/agendamento_form.html', agendamento=agendamento, servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, lista_horarios=lista_horarios, empresa=EMPRESA)
    # Abre o formulário de edição com horários filtrados por disponibilidade.


@admin.route('/servicos')
# Cria a rota administrativa de serviços.
def servicos():
    # Define a função que lista serviços.
    if not esta_logado():
        # Verifica login.
        return redirect(url_for('admin.login'))
        # Redireciona para login.
    db = get_db()
    # Abre o banco para enriquecer a lista com as profissionais que atendem cada serviço.
    lista = db.execute(
        # Faz uma única consulta agrupando os nomes das profissionais vinculadas a cada serviço.
        """SELECT s.id, s.nome, s.preco, s.duracao_min,
                  COALESCE(GROUP_CONCAT(p.nome, ', '), '') AS profissionais_atendem
           FROM servicos s
           LEFT JOIN profissionais_servicos ps ON ps.servico_id = s.id
           LEFT JOIN profissionais p ON p.id = ps.profissional_id AND p.ativo = 1
           GROUP BY s.id
           ORDER BY s.id"""
        # Junta serviços com as profissionais ativas vinculadas, para exibir no painel.
    ).fetchall()
    # Carrega o resultado para o template.
    return render_template('admin/servicos.html', servicos=lista, empresa=EMPRESA)
    # Renderiza a lista de serviços com as profissionais.


def _parse_servico_form():
    # Cria função auxiliar para ler formulário de serviço.
    nome = request.form.get('nome', '').strip()
    # Lê nome do serviço.
    preco_raw = request.form.get('preco', '').strip().replace(',', '.')
    # Lê preço e troca vírgula por ponto.
    duracao_raw = request.form.get('duracao_min', '').strip()
    # Lê duração.
    erro = None
    # Cria variável de erro.
    preco = duracao = None
    # Cria variáveis de preço e duração.
    try:
        # Tenta converter valores.
        preco = float(preco_raw)
        # Converte preço para número decimal.
        duracao = int(duracao_raw)
        # Converte duração para inteiro.
    except ValueError:
        # Captura erro de conversão.
        erro = 'Preço e duração precisam ser numéricos.'
        # Define mensagem de erro.
    if not erro:
        # Continua validação se não houve erro.
        if not nome:
            # Verifica nome vazio.
            erro = 'Nome é obrigatório.'
            # Define erro.
        elif preco < 0:
            # Verifica preço negativo.
            erro = 'Preço não pode ser negativo.'
            # Define erro.
        elif duracao <= 0:
            # Verifica duração inválida.
            erro = 'Duração deve ser maior que zero.'
            # Define erro.
    return nome, preco, duracao, erro
    # Retorna os dados tratados.


@admin.route('/servicos/novo', methods=['GET', 'POST'])
# Cria rota para cadastrar serviço.
def servico_novo():
    # Define a função de cadastro.
    if not esta_logado():
        # Verifica login.
        return redirect(url_for('admin.login'))
        # Redireciona para login.
    db = get_db()
    # Abre o banco para buscar profissionais disponíveis e gravar vínculos depois.
    profissionais = buscar_profissionais(False)
    # Carrega todas as profissionais (ativas e inativas) para o admin ligar ao serviço.
    if request.method == 'POST':
        # Verifica envio do formulário.
        nome, preco, duracao, erro = _parse_servico_form()
        # Lê e valida dados.
        ids_profissionais = request.form.getlist('profissionais_ids')
        # Lê quais profissionais foram marcadas como aptas a realizar o serviço.
        if erro:
            # Verifica erro.
            return render_template('admin/servico_form.html', servico=None, form=request.form, erro=erro, profissionais=profissionais, profissionais_selecionadas=set(ids_profissionais), empresa=EMPRESA)
            # Reabre formulário com erro mantendo as profissionais marcadas.
        cursor = db.execute('INSERT INTO servicos (nome, preco, duracao_min) VALUES (?, ?, ?)', (nome, preco, duracao))
        # Insere serviço.
        novo_id = cursor.lastrowid
        # Pega o id recém-criado para gravar vínculos a seguir.
        for pid in ids_profissionais:
            # Percorre cada profissional marcada no formulário.
            db.execute(
                # Insere o vínculo entre a profissional e o novo serviço.
                'INSERT OR IGNORE INTO profissionais_servicos (profissional_id, servico_id) VALUES (?, ?)',
                # Usa OR IGNORE para evitar duplicidade caso o admin marque duas vezes.
                (pid, novo_id)
                # Envia os ids para o SQLite.
            )
            # Finaliza o insert do vínculo.
        db.commit()
        # Salva serviço e vínculos.
        flash(f'Serviço "{nome}" criado com sucesso.', 'success')
        # Mostra sucesso.
        return redirect(url_for('admin.servicos'))
        # Volta para serviços.
    return render_template('admin/servico_form.html', servico=None, form=None, profissionais=profissionais, profissionais_selecionadas=set(), empresa=EMPRESA)
    # Abre formulário vazio com a lista de profissionais para vincular.


@admin.route('/servicos/<int:id>/editar', methods=['GET', 'POST'])
# Cria rota para editar serviço.
def servico_editar(id):
    # Define função de edição.
    if not esta_logado():
        # Verifica login.
        return redirect(url_for('admin.login'))
        # Redireciona para login.
    db = get_db()
    # Abre banco.
    servico = db.execute('SELECT * FROM servicos WHERE id = ?', (id,)).fetchone()
    # Busca serviço pelo id.
    if servico is None:
        # Verifica se existe.
        flash('Serviço não encontrado.', 'error')
        # Mostra erro.
        return redirect(url_for('admin.servicos'))
        # Volta para lista.
    profissionais = buscar_profissionais(False)
    # Lista profissionais (ativas e inativas) para o admin marcar as aptas.
    vinculadas_atual = {
        # Constrói um conjunto com os ids das profissionais já vinculadas a este serviço.
        str(linha['profissional_id'])
        # Converte cada id para texto para casar com o value do checkbox.
        for linha in db.execute('SELECT profissional_id FROM profissionais_servicos WHERE servico_id = ?', (id,)).fetchall()
        # Busca os vínculos atuais no banco.
    }
    # Fecha o set de profissionais vinculadas.
    if request.method == 'POST':
        # Verifica envio do formulário.
        nome, preco, duracao, erro = _parse_servico_form()
        # Lê e valida formulário.
        ids_profissionais = request.form.getlist('profissionais_ids')
        # Lê as profissionais marcadas no formulário.
        if erro:
            # Verifica erro.
            return render_template('admin/servico_form.html', servico=servico, form=request.form, erro=erro, profissionais=profissionais, profissionais_selecionadas=set(ids_profissionais), empresa=EMPRESA)
            # Reabre formulário com erro mantendo o que foi marcado.
        db.execute('UPDATE servicos SET nome = ?, preco = ?, duracao_min = ? WHERE id = ?', (nome, preco, duracao, id))
        # Atualiza serviço.
        db.execute('DELETE FROM profissionais_servicos WHERE servico_id = ?', (id,))
        # Remove os vínculos antigos para reescrever conforme as marcações atuais.
        for pid in ids_profissionais:
            # Percorre cada profissional marcada.
            db.execute(
                # Insere o vínculo atualizado.
                'INSERT OR IGNORE INTO profissionais_servicos (profissional_id, servico_id) VALUES (?, ?)',
                # Usa OR IGNORE para evitar erro caso o admin marque a mesma duas vezes.
                (pid, id)
                # Envia os ids da profissional e do serviço.
            )
            # Finaliza o vínculo atual.
        db.commit()
        # Salva atualização e vínculos.
        flash(f'Serviço "{nome}" atualizado.', 'success')
        # Mostra sucesso.
        return redirect(url_for('admin.servicos'))
        # Volta para lista.
    return render_template('admin/servico_form.html', servico=servico, form=None, profissionais=profissionais, profissionais_selecionadas=vinculadas_atual, empresa=EMPRESA)
    # Abre formulário preenchido com profissionais já vinculadas marcadas.


@admin.route('/servicos/<int:id>/excluir', methods=['POST'])
# Cria rota para excluir serviço.
def servico_excluir(id):
    # Define função de exclusão.
    if not esta_logado():
        # Verifica login.
        return redirect(url_for('admin.login'))
        # Redireciona para login.
    db = get_db()
    # Abre banco.
    servico = db.execute('SELECT * FROM servicos WHERE id = ?', (id,)).fetchone()
    # Busca serviço.
    if servico is None:
        # Verifica existência.
        flash('Serviço não encontrado.', 'error')
        # Mostra erro.
        return redirect(url_for('admin.servicos'))
        # Volta para lista.
    em_uso = db.execute('SELECT COUNT(*) AS n FROM agendamentos WHERE servico_id = ?', (id,)).fetchone()['n']
    # Conta agendamentos ligados ao serviço.
    if em_uso:
        # Verifica se existe vínculo.
        flash(f'Não é possível excluir "{servico["nome"]}": existem {em_uso} agendamento(s) usando este serviço.', 'error')
        # Mostra erro.
        return redirect(url_for('admin.servicos'))
        # Volta para serviços.
    db.execute('DELETE FROM servicos WHERE id = ?', (id,))
    # Exclui serviço.
    db.commit()
    # Salva exclusão.
    flash(f'Serviço "{servico["nome"]}" excluído.', 'success')
    # Mostra sucesso.
    return redirect(url_for('admin.servicos'))
    # Volta para serviços.


@admin.route('/bloqueios', methods=['GET', 'POST'])
# Cria rota para o administrador bloquear folgas, feriados ou horários.
def bloqueios():
    # Define função de gerenciamento de bloqueios.
    if not esta_logado():
        # Verifica login.
        return redirect(url_for('admin.login'))
        # Redireciona para login.
    db = get_db()
    # Abre o banco.
    profissionais = buscar_profissionais(False)
    # Busca profissionais para o formulário.
    if request.method == 'POST':
        # Verifica se o formulário de bloqueio foi enviado.
        profissional_id = request.form.get('profissional_id', '').strip()
        # Recebe profissional.
        data_texto = request.form.get('data', '').strip()
        # Recebe data.
        horario = request.form.get('horario', '').strip()
        # Recebe horário ou vazio para dia inteiro.
        motivo = request.form.get('motivo', '').strip()
        # Recebe motivo do bloqueio.
        if profissional_id == '' or data_texto == '':
            # Verifica campos obrigatórios.
            flash('Profissional e data são obrigatórios.', 'error')
            # Mostra erro.
        else:
            # Entra aqui se os campos obrigatórios foram preenchidos.
            horario_salvo = horario if horario != 'dia_inteiro' else ''
            # Salva vazio quando o bloqueio for para o dia inteiro.
            motivo_salvo = motivo if motivo else 'Bloqueio administrativo'
            # Usa motivo padrão caso o campo esteja vazio.
            db.execute('INSERT INTO bloqueios_agenda (profissional_id, data, horario, motivo) VALUES (?, ?, ?, ?)', (profissional_id, data_texto, horario_salvo, motivo_salvo))
            # Insere o bloqueio no banco.
            db.commit()
            # Salva o bloqueio.
            flash('Bloqueio cadastrado com sucesso.', 'success')
            # Mostra sucesso.
        return redirect(url_for('admin.bloqueios'))
        # Volta para a tela de bloqueios.
    bloqueios_lista = db.execute(
        # Busca todos os bloqueios cadastrados.
        '''SELECT b.id, b.data, b.horario, b.motivo, p.nome AS profissional_nome
           FROM bloqueios_agenda b
           JOIN profissionais p ON p.id = b.profissional_id
           ORDER BY b.data DESC, p.nome, b.horario'''
        # Junta bloqueios com o nome da profissional.
    ).fetchall()
    # Guarda a lista de bloqueios.
    return render_template('admin/bloqueios.html', bloqueios=bloqueios_lista, profissionais=profissionais, horarios=HORARIOS, empresa=EMPRESA)
    # Renderiza a tela de bloqueios.


@admin.route('/bloqueios/<int:id>/excluir', methods=['POST'])
# Cria rota para excluir um bloqueio.
def bloqueio_excluir(id):
    # Define função de exclusão de bloqueio.
    if not esta_logado():
        # Verifica login.
        return redirect(url_for('admin.login'))
        # Redireciona para login.
    db = get_db()
    # Abre o banco.
    db.execute('DELETE FROM bloqueios_agenda WHERE id = ?', (id,))
    # Remove o bloqueio selecionado; o horário volta a ficar disponível se não houver agendamento ativo.
    db.commit()
    # Salva a exclusão.
    flash('Bloqueio removido. O horário voltou a ficar disponível se não houver reserva ativa.', 'success')
    # Mostra mensagem de sucesso.
    return redirect(url_for('admin.bloqueios'))
    # Volta para a tela de bloqueios.


@admin.route('/profissionais')
# Cria a rota administrativa de profissionais.
def profissionais():
    # Define a função que lista profissionais cadastradas.
    if not esta_logado():
        # Verifica login.
        return redirect(url_for('admin.login'))
        # Redireciona para login.
    db = get_db()
    # Abre o banco para consultar profissionais e seus vínculos.
    lista = db.execute(
        # Faz a consulta agregando os serviços que cada profissional atende.
        """SELECT p.id, p.nome, p.especialidade, p.foto, p.ativo,
                  COALESCE(GROUP_CONCAT(s.nome, ', '), '') AS servicos_atende
           FROM profissionais p
           LEFT JOIN profissionais_servicos ps ON ps.profissional_id = p.id
           LEFT JOIN servicos s ON s.id = ps.servico_id
           GROUP BY p.id
           ORDER BY p.ativo DESC, p.nome"""
        # Junta as tabelas para listar profissionais com seus serviços.
    ).fetchall()
    # Carrega a lista para o template.
    return render_template('admin/profissionais.html', profissionais=lista, empresa=EMPRESA)
    # Renderiza a página de profissionais.


def _parse_profissional_form():
    # Cria função auxiliar para ler o formulário de profissional.
    nome = request.form.get('nome', '').strip()
    # Lê o nome digitado.
    especialidade = request.form.get('especialidade', '').strip()
    # Lê a especialidade.
    foto = request.form.get('foto', '').strip()
    # Lê o nome do arquivo de foto (já presente em static/img).
    ativo = 1 if request.form.get('ativo') == 'on' else 0
    # Converte o checkbox em 0 ou 1 para o banco.
    erro = None
    # Inicializa a variável de erro.
    if len(nome) < 2:
        # Verifica nome muito curto.
        erro = 'Informe o nome da profissional.'
        # Define a mensagem.
    elif len(especialidade) < 2:
        # Verifica especialidade vazia.
        erro = 'Informe a especialidade.'
        # Define a mensagem.
    elif foto == '':
        # Verifica se a foto foi informada.
        erro = 'Informe o nome do arquivo da foto (ex: pamela_francisco.png).'
        # Define mensagem padrão sobre a foto.
    return nome, especialidade, foto, ativo, erro
    # Retorna os dados normalizados e o erro de validação.


@admin.route('/profissionais/nova', methods=['GET', 'POST'])
# Cria rota para cadastrar uma nova profissional.
def profissional_nova():
    # Define a função de cadastro.
    if not esta_logado():
        # Verifica login.
        return redirect(url_for('admin.login'))
        # Redireciona para login.
    db = get_db()
    # Abre o banco para gravar a profissional e seus vínculos.
    servicos = buscar_servicos()
    # Lista os serviços para permitir escolher quais a profissional atende.
    if request.method == 'POST':
        # Verifica envio do formulário.
        nome, especialidade, foto, ativo, erro = _parse_profissional_form()
        # Lê e valida os dados do formulário.
        ids_servicos = request.form.getlist('servicos_ids')
        # Lê quais serviços foram marcados para essa profissional.
        if erro:
            # Verifica se houve erro de validação.
            return render_template('admin/profissional_form.html', profissional=None, form=request.form, erro=erro, servicos=servicos, servicos_selecionados=set(ids_servicos), empresa=EMPRESA)
            # Reabre o formulário com erro mantendo o que foi digitado.
        cursor = db.execute(
            # Insere a profissional no banco.
            'INSERT INTO profissionais (nome, especialidade, foto, ativo) VALUES (?, ?, ?, ?)',
            # Usa parâmetros para evitar injeção de SQL.
            (nome, especialidade, foto, ativo)
            # Envia os dados.
        )
        # Finaliza o insert principal.
        novo_id = cursor.lastrowid
        # Guarda o id da nova profissional para os vínculos a seguir.
        for sid in ids_servicos:
            # Percorre cada serviço marcado.
            db.execute(
                # Insere o vínculo entre profissional e serviço.
                'INSERT OR IGNORE INTO profissionais_servicos (profissional_id, servico_id) VALUES (?, ?)',
                # OR IGNORE evita duplicidade.
                (novo_id, sid)
                # Envia os ids.
            )
            # Encerra o vínculo atual.
        db.commit()
        # Salva tudo de uma vez.
        flash(f'Profissional "{nome}" cadastrada com sucesso.', 'success')
        # Mostra mensagem de sucesso.
        return redirect(url_for('admin.profissionais'))
        # Volta para a lista.
    return render_template('admin/profissional_form.html', profissional=None, form=None, servicos=servicos, servicos_selecionados=set(), empresa=EMPRESA)
    # Abre o formulário vazio.


@admin.route('/profissionais/<int:id>/editar', methods=['GET', 'POST'])
# Cria rota para editar dados de uma profissional.
def profissional_editar(id):
    # Define a função de edição.
    if not esta_logado():
        # Verifica login.
        return redirect(url_for('admin.login'))
        # Redireciona para login.
    db = get_db()
    # Abre o banco.
    profissional = db.execute('SELECT * FROM profissionais WHERE id = ?', (id,)).fetchone()
    # Busca a profissional.
    if profissional is None:
        # Verifica se existe.
        flash('Profissional não encontrada.', 'error')
        # Mostra erro.
        return redirect(url_for('admin.profissionais'))
        # Volta para a lista.
    servicos = buscar_servicos()
    # Lista todos os serviços para o admin marcar quais ela atende.
    vinculadas_atual = {
        # Calcula os ids dos serviços já vinculados.
        str(linha['servico_id'])
        # Converte cada id para texto.
        for linha in db.execute('SELECT servico_id FROM profissionais_servicos WHERE profissional_id = ?', (id,)).fetchall()
        # Busca os vínculos atuais.
    }
    # Fecha o set de serviços vinculados.
    if request.method == 'POST':
        # Verifica envio do formulário.
        nome, especialidade, foto, ativo, erro = _parse_profissional_form()
        # Lê e valida os dados.
        ids_servicos = request.form.getlist('servicos_ids')
        # Lê os serviços marcados.
        if erro:
            # Verifica erro de validação.
            return render_template('admin/profissional_form.html', profissional=profissional, form=request.form, erro=erro, servicos=servicos, servicos_selecionados=set(ids_servicos), empresa=EMPRESA)
            # Reabre o formulário mantendo o que foi digitado.
        db.execute(
            # Atualiza os dados principais da profissional.
            'UPDATE profissionais SET nome = ?, especialidade = ?, foto = ?, ativo = ? WHERE id = ?',
            # Atualiza tudo de uma vez.
            (nome, especialidade, foto, ativo, id)
            # Envia os dados para o SQLite.
        )
        # Finaliza o update principal.
        db.execute('DELETE FROM profissionais_servicos WHERE profissional_id = ?', (id,))
        # Apaga os vínculos antigos para reescrever conforme a tela.
        for sid in ids_servicos:
            # Percorre cada serviço marcado.
            db.execute(
                # Insere o vínculo atualizado.
                'INSERT OR IGNORE INTO profissionais_servicos (profissional_id, servico_id) VALUES (?, ?)',
                # Mantém OR IGNORE por segurança.
                (id, sid)
                # Envia os ids.
            )
            # Encerra o vínculo atual.
        db.commit()
        # Salva tudo.
        flash(f'Profissional "{nome}" atualizada.', 'success')
        # Mensagem de sucesso.
        return redirect(url_for('admin.profissionais'))
        # Volta para a lista.
    return render_template('admin/profissional_form.html', profissional=profissional, form=None, servicos=servicos, servicos_selecionados=vinculadas_atual, empresa=EMPRESA)
    # Abre o formulário preenchido com os dados atuais.


@admin.route('/profissionais/<int:id>/ativar', methods=['POST'])
# Cria rota para alternar o status ativo/inativo da profissional.
def profissional_alternar_ativo(id):
    # Define a função que alterna o status.
    if not esta_logado():
        # Verifica login.
        return redirect(url_for('admin.login'))
        # Redireciona para login.
    db = get_db()
    # Abre o banco.
    profissional = db.execute('SELECT * FROM profissionais WHERE id = ?', (id,)).fetchone()
    # Busca a profissional.
    if profissional is None:
        # Verifica se existe.
        flash('Profissional não encontrada.', 'error')
        # Mostra erro.
        return redirect(url_for('admin.profissionais'))
        # Volta para a lista.
    novo_status = 0 if profissional['ativo'] else 1
    # Calcula o status invertido.
    db.execute('UPDATE profissionais SET ativo = ? WHERE id = ?', (novo_status, id))
    # Aplica a mudança.
    db.commit()
    # Salva.
    if novo_status:
        # Verifica se foi reativada.
        flash(f'Profissional "{profissional["nome"]}" reativada.', 'success')
        # Mensagem para reativada.
    else:
        # Caso contrário, foi inativada.
        flash(f'Profissional "{profissional["nome"]}" inativada. Ela deixa de aparecer no agendamento.', 'info')
        # Mensagem para inativada.
    return redirect(url_for('admin.profissionais'))
    # Volta para a lista.


@admin.route('/profissionais/<int:id>/excluir', methods=['POST'])
# Cria rota para excluir uma profissional definitivamente.
def profissional_excluir(id):
    # Define a função de exclusão.
    if not esta_logado():
        # Verifica login.
        return redirect(url_for('admin.login'))
        # Redireciona para login.
    db = get_db()
    # Abre o banco.
    profissional = db.execute('SELECT * FROM profissionais WHERE id = ?', (id,)).fetchone()
    # Busca a profissional.
    if profissional is None:
        # Verifica se existe.
        flash('Profissional não encontrada.', 'error')
        # Mostra erro.
        return redirect(url_for('admin.profissionais'))
        # Volta para a lista.
    em_uso = db.execute('SELECT COUNT(*) AS n FROM agendamentos WHERE profissional_id = ?', (id,)).fetchone()['n']
    # Conta quantos agendamentos referenciam essa profissional.
    if em_uso:
        # Verifica se existem agendamentos.
        flash(f'Não é possível excluir "{profissional["nome"]}": existem {em_uso} agendamento(s) associado(s). Inative em vez de excluir.', 'error')
        # Mensagem orientando o admin a inativar.
        return redirect(url_for('admin.profissionais'))
        # Volta para a lista.
    db.execute('DELETE FROM profissionais_servicos WHERE profissional_id = ?', (id,))
    # Remove os vínculos antes de apagar a profissional.
    db.execute('DELETE FROM bloqueios_agenda WHERE profissional_id = ?', (id,))
    # Remove eventuais bloqueios cadastrados para essa profissional.
    db.execute('DELETE FROM profissionais WHERE id = ?', (id,))
    # Exclui a profissional.
    db.commit()
    # Salva tudo.
    flash(f'Profissional "{profissional["nome"]}" excluída.', 'success')
    # Mensagem de sucesso.
    return redirect(url_for('admin.profissionais'))
    # Volta para a lista.


@admin.route('/clientes')
# Cria a rota administrativa de clientes.
def clientes():
    # Define a função que lista clientes que já agendaram.
    if not esta_logado():
        # Verifica login.
        return redirect(url_for('admin.login'))
        # Redireciona para login.
    busca = request.args.get('q', '').strip()
    # Lê o termo de busca opcional.
    db = get_db()
    # Abre o banco.
    sql = """SELECT c.id, c.nome, c.telefone,
                    COUNT(a.id) AS total_agendamentos,
                    SUM(CASE WHEN a.status = 'cancelado' THEN 1 ELSE 0 END) AS total_cancelados,
                    SUM(CASE WHEN a.status = 'confirmado' THEN 1 ELSE 0 END) AS total_confirmados,
                    MAX(a.data) AS ultimo_atendimento
             FROM clientes c
             LEFT JOIN agendamentos a ON a.cliente_id = c.id"""
    # Monta a consulta principal somando estatísticas por cliente.
    params = []
    # Cria a lista de parâmetros.
    if busca:
        # Verifica se há busca.
        sql += ' WHERE c.nome LIKE ? OR c.telefone LIKE ?'
        # Adiciona filtro por nome ou telefone.
        like = f'%{busca}%'
        # Monta o padrão LIKE.
        params.extend([like, like])
        # Adiciona o padrão para nome e telefone.
    sql += ' GROUP BY c.id ORDER BY c.nome'
    # Finaliza agrupando por cliente.
    lista = db.execute(sql, params).fetchall()
    # Executa a consulta.
    return render_template('admin/clientes.html', clientes=lista, busca=busca, empresa=EMPRESA)
    # Renderiza a página de clientes.


@admin.route('/clientes/<int:id>')
# Cria a rota de detalhe da cliente.
def cliente_detalhe(id):
    # Define a função que mostra histórico de uma cliente.
    if not esta_logado():
        # Verifica login.
        return redirect(url_for('admin.login'))
        # Redireciona para login.
    db = get_db()
    # Abre o banco.
    cliente = db.execute('SELECT * FROM clientes WHERE id = ?', (id,)).fetchone()
    # Busca a cliente.
    if cliente is None:
        # Verifica se existe.
        flash('Cliente não encontrada.', 'error')
        # Mostra erro.
        return redirect(url_for('admin.clientes'))
        # Volta para a lista.
    agendamentos = db.execute(
        # Busca todo o histórico de agendamentos da cliente.
        """SELECT a.id, a.data, a.horario, a.status,
                  s.nome AS servico_nome, s.preco,
                  p.nome AS profissional_nome
           FROM agendamentos a
           JOIN servicos s ON s.id = a.servico_id
           JOIN profissionais p ON p.id = a.profissional_id
           WHERE a.cliente_id = ?
           ORDER BY a.data DESC, a.horario DESC""",
        # Busca os agendamentos ordenados do mais recente para o mais antigo.
        (id,)
        # Envia o id da cliente.
    ).fetchall()
    # Carrega o histórico.
    return render_template('admin/cliente_detalhe.html', cliente=cliente, agendamentos=agendamentos, empresa=EMPRESA)
    # Renderiza a página de detalhe.


app.register_blueprint(publico)
# Registra as rotas públicas dentro do Flask.

app.register_blueprint(admin)
# Registra as rotas administrativas dentro do Flask.


@app.teardown_appcontext
# Define função executada ao final de cada requisição.
def close_db(e=None):
    # Fecha a conexão com o banco quando ela existir.
    from flask import g
    # Importa o objeto g usado para guardar a conexão.
    db = g.pop('db', None)
    # Remove a conexão do g se ela existir.
    if db is not None:
        # Verifica se existe uma conexão aberta.
        db.close()
        # Fecha a conexão.


if __name__ == '__main__':
    # Garante que o código abaixo execute apenas ao rodar python app.py.
    init_db()
    # Inicializa o banco, tabelas, serviços e profissionais.
    app.run(debug=True)
    # Inicia o servidor Flask em modo debug.
