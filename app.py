from flask import Flask, Blueprint, render_template, request, redirect, url_for, jsonify, session, flash

from database import init_db, get_db

from datetime import date, datetime, timedelta

import calendar

app = Flask(__name__)

app.config['SECRET_KEY'] = 'esmalteria-secret-key'

publico = Blueprint('publico', __name__)

admin = Blueprint('admin', __name__, url_prefix='/admin')

EMPRESA = {
    'nome': 'Refúgio da Preta',
    'dona': 'Pamela Francisco',
    'telefone': '(11) 99220-4706',
    'endereco': 'Rua Carapicuíba, 143 - BNH Grajaú',
    'horarios': 'Terça a sábado, das 10h às 19h',
    'instagram_nome': '@refugiodapreta',
    'instagram_url': 'https://www.instagram.com/refugiodapreta/',
    'foto_dona': 'pamela_francisco.png',
    'slogan': 'Beleza, cuidado e acolhimento.',
}

HORARIOS = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00']

# weekday(): segunda=0, terça=1, quarta=2, quinta=3, sexta=4, sábado=5
DIAS_FUNCIONAMENTO = {1, 2, 3, 4, 5}

ADMIN_USUARIO = 'admin'

ADMIN_SENHA = 'esmalteria123'


def esta_logado():
    return session.get('logado') is True


def buscar_servicos():
    db = get_db()
    return db.execute('SELECT * FROM servicos ORDER BY id').fetchall()


def buscar_profissionais(apenas_ativas=True):
    db = get_db()
    if apenas_ativas:
        return db.execute('SELECT * FROM profissionais WHERE ativo = 1 ORDER BY id').fetchall()
    return db.execute('SELECT * FROM profissionais ORDER BY id').fetchall()


def buscar_vinculos_profissionais_servicos():
    db = get_db()
    linhas = db.execute('SELECT profissional_id, servico_id FROM profissionais_servicos').fetchall()
    mapa = {}
    for linha in linhas:
        profissional_id = str(linha['profissional_id'])
        servico_id = str(linha['servico_id'])
        if profissional_id not in mapa:
            mapa[profissional_id] = []
        mapa[profissional_id].append(servico_id)
    return mapa


def profissional_atende_servico(profissional_id, servico_id):
    if profissional_id == '' or servico_id == '':
        return False
    db = get_db()
    vinculo = db.execute(
        'SELECT 1 FROM profissionais_servicos WHERE profissional_id = ? AND servico_id = ?',
        (profissional_id, servico_id)
    ).fetchone()
    return vinculo is not None


def dia_funciona(data_texto):
    try:
        data_objeto = date.fromisoformat(data_texto)
    except ValueError:
        return False
    return data_objeto.weekday() in DIAS_FUNCIONAMENTO


def buscar_bloqueios(data_texto, profissional_id):
    if data_texto == '' or profissional_id == '':
        return []
    db = get_db()
    return db.execute(
        'SELECT * FROM bloqueios_agenda WHERE data = ? AND profissional_id = ? ORDER BY horario',
        (data_texto, profissional_id)
    ).fetchall()


def buscar_horarios_indisponiveis(data_texto, profissional_id, ignorar_agendamento_id=None):
    if data_texto == '' or profissional_id == '':
        return set()
    indisponiveis = set()
    if not dia_funciona(data_texto):
        return set(HORARIOS)
    db = get_db()
    sql = 'SELECT horario FROM agendamentos WHERE data = ? AND profissional_id = ? AND status != ?'
    parametros = [data_texto, profissional_id, 'cancelado']
    if ignorar_agendamento_id is not None:
        # Evita conflito do agendamento consigo mesmo durante remarcação
        sql += ' AND id != ?'
        parametros.append(ignorar_agendamento_id)
    agendados = db.execute(sql, parametros).fetchall()
    for linha in agendados:
        indisponiveis.add(linha['horario'])
    bloqueios = buscar_bloqueios(data_texto, profissional_id)
    for bloqueio in bloqueios:
        if bloqueio['horario'] in (None, ''):
            indisponiveis.update(HORARIOS)
        else:
            indisponiveis.add(bloqueio['horario'])
    return indisponiveis


