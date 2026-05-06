from flask import Flask, Blueprint, render_template, request, redirect, url_for, jsonify, session, flash
from database import init_db, get_db

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


def buscar_servicos():
    db = get_db()
    return db.execute('SELECT * FROM servicos ORDER BY id').fetchall()


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
    dados = {'nome': '', 'telefone': '', 'email': '', 'servico_id': '', 'data': '', 'horario': ''}
    return render_template('agendamento.html', servicos=servicos, empresa=EMPRESA, horarios=HORARIOS, horarios_ocupados=[], dados=dados, erro=None)


@publico.route('/agendar', methods=['POST'])
def agendar_post():
    db = get_db()
    nome = request.form.get('nome', '').strip()
    telefone = request.form.get('telefone', '').strip()
    email = request.form.get('email', '').strip().lower()
    servico_id = request.form.get('servico_id', '').strip()
    data = request.form.get('data', '').strip()
    horario = request.form.get('horario', '').strip()
    dados = {'nome': nome, 'telefone': telefone, 'email': email, 'servico_id': servico_id, 'data': data, 'horario': horario}

    def erro_form(msg):
        # cancelados não bloqueiam o horário — podem ser reagendados
        agendados = db.execute('SELECT horario FROM agendamentos WHERE data = ? AND status != ?', (data, 'cancelado')).fetchall()
        horarios_ocupados = {row['horario'] for row in agendados}
        return render_template('agendamento.html', servicos=buscar_servicos(), empresa=EMPRESA, horarios=HORARIOS, horarios_ocupados=horarios_ocupados, dados=dados, erro=msg)

    if len(nome) < 2:
        return erro_form('Informe um nome válido.')
    if len(telefone) < 8:
        return erro_form('Informe um telefone válido.')
    if email != '' and ('@' not in email or '.' not in email):
        return erro_form('Informe um email válido.')
    if servico_id == '':
        return erro_form('Selecione um serviço.')
    if data == '':
        return erro_form('Selecione uma data.')
    if horario == '':
        return erro_form('Selecione um horário.')

    conflito = db.execute('SELECT id FROM agendamentos WHERE data = ? AND horario = ? AND status != ?', (data, horario, 'cancelado')).fetchone()
    if conflito:
        return erro_form('Horário indisponível para a data selecionada.')

    # reutiliza cliente existente pelo telefone em vez de criar duplicata
    cliente = db.execute('SELECT id FROM clientes WHERE telefone = ?', (telefone,)).fetchone()
    if cliente:
        cliente_id = cliente['id']
    else:
        cursor = db.execute('INSERT INTO clientes (nome, telefone, email) VALUES (?, ?, ?)', (nome, telefone, email))
        cliente_id = cursor.lastrowid

    db.execute('INSERT INTO agendamentos (cliente_id, servico_id, data, horario, status) VALUES (?, ?, ?, ?, ?)', (cliente_id, servico_id, data, horario, 'pendente'))
    db.commit()
    return redirect(url_for('publico.confirmacao'))


@publico.route('/confirmacao')
def confirmacao():
    return render_template('confirmacao.html', empresa=EMPRESA)


@publico.route('/horarios-disponiveis')
def horarios_disponiveis():
    data = request.args.get('data')
    db = get_db()
    agendados = db.execute('SELECT horario FROM agendamentos WHERE data = ? AND status != ?', (data, 'cancelado')).fetchall()
    horarios_ocupados = {row['horario'] for row in agendados}
    disponiveis = [h for h in HORARIOS if h not in horarios_ocupados]
    return jsonify(disponiveis)


