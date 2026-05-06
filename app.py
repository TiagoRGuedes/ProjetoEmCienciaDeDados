from flask import Flask, Blueprint, render_template, request, redirect, url_for, jsonify, session, flash
from database import init_db, get_db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'esmalteria-secret-key'

publico = Blueprint('publico', __name__)
admin = Blueprint('admin', __name__, url_prefix='/admin')

HORARIOS = ['09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00']

@publico.route('/')
def index():
    db = get_db()
    servicos = db.execute('SELECT * FROM servicos').fetchall()
    return render_template('index.html', servicos=servicos)

@publico.route('/agendar', methods=['GET'])
def agendar_get():
    db = get_db()
    servicos = db.execute('SELECT * FROM servicos').fetchall()
    return render_template('agendamento.html', servicos=servicos)

@publico.route('/agendar', methods=['POST'])
def agendar_post():
    db = get_db()
    nome = request.form['nome']
    telefone = request.form['telefone']
    email = request.form['email']
    servico_id = request.form['servico_id']
    data = request.form['data']
    horario = request.form['horario']

    conflito = db.execute(
        'SELECT id FROM agendamentos WHERE data = ? AND horario = ?',
        (data, horario)
    ).fetchone()

    if conflito:
        servicos = db.execute('SELECT * FROM servicos').fetchall()
        return render_template('agendamento.html', servicos=servicos, erro='Horário indisponível para a data selecionada.')

    cliente = db.execute(
        'SELECT id FROM clientes WHERE telefone = ?',
        (telefone,)
    ).fetchone()

    if cliente:
        cliente_id = cliente['id']
    else:
        cursor = db.execute(
            'INSERT INTO clientes (nome, telefone, email) VALUES (?, ?, ?)',
            (nome, telefone, email)
        )
        cliente_id = cursor.lastrowid

    db.execute(
        'INSERT INTO agendamentos (cliente_id, servico_id, data, horario, status) VALUES (?, ?, ?, ?, ?)',
        (cliente_id, servico_id, data, horario, 'pendente')
    )
    db.commit()

    return redirect(url_for('publico.confirmacao'))

@publico.route('/confirmacao')
def confirmacao():
    return render_template('confirmacao.html')

@publico.route('/horarios-disponiveis')
def horarios_disponiveis():
    data = request.args.get('data')
    servico_id = request.args.get('servico_id')

    db = get_db()
    agendados = db.execute(
        'SELECT horario FROM agendamentos WHERE data = ? AND status != ?',
        (data, 'cancelado')
    ).fetchall()

    horarios_ocupados = {row['horario'] for row in agendados}
    disponiveis = [h for h in HORARIOS if h not in horarios_ocupados]

    return jsonify(disponiveis)

ADMIN_USUARIO = 'admin'
ADMIN_SENHA = 'esmalteria123'

@admin.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        if usuario == ADMIN_USUARIO and senha == ADMIN_SENHA:
            session['logado'] = True
            return redirect(url_for('admin.dashboard'))
        return render_template('admin/login.html', erro='Usuário ou senha inválidos.')
    return render_template('admin/login.html')

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
    return render_template(
        'admin/dashboard.html',
        agendamentos=agendamentos,
        filtro_status=filtro_status,
        filtro_data=filtro_data,
    )

@admin.route('/agendamento/<int:id>/status', methods=['POST'])
def atualizar_status(id):
    if not session.get('logado'):
        return redirect(url_for('admin.login'))
    novo_status = request.form['novo_status']
    db = get_db()
    db.execute('UPDATE agendamentos SET status = ? WHERE id = ?', (novo_status, id))
    db.commit()
    return redirect(url_for('admin.dashboard'))

@admin.route('/servicos')
def servicos():
    if not session.get('logado'):
        return redirect(url_for('admin.login'))
    db = get_db()
    lista = db.execute('SELECT * FROM servicos ORDER BY nome').fetchall()
    return render_template('admin/servicos.html', servicos=lista)


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
            return render_template('admin/servico_form.html', servico=None, form=request.form, erro=erro)
        db = get_db()
        db.execute(
            'INSERT INTO servicos (nome, preco, duracao_min) VALUES (?, ?, ?)',
            (nome, preco, duracao),
        )
        db.commit()
        flash(f'Serviço "{nome}" criado com sucesso.', 'success')
        return redirect(url_for('admin.servicos'))
    return render_template('admin/servico_form.html', servico=None, form=None)


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
            return render_template('admin/servico_form.html', servico=servico, form=request.form, erro=erro)
        db.execute(
            'UPDATE servicos SET nome = ?, preco = ?, duracao_min = ? WHERE id = ?',
            (nome, preco, duracao, id),
        )
        db.commit()
        flash(f'Serviço "{nome}" atualizado.', 'success')
        return redirect(url_for('admin.servicos'))
    return render_template('admin/servico_form.html', servico=servico, form=None)


@admin.route('/servicos/<int:id>/excluir', methods=['POST'])
def servico_excluir(id):
    if not session.get('logado'):
        return redirect(url_for('admin.login'))
    db = get_db()
    servico = db.execute('SELECT * FROM servicos WHERE id = ?', (id,)).fetchone()
    if servico is None:
        flash('Serviço não encontrado.', 'error')
        return redirect(url_for('admin.servicos'))
    em_uso = db.execute(
        'SELECT COUNT(*) AS n FROM agendamentos WHERE servico_id = ?',
        (id,),
    ).fetchone()['n']
    if em_uso:
        flash(
            f'Não é possível excluir "{servico["nome"]}": existem {em_uso} agendamento(s) usando este serviço.',
            'error',
        )
        return redirect(url_for('admin.servicos'))
    db.execute('DELETE FROM servicos WHERE id = ?', (id,))
    db.commit()
    flash(f'Serviço "{servico["nome"]}" excluído.', 'success')
    return redirect(url_for('admin.servicos'))


app.register_blueprint(publico)
app.register_blueprint(admin)

@app.teardown_appcontext
def close_db(e=None):
    db = app.extensions.get('db') if hasattr(app, 'extensions') else None
    from flask import g
    db = g.pop('db', None)
    if db is not None:
        db.close()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
