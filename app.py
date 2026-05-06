from flask import Flask, Blueprint, render_template, request, redirect, url_for, jsonify, session  # Importa ferramentas do Flask para criar site, rotas, páginas, formulários, redirecionamentos, JSON e login.
from database import init_db, get_db  # Importa funções do arquivo database.py para iniciar o banco e abrir conexão com ele.

app = Flask(__name__)  # Cria a aplicação Flask, que será o servidor do site.
app.config['SECRET_KEY'] = 'esmalteria-secret-key'  # Define uma chave secreta usada para guardar dados de sessão, como login do admin.

publico = Blueprint('publico', __name__)  # Cria um grupo de rotas públicas, acessíveis pelas clientes do site.
admin = Blueprint('admin', __name__, url_prefix='/admin')  # Cria um grupo de rotas administrativas, todas começando com /admin.

EMPRESA = {  # Cria um dicionário com os dados fixos da empresa usados nas páginas HTML.
    'nome': 'Refúgio da Preta',  # Guarda o nome da empresa.
    'dona': 'Pamela Francisco',  # Guarda o nome da dona da empresa.
    'telefone': '99220-4706',  # Guarda o telefone de contato da empresa.
    'endereco': 'Rua Carapicuíba, 143 - BNH Grajaú',  # Guarda o endereço da empresa.
    'horarios': 'Terça a sábado, das 10h às 19h',  # Guarda o horário de funcionamento da empresa.
    'instagram_nome': '@refugiodapreta',  # Guarda o nome do perfil da empresa no Instagram.
    'instagram_url': 'https://www.instagram.com/refugiodapreta/',  # Guarda o link do Instagram da empresa.
    'foto_dona': 'pamela_francisco.png'  # Guarda o nome do arquivo da foto da dona dentro de static/img.
}  # Fecha o dicionário EMPRESA.

HORARIOS = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00']  # Lista os horários disponíveis para atendimento.


def buscar_servicos():  # Cria uma função auxiliar para buscar todos os serviços no banco.
    db = get_db()  # Abre uma conexão com o banco de dados.
    return db.execute('SELECT * FROM servicos ORDER BY id').fetchall()  # Retorna todos os serviços cadastrados, ordenados pelo ID.


@publico.route('/')  # Define a rota da página inicial, acessada pelo endereço principal do site.
def index():  # Cria a função que será executada quando a cliente acessar a página inicial.
    servicos = buscar_servicos()  # Busca os serviços no banco para mostrar na página inicial.
    galeria = [  # Cria a lista com as imagens da galeria do site.
        {'arquivo': 'trabalho1.png', 'titulo': 'Esmaltação marrom nude elegante'},  # Define a primeira foto e seu título.
        {'arquivo': 'trabalho2.png', 'titulo': 'Atendimento com cuidado e técnica'},  # Define a segunda foto e seu título.
        {'arquivo': 'trabalho3.png', 'titulo': 'Nude com brilho delicado'}  # Define a terceira foto e seu título.
    ]  # Fecha a lista de fotos da galeria.
    return render_template('index.html', servicos=servicos, empresa=EMPRESA, galeria=galeria)  # Abre o HTML inicial e envia serviços, dados da empresa e galeria.


@publico.route('/agendar', methods=['GET'])  # Define a rota que mostra o formulário de agendamento quando a cliente acessa a página.
def agendar_get():  # Cria a função que renderiza a tela de agendamento vazia.
    servicos = buscar_servicos()  # Busca os serviços para preencher o campo de escolha no formulário.
    dados = {'nome': '', 'telefone': '', 'email': '', 'servico_id': '', 'data': '', 'horario': ''}  # Cria dados vazios para evitar erro no HTML.
    return render_template('agendamento.html', servicos=servicos, empresa=EMPRESA, horarios=HORARIOS, dados=dados, erro=None)  # Abre o formulário de agendamento sem mensagem de erro.


