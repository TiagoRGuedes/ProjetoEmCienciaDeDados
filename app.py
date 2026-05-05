from flask import Flask, Blueprint, render_template, request, redirect, url_for, jsonify, session
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
    db = get_db()
    agendamentos = db.execute(
        '''SELECT a.id, a.data, a.horario, a.status,
                  c.nome AS cliente_nome, c.telefone, c.email,
                  s.nome AS servico_nome, s.preco, s.duracao_min
           FROM agendamentos a
           JOIN clientes c ON c.id = a.cliente_id
           JOIN servicos s ON s.id = a.servico_id
           ORDER BY a.data, a.horario'''
    ).fetchall()
    return render_template('admin/dashboard.html', agendamentos=agendamentos)

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
    lista = db.execute('SELECT * FROM servicos').fetchall()
    return render_template('admin/servicos.html', servicos=lista)

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