def montar_lista_horarios(data_texto, profissional_id, ignorar_agendamento_id=None):
    indisponiveis = buscar_horarios_indisponiveis(data_texto, profissional_id, ignorar_agendamento_id)
    lista = []
    for horario in HORARIOS:
        disponivel = horario not in indisponiveis
        lista.append({'horario': horario, 'disponivel': disponivel})
    return lista


def contar_horarios_disponiveis(data_texto, profissional_id):
    lista = montar_lista_horarios(data_texto, profissional_id)
    return sum(1 for item in lista if item['disponivel'])


def conflito_agenda(data_texto, horario, profissional_id, ignorar_agendamento_id=None):
    indisponiveis = buscar_horarios_indisponiveis(data_texto, profissional_id, ignorar_agendamento_id)
    return horario in indisponiveis


@publico.route('/')
def index():
    servicos = buscar_servicos()
    galeria = [
        {'arquivo': 'trabalho1.png', 'titulo': 'Esmaltação marrom nude elegante'},
        {'arquivo': 'trabalho2.png', 'titulo': 'Atendimento com cuidado e técnica'},
        {'arquivo': 'trabalho3.png', 'titulo': 'Nude com brilho delicado'},
    ]
    return render_template('index.html', servicos=servicos, empresa=EMPRESA, galeria=galeria)


@publico.route('/agendar', methods=['GET'])
def agendar_get():
    servicos = buscar_servicos()
    profissionais = buscar_profissionais()
    profissionais_servicos = buscar_vinculos_profissionais_servicos()
    dados = {'nome': '', 'telefone': '', 'servico_id': '', 'profissional_id': '', 'data': '', 'horario': ''}
    return render_template('agendamento.html', servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, empresa=EMPRESA, horarios=HORARIOS, horarios_ocupados=[], dados=dados, erro=None)


@publico.route('/agendar', methods=['POST'])
def agendar_post():
    db = get_db()
    nome = request.form.get('nome', '').strip()
    telefone = request.form.get('telefone', '').strip()
    servico_id = request.form.get('servico_id', '').strip()
    profissional_id = request.form.get('profissional_id', '').strip()
    data_texto = request.form.get('data', '').strip()
    horario = request.form.get('horario', '').strip()
    dados = {'nome': nome, 'telefone': telefone, 'servico_id': servico_id, 'profissional_id': profissional_id, 'data': data_texto, 'horario': horario}

    def erro_form(msg):
        servicos = buscar_servicos()
        profissionais = buscar_profissionais()
        profissionais_servicos = buscar_vinculos_profissionais_servicos()
        horarios_ocupados = buscar_horarios_indisponiveis(data_texto, profissional_id)
        return render_template('agendamento.html', servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, empresa=EMPRESA, horarios=HORARIOS, horarios_ocupados=horarios_ocupados, dados=dados, erro=msg)

    if len(nome) < 2:
        return erro_form('Informe um nome válido.')
    if len(telefone) < 8:
        return erro_form('Informe um telefone válido.')
    if servico_id == '':
        return erro_form('Selecione um serviço.')
    if profissional_id == '':
        return erro_form('Selecione uma profissional.')
    if not profissional_atende_servico(profissional_id, servico_id):
        return erro_form('Selecione uma profissional disponível para esse serviço.')
    if data_texto == '':
        return erro_form('Selecione uma data no calendário.')
    if not dia_funciona(data_texto):
        return erro_form('Selecione uma data entre terça e sábado.')
    if horario == '':
        return erro_form('Selecione um horário disponível.')
    if conflito_agenda(data_texto, horario, profissional_id):
        return erro_form('Horário indisponível para a profissional selecionada.')

    cliente = db.execute('SELECT id FROM clientes WHERE telefone = ?', (telefone,)).fetchone()
    if cliente:
        cliente_id = cliente['id']
    else:
        cursor = db.execute('INSERT INTO clientes (nome, telefone) VALUES (?, ?)', (nome, telefone))
        cliente_id = cursor.lastrowid

    db.execute('INSERT INTO agendamentos (cliente_id, servico_id, profissional_id, data, horario, status) VALUES (?, ?, ?, ?, ?, ?)', (cliente_id, servico_id, profissional_id, data_texto, horario, 'pendente'))
    db.commit()
    return redirect(url_for('publico.confirmacao'))