@publico.route('/agendar', methods=['POST'])  # Define a rota que recebe os dados quando a cliente envia o formulário.
def agendar_post():  # Cria a função que valida e salva o agendamento no banco.
    db = get_db()  # Abre a conexão com o banco de dados.
    nome = request.form.get('nome', '').strip()  # Recebe o nome digitado no formulário e remove espaços extras.
    telefone = request.form.get('telefone', '').strip()  # Recebe o telefone digitado no formulário e remove espaços extras.
    email = request.form.get('email', '').strip().lower()  # Recebe o email digitado e transforma em minúsculo.
    servico_id = request.form.get('servico_id', '').strip()  # Recebe o ID do serviço escolhido.
    data = request.form.get('data', '').strip()  # Recebe a data escolhida para o atendimento.
    horario = request.form.get('horario', '').strip()  # Recebe o horário escolhido para o atendimento.
    dados = {'nome': nome, 'telefone': telefone, 'email': email, 'servico_id': servico_id, 'data': data, 'horario': horario}  # Guarda os dados para manter o formulário preenchido se houver erro.

    if len(nome) < 2:  # Verifica se o nome tem pelo menos 2 caracteres.
        return render_template('agendamento.html', servicos=buscar_servicos(), empresa=EMPRESA, horarios=HORARIOS, dados=dados, erro='Informe um nome válido.')  # Volta para o formulário mostrando erro de nome.
    if len(telefone) < 8:  # Verifica se o telefone tem um tamanho mínimo aceitável.
        return render_template('agendamento.html', servicos=buscar_servicos(), empresa=EMPRESA, horarios=HORARIOS, dados=dados, erro='Informe um telefone válido.')  # Volta para o formulário mostrando erro de telefone.
    if email != '' and ('@' not in email or '.' not in email):  # Verifica se o email preenchido possui formato básico válido.
        return render_template('agendamento.html', servicos=buscar_servicos(), empresa=EMPRESA, horarios=HORARIOS, dados=dados, erro='Informe um email válido.')  # Volta para o formulário mostrando erro de email.
    if servico_id == '':  # Verifica se a cliente selecionou um serviço.
        return render_template('agendamento.html', servicos=buscar_servicos(), empresa=EMPRESA, horarios=HORARIOS, dados=dados, erro='Selecione um serviço.')  # Volta para o formulário mostrando erro de serviço.
    if data == '':  # Verifica se a cliente escolheu uma data.
        return render_template('agendamento.html', servicos=buscar_servicos(), empresa=EMPRESA, horarios=HORARIOS, dados=dados, erro='Selecione uma data.')  # Volta para o formulário mostrando erro de data.
    if horario == '':  # Verifica se a cliente escolheu um horário.
        return render_template('agendamento.html', servicos=buscar_servicos(), empresa=EMPRESA, horarios=HORARIOS, dados=dados, erro='Selecione um horário.')  # Volta para o formulário mostrando erro de horário.

    conflito = db.execute('SELECT id FROM agendamentos WHERE data = ? AND horario = ? AND status != ?', (data, horario, 'cancelado')).fetchone()  # Procura agendamento ativo na mesma data e horário.
    if conflito:  # Verifica se a consulta encontrou algum agendamento no mesmo horário.
        return render_template('agendamento.html', servicos=buscar_servicos(), empresa=EMPRESA, horarios=HORARIOS, dados=dados, erro='Horário indisponível para a data selecionada.')  # Volta para o formulário mostrando que o horário está ocupado.

    cliente = db.execute('SELECT id FROM clientes WHERE telefone = ?', (telefone,)).fetchone()  # Procura se já existe cliente com o mesmo telefone.
    if cliente:  # Verifica se a cliente já existe no banco.
        cliente_id = cliente['id']  # Usa o ID da cliente que já estava cadastrada.
    else:  # Entra aqui se a cliente ainda não existe no banco.
        cursor = db.execute('INSERT INTO clientes (nome, telefone, email) VALUES (?, ?, ?)', (nome, telefone, email))  # Cadastra uma nova cliente no banco.
        cliente_id = cursor.lastrowid  # Pega o ID da nova cliente cadastrada.

    db.execute('INSERT INTO agendamentos (cliente_id, servico_id, data, horario, status) VALUES (?, ?, ?, ?, ?)', (cliente_id, servico_id, data, horario, 'pendente'))  # Salva o agendamento com status pendente.
    db.commit()  # Confirma e grava oficialmente as alterações no banco.
    return redirect(url_for('publico.confirmacao'))  # Redireciona a cliente para a página de confirmação.


@publico.route('/confirmacao')  # Define a rota da página de confirmação do agendamento.
def confirmacao():  # Cria a função que mostra a tela final após agendar.
    return render_template('confirmacao.html', empresa=EMPRESA)  # Abre o HTML de confirmação e envia os dados da empresa.


@publico.route('/horarios-disponiveis')  # Define uma rota auxiliar que devolve horários livres em formato JSON.
def horarios_disponiveis():  # Cria a função que calcula horários disponíveis para uma data.
    data = request.args.get('data')  # Recebe a data enviada pela URL.
    db = get_db()  # Abre uma conexão com o banco.
    agendados = db.execute('SELECT horario FROM agendamentos WHERE data = ? AND status != ?', (data, 'cancelado')).fetchall()  # Busca horários já ocupados nessa data.
    horarios_ocupados = {row['horario'] for row in agendados}  # Cria um conjunto com os horários ocupados.
    disponiveis = [h for h in HORARIOS if h not in horarios_ocupados]  # Monta uma lista apenas com horários que ainda estão livres.
    return jsonify(disponiveis)  # Retorna a lista de horários livres em formato JSON.