ADMIN_USUARIO = 'admin'
ADMIN_SENHA = 'esmalteria123'


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
    if not session.get('logado'):
        return redirect(url_for('admin.login'))
    filtro_status = request.args.get('status', '').strip()
    filtro_data = request.args.get('data', '').strip()
    sql = '''SELECT a.id, a.data, a.horario, a.status,
                    c.nome AS cliente_nome, c.telefone, c.email,
                    s.nome AS servico_nome, s.preco, s.duracao_min
             FROM agendamentos a
             JOIN clientes c ON c.id = a.cliente_id
             JOIN servicos s ON s.id = a.servico_id'''
    where = []
    params = []
    if filtro_status in ('pendente', 'confirmado', 'cancelado'):
        where.append('a.status = ?')
        params.append(filtro_status)
    if filtro_data:
        where.append('a.data = ?')
        params.append(filtro_data)
    if where:
        sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY a.data, a.horario'
    db = get_db()
    agendamentos = db.execute(sql, params).fetchall()
    return render_template('admin/dashboard.html', agendamentos=agendamentos, filtro_status=filtro_status, filtro_data=filtro_data, empresa=EMPRESA)


@admin.route('/agendamento/<int:id>/status', methods=['POST'])
def atualizar_status(id):
    if not session.get('logado'):
        return redirect(url_for('admin.login'))
    novo_status = request.form.get('novo_status')
    db = get_db()
    db.execute('UPDATE agendamentos SET status = ? WHERE id = ?', (novo_status, id))
    db.commit()
    return redirect(url_for('admin.dashboard'))


@admin.route('/servicos')
def servicos():
    if not session.get('logado'):
        return redirect(url_for('admin.login'))
    lista = buscar_servicos()
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
    if not session.get('logado'):
        return redirect(url_for('admin.login'))
    if request.method == 'POST':
        nome, preco, duracao, erro = _parse_servico_form()
        if erro:
            return render_template('admin/servico_form.html', servico=None, form=request.form, erro=erro, empresa=EMPRESA)
        db = get_db()
        db.execute('INSERT INTO servicos (nome, preco, duracao_min) VALUES (?, ?, ?)', (nome, preco, duracao))
        db.commit()
        flash(f'Serviço "{nome}" criado com sucesso.', 'success')
        return redirect(url_for('admin.servicos'))
    return render_template('admin/servico_form.html', servico=None, form=None, empresa=EMPRESA)


@admin.route('/servicos/<int:id>/editar', methods=['GET', 'POST'])
def servico_editar(id):
    if not session.get('logado'):
        return redirect(url_for('admin.login'))
    db = get_db()
    servico = db.execute('SELECT * FROM servicos WHERE id = ?', (id,)).fetchone()
    if servico is None:
        flash('Serviço não encontrado.', 'error')
        return redirect(url_for('admin.servicos'))
    if request.method == 'POST':
        nome, preco, duracao, erro = _parse_servico_form()
        if erro:
            return render_template('admin/servico_form.html', servico=servico, form=request.form, erro=erro, empresa=EMPRESA)
        db.execute('UPDATE servicos SET nome = ?, preco = ?, duracao_min = ? WHERE id = ?', (nome, preco, duracao, id))
        db.commit()
        flash(f'Serviço "{nome}" atualizado.', 'success')
        return redirect(url_for('admin.servicos'))
    return render_template('admin/servico_form.html', servico=servico, form=None, empresa=EMPRESA)


@admin.route('/servicos/<int:id>/excluir', methods=['POST'])
def servico_excluir(id):
    if not session.get('logado'):
        return redirect(url_for('admin.login'))
    db = get_db()
    servico = db.execute('SELECT * FROM servicos WHERE id = ?', (id,)).fetchone()
    if servico is None:
        flash('Serviço não encontrado.', 'error')
        return redirect(url_for('admin.servicos'))
    # bloqueia exclusão se houver agendamentos vinculados, para não criar referências órfãs
    em_uso = db.execute('SELECT COUNT(*) AS n FROM agendamentos WHERE servico_id = ?', (id,)).fetchone()['n']
    if em_uso:
        flash(f'Não é possível excluir "{servico["nome"]}": existem {em_uso} agendamento(s) usando este serviço.', 'error')
        return redirect(url_for('admin.servicos'))
    db.execute('DELETE FROM servicos WHERE id = ?', (id,))
    db.commit()
    flash(f'Serviço "{servico["nome"]}" excluído.', 'success')
    return redirect(url_for('admin.servicos'))


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