@publico.route('/confirmacao')
def confirmacao():
    return render_template('confirmacao.html', empresa=EMPRESA)


@publico.route('/horarios-disponiveis')
def horarios_disponiveis():
    data_texto = request.args.get('data', '').strip()
    profissional_id = request.args.get('profissional_id', '').strip()
    horarios = montar_lista_horarios(data_texto, profissional_id)
    return jsonify({'data': data_texto, 'horarios': horarios})


@publico.route('/disponibilidade-mes')
def disponibilidade_mes():
    ano = int(request.args.get('ano', date.today().year))
    mes = int(request.args.get('mes', date.today().month))
    profissional_id = request.args.get('profissional_id', '').strip()
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    resposta = {}
    for dia in range(1, ultimo_dia + 1):
        data_texto = f'{ano:04d}-{mes:02d}-{dia:02d}'
        aberto = dia_funciona(data_texto)
        livres = contar_horarios_disponiveis(data_texto, profissional_id) if profissional_id and aberto else 0
        resposta[data_texto] = {'aberto': aberto, 'livres': livres, 'total': len(HORARIOS)}
    return jsonify(resposta)


@admin.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario', '')
        senha = request.form.get('senha', '')
        if usuario == ADMIN_USUARIO and senha == ADMIN_SENHA:
            session['logado'] = True
            return redirect(url_for('admin.dashboard'))
        return render_template('admin/login.html', erro='Usuário ou senha inválidos.', empresa=EMPRESA)
    return render_template('admin/login.html', empresa=EMPRESA)


@admin.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.login'))


@admin.route('/dashboard')
def dashboard():
    if not esta_logado():
        return redirect(url_for('admin.login'))
    filtro_status = request.args.get('status', '').strip()
    filtro_data = request.args.get('data', '').strip()
    filtro_profissional = request.args.get('profissional_id', '').strip()
    sql = '''SELECT a.id, a.data, a.horario, a.status,
                    c.nome AS cliente_nome, c.telefone,
                    s.nome AS servico_nome, s.preco, s.duracao_min,
                    p.nome AS profissional_nome
             FROM agendamentos a
             JOIN clientes c ON c.id = a.cliente_id
             JOIN servicos s ON s.id = a.servico_id
             JOIN profissionais p ON p.id = a.profissional_id'''
    where = []
    params = []
    if filtro_status in ('pendente', 'confirmado', 'cancelado'):
        where.append('a.status = ?')
        params.append(filtro_status)
    if filtro_data:
        where.append('a.data = ?')
        params.append(filtro_data)
    if filtro_profissional:
        where.append('a.profissional_id = ?')
        params.append(filtro_profissional)
    if where:
        sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY a.data, a.horario'
    db = get_db()
    agendamentos = db.execute(sql, params).fetchall()
    profissionais = buscar_profissionais(False)
    kpis = calcular_kpis_dashboard(db)
    return render_template('admin/dashboard.html', agendamentos=agendamentos, profissionais=profissionais, filtro_status=filtro_status, filtro_data=filtro_data, filtro_profissional=filtro_profissional, empresa=EMPRESA, kpis=kpis)