ADMIN_USUARIO = 'admin'  # Define o nome de usuário do painel administrativo.
ADMIN_SENHA = 'esmalteria123'  # Define a senha do painel administrativo.


@admin.route('/login', methods=['GET', 'POST'])  # Define a rota de login do admin, aceitando abrir a página e enviar formulário.
def login():  # Cria a função que controla o login administrativo.
    if request.method == 'POST':  # Verifica se o formulário de login foi enviado.
        usuario = request.form.get('usuario', '')  # Recebe o usuário digitado.
        senha = request.form.get('senha', '')  # Recebe a senha digitada.
        if usuario == ADMIN_USUARIO and senha == ADMIN_SENHA:  # Confere se usuário e senha estão corretos.
            session['logado'] = True  # Guarda na sessão que o administrador está logado.
            return redirect(url_for('admin.dashboard'))  # Envia o admin para o painel.
        return render_template('admin/login.html', erro='Usuário ou senha inválidos.', empresa=EMPRESA)  # Mostra erro se usuário ou senha estiverem errados.
    return render_template('admin/login.html', empresa=EMPRESA)  # Mostra a página de login quando o método for GET.


@admin.route('/logout')  # Define a rota para sair do painel administrativo.
def logout():  # Cria a função que faz logout.
    session.clear()  # Limpa todos os dados da sessão, removendo o login.
    return redirect(url_for('admin.login'))  # Volta para a página de login.


@admin.route('/dashboard')  # Define a rota do dashboard administrativo.
def dashboard():  # Cria a função que mostra os agendamentos para o admin.
    if not session.get('logado'):  # Verifica se o admin não está logado.
        return redirect(url_for('admin.login'))  # Envia para o login se não estiver logado.
    db = get_db()  # Abre a conexão com o banco.
    agendamentos = db.execute('''SELECT a.id, a.data, a.horario, a.status, c.nome AS cliente_nome, c.telefone, c.email, s.nome AS servico_nome, s.preco, s.duracao_min FROM agendamentos a JOIN clientes c ON c.id = a.cliente_id JOIN servicos s ON s.id = a.servico_id ORDER BY a.data, a.horario''').fetchall()  # Busca agendamentos juntando informações de cliente e serviço.
    return render_template('admin/dashboard.html', agendamentos=agendamentos, empresa=EMPRESA)  # Abre o dashboard enviando os agendamentos.


@admin.route('/agendamento/<int:id>/status', methods=['POST'])  # Define a rota que muda o status de um agendamento específico.
def atualizar_status(id):  # Cria a função que recebe o ID do agendamento pela URL.
    if not session.get('logado'):  # Verifica se o admin não está logado.
        return redirect(url_for('admin.login'))  # Envia para login se não estiver logado.
    novo_status = request.form.get('novo_status')  # Recebe o novo status enviado pelo formulário.
    db = get_db()  # Abre a conexão com o banco.
    db.execute('UPDATE agendamentos SET status = ? WHERE id = ?', (novo_status, id))  # Atualiza o status do agendamento no banco.
    db.commit()  # Salva oficialmente a alteração.
    return redirect(url_for('admin.dashboard'))  # Volta para o dashboard.


@admin.route('/servicos')  # Define a rota administrativa que lista os serviços.
def servicos():  # Cria a função que mostra os serviços para o admin.
    if not session.get('logado'):  # Verifica se o admin não está logado.
        return redirect(url_for('admin.login'))  # Envia para login se não estiver logado.
    lista = buscar_servicos()  # Busca todos os serviços cadastrados no banco.
    return render_template('admin/servicos.html', servicos=lista, empresa=EMPRESA)  # Abre a página de serviços do admin.


app.register_blueprint(publico)  # Registra o grupo de rotas públicas na aplicação Flask.
app.register_blueprint(admin)  # Registra o grupo de rotas administrativas na aplicação Flask.


@app.teardown_appcontext  # Define uma função que será executada ao final de cada requisição.
def close_db(e=None):  # Cria a função responsável por fechar o banco.
    from flask import g  # Importa o objeto g do Flask, onde a conexão fica guardada temporariamente.
    db = g.pop('db', None)  # Remove a conexão do g, se ela existir.
    if db is not None:  # Verifica se realmente existe uma conexão aberta.
        db.close()  # Fecha a conexão com o banco.


if __name__ == '__main__':  # Garante que o código abaixo só rode quando executarmos python app.py diretamente.
    init_db()  # Cria as tabelas e insere os serviços iniciais se ainda não existirem.
    app.run(debug=True)  # Inicia o servidor Flask em modo debug.