def calcular_kpis_dashboard(db):
    hoje = date.today().isoformat()
    inicio_semana = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    fim_semana = (date.today() + timedelta(days=6 - date.today().weekday())).isoformat()
    total_hoje = db.execute(
        "SELECT COUNT(*) AS n FROM agendamentos WHERE data = ? AND status != 'cancelado'",
        (hoje,)
    ).fetchone()['n']
    confirmados_hoje = db.execute(
        "SELECT COUNT(*) AS n FROM agendamentos WHERE data = ? AND status = 'confirmado'",
        (hoje,)
    ).fetchone()['n']
    pendentes = db.execute(
        "SELECT COUNT(*) AS n FROM agendamentos WHERE status = 'pendente' AND data >= ?",
        (hoje,)
    ).fetchone()['n']
    receita_semana = db.execute(
        """SELECT COALESCE(SUM(s.preco), 0) AS total
           FROM agendamentos a
           JOIN servicos s ON s.id = a.servico_id
           WHERE a.data BETWEEN ? AND ? AND a.status != 'cancelado'""",
        (inicio_semana, fim_semana)
    ).fetchone()['total']
    profissionais_ativas = db.execute(
        "SELECT COUNT(*) AS n FROM profissionais WHERE ativo = 1"
    ).fetchone()['n']
    return {
        'hoje': total_hoje,
        'confirmados_hoje': confirmados_hoje,
        'pendentes': pendentes,
        'receita_semana': receita_semana,
        'profissionais_ativas': profissionais_ativas,
    }


@admin.route('/agendamento/<int:id>/status', methods=['POST'])
def atualizar_status(id):
    if not esta_logado():
        return redirect(url_for('admin.login'))
    novo_status = request.form.get('novo_status')
    if novo_status not in ('pendente', 'confirmado', 'cancelado'):
        flash('Status inválido.', 'error')
        return redirect(url_for('admin.dashboard'))
    db = get_db()
    db.execute('UPDATE agendamentos SET status = ? WHERE id = ?', (novo_status, id))
    db.commit()
    flash('Status do agendamento atualizado.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin.route('/agendamento/<int:id>/editar', methods=['GET', 'POST'])
def agendamento_editar(id):
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    agendamento = db.execute('SELECT * FROM agendamentos WHERE id = ?', (id,)).fetchone()
    if agendamento is None:
        flash('Agendamento não encontrado.', 'error')
        return redirect(url_for('admin.dashboard'))
    servicos = buscar_servicos()
    profissionais = buscar_profissionais(False)
    profissionais_servicos = buscar_vinculos_profissionais_servicos()
    if request.method == 'POST':
        servico_id = request.form.get('servico_id', '').strip()
        profissional_id = request.form.get('profissional_id', '').strip()
        data_texto = request.form.get('data', '').strip()
        horario = request.form.get('horario', '').strip()
        status = request.form.get('status', '').strip()
        if servico_id == '' or profissional_id == '' or data_texto == '' or horario == '' or status == '':
            flash('Preencha todos os campos do agendamento.', 'error')
            lista_horarios = montar_lista_horarios(data_texto, profissional_id, ignorar_agendamento_id=id)
            return render_template('admin/agendamento_form.html', agendamento=agendamento, servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, lista_horarios=lista_horarios, empresa=EMPRESA)
        if not profissional_atende_servico(profissional_id, servico_id):
            flash('A profissional escolhida não atende esse serviço.', 'error')
            lista_horarios = montar_lista_horarios(data_texto, profissional_id, ignorar_agendamento_id=id)
            return render_template('admin/agendamento_form.html', agendamento=agendamento, servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, lista_horarios=lista_horarios, empresa=EMPRESA)
        if status != 'cancelado' and conflito_agenda(data_texto, horario, profissional_id, id):
            flash('Este horário está indisponível para a profissional escolhida.', 'error')
            lista_horarios = montar_lista_horarios(data_texto, profissional_id, ignorar_agendamento_id=id)
            return render_template('admin/agendamento_form.html', agendamento=agendamento, servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, lista_horarios=lista_horarios, empresa=EMPRESA)
        db.execute('UPDATE agendamentos SET servico_id = ?, profissional_id = ?, data = ?, horario = ?, status = ? WHERE id = ?', (servico_id, profissional_id, data_texto, horario, status, id))
        db.commit()
        flash('Agendamento atualizado com sucesso.', 'success')
        return redirect(url_for('admin.dashboard'))
    lista_horarios = montar_lista_horarios(agendamento['data'], str(agendamento['profissional_id']), ignorar_agendamento_id=id)
    return render_template('admin/agendamento_form.html', agendamento=agendamento, servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, lista_horarios=lista_horarios, empresa=EMPRESA)


@admin.route('/servicos')
def servicos():
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    lista = db.execute(
        """SELECT s.id, s.nome, s.preco, s.duracao_min,
                  COALESCE(GROUP_CONCAT(p.nome, ', '), '') AS profissionais_atendem
           FROM servicos s
           LEFT JOIN profissionais_servicos ps ON ps.servico_id = s.id
           LEFT JOIN profissionais p ON p.id = ps.profissional_id AND p.ativo = 1
           GROUP BY s.id
           ORDER BY s.id"""
    ).fetchall()
    return render_template('admin/servicos.html', servicos=lista, empresa=EMPRESA)


def _parse_servico_form():
    nome = request.form.get('nome', '').strip()
    preco_raw = request.form.get('preco', '').strip().replace(',', '.')
    duracao_raw = request.form.get('duracao_min', '').strip()
    erro = None
    preco = duracao = None
    try:
        preco = float(preco_raw)
        duracao = int(duracao_raw)
    except ValueError:
        erro = 'Preço e duração precisam ser numéricos.'
    if not erro:
        if not nome:
            erro = 'Nome é obrigatório.'
        elif preco < 0:
            erro = 'Preço não pode ser negativo.'
        elif duracao <= 0:
            erro = 'Duração deve ser maior que zero.'
    return nome, preco, duracao, erro


@admin.route('/servicos/novo', methods=['GET', 'POST'])
def servico_novo():
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    profissionais = buscar_profissionais(False)
    if request.method == 'POST':
        nome, preco, duracao, erro = _parse_servico_form()
        ids_profissionais = request.form.getlist('profissionais_ids')
        if erro:
            return render_template('admin/servico_form.html', servico=None, form=request.form, erro=erro, profissionais=profissionais, profissionais_selecionadas=set(ids_profissionais), empresa=EMPRESA)
        cursor = db.execute('INSERT INTO servicos (nome, preco, duracao_min) VALUES (?, ?, ?)', (nome, preco, duracao))
        novo_id = cursor.lastrowid
        for pid in ids_profissionais:
            db.execute(
                'INSERT OR IGNORE INTO profissionais_servicos (profissional_id, servico_id) VALUES (?, ?)',
                (pid, novo_id)
            )
        db.commit()
        flash(f'Serviço "{nome}" criado com sucesso.', 'success')
        return redirect(url_for('admin.servicos'))
    return render_template('admin/servico_form.html', servico=None, form=None, profissionais=profissionais, profissionais_selecionadas=set(), empresa=EMPRESA)


@admin.route('/servicos/<int:id>/editar', methods=['GET', 'POST'])
def servico_editar(id):
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    servico = db.execute('SELECT * FROM servicos WHERE id = ?', (id,)).fetchone()
    if servico is None:
        flash('Serviço não encontrado.', 'error')
        return redirect(url_for('admin.servicos'))
    profissionais = buscar_profissionais(False)
    vinculadas_atual = {
        str(linha['profissional_id'])
        for linha in db.execute('SELECT profissional_id FROM profissionais_servicos WHERE servico_id = ?', (id,)).fetchall()
    }
    if request.method == 'POST':
        nome, preco, duracao, erro = _parse_servico_form()
        ids_profissionais = request.form.getlist('profissionais_ids')
        if erro:
            return render_template('admin/servico_form.html', servico=servico, form=request.form, erro=erro, profissionais=profissionais, profissionais_selecionadas=set(ids_profissionais), empresa=EMPRESA)
        db.execute('UPDATE servicos SET nome = ?, preco = ?, duracao_min = ? WHERE id = ?', (nome, preco, duracao, id))
        db.execute('DELETE FROM profissionais_servicos WHERE servico_id = ?', (id,))
        for pid in ids_profissionais:
            db.execute(
                'INSERT OR IGNORE INTO profissionais_servicos (profissional_id, servico_id) VALUES (?, ?)',
                (pid, id)
            )
        db.commit()
        flash(f'Serviço "{nome}" atualizado.', 'success')
        return redirect(url_for('admin.servicos'))
    return render_template('admin/servico_form.html', servico=servico, form=None, profissionais=profissionais, profissionais_selecionadas=vinculadas_atual, empresa=EMPRESA)


@admin.route('/servicos/<int:id>/excluir', methods=['POST'])
def servico_excluir(id):
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    servico = db.execute('SELECT * FROM servicos WHERE id = ?', (id,)).fetchone()
    if servico is None:
        flash('Serviço não encontrado.', 'error')
        return redirect(url_for('admin.servicos'))
    em_uso = db.execute('SELECT COUNT(*) AS n FROM agendamentos WHERE servico_id = ?', (id,)).fetchone()['n']
    if em_uso:
        flash(f'Não é possível excluir "{servico["nome"]}": existem {em_uso} agendamento(s) usando este serviço.', 'error')
        return redirect(url_for('admin.servicos'))
    db.execute('DELETE FROM servicos WHERE id = ?', (id,))
    db.commit()
    flash(f'Serviço "{servico["nome"]}" excluído.', 'success')
    return redirect(url_for('admin.servicos'))


@admin.route('/bloqueios', methods=['GET', 'POST'])
def bloqueios():
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    profissionais = buscar_profissionais(False)
    if request.method == 'POST':
        profissional_id = request.form.get('profissional_id', '').strip()
        data_texto = request.form.get('data', '').strip()
        horario = request.form.get('horario', '').strip()
        motivo = request.form.get('motivo', '').strip()
        if profissional_id == '' or data_texto == '':
            flash('Profissional e data são obrigatórios.', 'error')
        else:
            horario_salvo = horario if horario != 'dia_inteiro' else ''
            motivo_salvo = motivo if motivo else 'Bloqueio administrativo'
            db.execute('INSERT INTO bloqueios_agenda (profissional_id, data, horario, motivo) VALUES (?, ?, ?, ?)', (profissional_id, data_texto, horario_salvo, motivo_salvo))
            db.commit()
            flash('Bloqueio cadastrado com sucesso.', 'success')
        return redirect(url_for('admin.bloqueios'))
    bloqueios_lista = db.execute(
        '''SELECT b.id, b.data, b.horario, b.motivo, p.nome AS profissional_nome
           FROM bloqueios_agenda b
           JOIN profissionais p ON p.id = b.profissional_id
           ORDER BY b.data DESC, p.nome, b.horario'''
    ).fetchall()
    return render_template('admin/bloqueios.html', bloqueios=bloqueios_lista, profissionais=profissionais, horarios=HORARIOS, empresa=EMPRESA)


@admin.route('/bloqueios/<int:id>/excluir', methods=['POST'])
def bloqueio_excluir(id):
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    db.execute('DELETE FROM bloqueios_agenda WHERE id = ?', (id,))
    db.commit()
    flash('Bloqueio removido. O horário voltou a ficar disponível se não houver reserva ativa.', 'success')
    return redirect(url_for('admin.bloqueios'))


@admin.route('/profissionais')
def profissionais():
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    lista = db.execute(
        """SELECT p.id, p.nome, p.especialidade, p.foto, p.ativo,
                  COALESCE(GROUP_CONCAT(s.nome, ', '), '') AS servicos_atende
           FROM profissionais p
           LEFT JOIN profissionais_servicos ps ON ps.profissional_id = p.id
           LEFT JOIN servicos s ON s.id = ps.servico_id
           GROUP BY p.id
           ORDER BY p.ativo DESC, p.nome"""
    ).fetchall()
    return render_template('admin/profissionais.html', profissionais=lista, empresa=EMPRESA)


def _parse_profissional_form():
    nome = request.form.get('nome', '').strip()
    especialidade = request.form.get('especialidade', '').strip()
    foto = request.form.get('foto', '').strip()
    ativo = 1 if request.form.get('ativo') == 'on' else 0
    erro = None
    if len(nome) < 2:
        erro = 'Informe o nome da profissional.'
    elif len(especialidade) < 2:
        erro = 'Informe a especialidade.'
    elif foto == '':
        erro = 'Informe o nome do arquivo da foto (ex: pamela_francisco.png).'
    return nome, especialidade, foto, ativo, erro


@admin.route('/profissionais/nova', methods=['GET', 'POST'])
def profissional_nova():
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    servicos = buscar_servicos()
    if request.method == 'POST':
        nome, especialidade, foto, ativo, erro = _parse_profissional_form()
        ids_servicos = request.form.getlist('servicos_ids')
        if erro:
            return render_template('admin/profissional_form.html', profissional=None, form=request.form, erro=erro, servicos=servicos, servicos_selecionados=set(ids_servicos), empresa=EMPRESA)
        cursor = db.execute(
            'INSERT INTO profissionais (nome, especialidade, foto, ativo) VALUES (?, ?, ?, ?)',
            (nome, especialidade, foto, ativo)
        )
        novo_id = cursor.lastrowid
        for sid in ids_servicos:
            db.execute(
                'INSERT OR IGNORE INTO profissionais_servicos (profissional_id, servico_id) VALUES (?, ?)',
                (novo_id, sid)
            )
        db.commit()
        flash(f'Profissional "{nome}" cadastrada com sucesso.', 'success')
        return redirect(url_for('admin.profissionais'))
    return render_template('admin/profissional_form.html', profissional=None, form=None, servicos=servicos, servicos_selecionados=set(), empresa=EMPRESA)


@admin.route('/profissionais/<int:id>/editar', methods=['GET', 'POST'])
def profissional_editar(id):
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    profissional = db.execute('SELECT * FROM profissionais WHERE id = ?', (id,)).fetchone()
    if profissional is None:
        flash('Profissional não encontrada.', 'error')
        return redirect(url_for('admin.profissionais'))
    servicos = buscar_servicos()
    vinculadas_atual = {
        str(linha['servico_id'])
        for linha in db.execute('SELECT servico_id FROM profissionais_servicos WHERE profissional_id = ?', (id,)).fetchall()
    }
    if request.method == 'POST':
        nome, especialidade, foto, ativo, erro = _parse_profissional_form()
        ids_servicos = request.form.getlist('servicos_ids')
        if erro:
            return render_template('admin/profissional_form.html', profissional=profissional, form=request.form, erro=erro, servicos=servicos, servicos_selecionados=set(ids_servicos), empresa=EMPRESA)
        db.execute(
            'UPDATE profissionais SET nome = ?, especialidade = ?, foto = ?, ativo = ? WHERE id = ?',
            (nome, especialidade, foto, ativo, id)
        )
        db.execute('DELETE FROM profissionais_servicos WHERE profissional_id = ?', (id,))
        for sid in ids_servicos:
            db.execute(
                'INSERT OR IGNORE INTO profissionais_servicos (profissional_id, servico_id) VALUES (?, ?)',
                (id, sid)
            )
        db.commit()
        flash(f'Profissional "{nome}" atualizada.', 'success')
        return redirect(url_for('admin.profissionais'))
    return render_template('admin/profissional_form.html', profissional=profissional, form=None, servicos=servicos, servicos_selecionados=vinculadas_atual, empresa=EMPRESA)


@admin.route('/profissionais/<int:id>/ativar', methods=['POST'])
def profissional_alternar_ativo(id):
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    profissional = db.execute('SELECT * FROM profissionais WHERE id = ?', (id,)).fetchone()
    if profissional is None:
        flash('Profissional não encontrada.', 'error')
        return redirect(url_for('admin.profissionais'))
    novo_status = 0 if profissional['ativo'] else 1
    db.execute('UPDATE profissionais SET ativo = ? WHERE id = ?', (novo_status, id))
    db.commit()
    if novo_status:
        flash(f'Profissional "{profissional["nome"]}" reativada.', 'success')
    else:
        flash(f'Profissional "{profissional["nome"]}" inativada. Ela deixa de aparecer no agendamento.', 'info')
    return redirect(url_for('admin.profissionais'))


@admin.route('/profissionais/<int:id>/excluir', methods=['POST'])
def profissional_excluir(id):
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    profissional = db.execute('SELECT * FROM profissionais WHERE id = ?', (id,)).fetchone()
    if profissional is None:
        flash('Profissional não encontrada.', 'error')
        return redirect(url_for('admin.profissionais'))
    em_uso = db.execute('SELECT COUNT(*) AS n FROM agendamentos WHERE profissional_id = ?', (id,)).fetchone()['n']
    if em_uso:
        flash(f'Não é possível excluir "{profissional["nome"]}": existem {em_uso} agendamento(s) associado(s). Inative em vez de excluir.', 'error')
        return redirect(url_for('admin.profissionais'))
    db.execute('DELETE FROM profissionais_servicos WHERE profissional_id = ?', (id,))
    db.execute('DELETE FROM bloqueios_agenda WHERE profissional_id = ?', (id,))
    db.execute('DELETE FROM profissionais WHERE id = ?', (id,))
    db.commit()
    flash(f'Profissional "{profissional["nome"]}" excluída.', 'success')
    return redirect(url_for('admin.profissionais'))


@admin.route('/clientes')
def clientes():
    if not esta_logado():
        return redirect(url_for('admin.login'))
    busca = request.args.get('q', '').strip()
    db = get_db()
    sql = """SELECT c.id, c.nome, c.telefone,
                    COUNT(a.id) AS total_agendamentos,
                    SUM(CASE WHEN a.status = 'cancelado' THEN 1 ELSE 0 END) AS total_cancelados,
                    SUM(CASE WHEN a.status = 'confirmado' THEN 1 ELSE 0 END) AS total_confirmados,
                    MAX(a.data) AS ultimo_atendimento
             FROM clientes c
             LEFT JOIN agendamentos a ON a.cliente_id = c.id"""
    params = []
    if busca:
        sql += ' WHERE c.nome LIKE ? OR c.telefone LIKE ?'
        like = f'%{busca}%'
        params.extend([like, like])
    sql += ' GROUP BY c.id ORDER BY c.nome'
    lista = db.execute(sql, params).fetchall()
    return render_template('admin/clientes.html', clientes=lista, busca=busca, empresa=EMPRESA)


@admin.route('/clientes/<int:id>')
def cliente_detalhe(id):
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    cliente = db.execute('SELECT * FROM clientes WHERE id = ?', (id,)).fetchone()
    if cliente is None:
        flash('Cliente não encontrada.', 'error')
        return redirect(url_for('admin.clientes'))
    agendamentos = db.execute(
        """SELECT a.id, a.data, a.horario, a.status,
                  s.nome AS servico_nome, s.preco,
                  p.nome AS profissional_nome
           FROM agendamentos a
           JOIN servicos s ON s.id = a.servico_id
           JOIN profissionais p ON p.id = a.profissional_id
           WHERE a.cliente_id = ?
           ORDER BY a.data DESC, a.horario DESC""",
        (id,)
    ).fetchall()
    return render_template('admin/cliente_detalhe.html', cliente=cliente, agendamentos=agendamentos, empresa=EMPRESA)


app.register_blueprint(publico)

app.register_blueprint(admin)


@app.teardown_appcontext
def close_db(e=None):
    from flask import g
    db = g.pop('db', None)
    if db is not None:
        db.close()


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
