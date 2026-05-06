from flask import Flask, Blueprint, render_template, request, redirect, url_for, jsonify, session, flash  # Importa ferramentas do Flask para criar rotas, páginas, formulários, redirecionamentos, JSON, login e mensagens.
from database import init_db, get_db  # Importa as funções do arquivo database.py para iniciar o banco e abrir conexão.

app = Flask(__name__)  # Cria a aplicação Flask, que funciona como o servidor do site.
app.config['SECRET_KEY'] = 'esmalteria-secret-key'  # Define uma chave secreta usada para salvar dados de sessão, como login do admin.

publico = Blueprint('publico', __name__)  # Cria um grupo de rotas públicas, acessíveis pelas clientes do site.
admin = Blueprint('admin', __name__, url_prefix='/admin')  # Cria um grupo de rotas administrativas, sempre começando por /admin.

EMPRESA = {  # Cria um dicionário com os dados fixos da empresa para usar nos templates HTML.
    'nome': 'Refúgio da Preta',  # Guarda o nome da empresa que aparece no site.
    'dona': 'Pamela Francisco',  # Guarda o nome da dona/profissional responsável.
    'telefone': '99220-4706',  # Guarda o telefone informado para contato e confirmação.
    'endereco': 'Rua Carapicuíba, 143 - BNH Grajaú',  # Guarda o endereço da empresa.
    'horarios': 'Terça a sábado, das 10h às 19h',  # Guarda o horário de funcionamento.
    'instagram_nome': '@refugiodapreta',  # Guarda o nome do perfil do Instagram.
    'instagram_url': 'https://www.instagram.com/refugiodapreta/',  # Guarda o link clicável do Instagram.
    'foto_dona': 'pamela_francisco.png',  # Guarda o nome da imagem da Pamela dentro da pasta static/img.
    'slogan': 'Beleza, cuidado e acolhimento.'  # Guarda uma frase curta para apresentar a identidade da marca.
}  # Fecha o dicionário EMPRESA.

HORARIOS = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00']  # Define os horários disponíveis para agendamento.


def buscar_servicos():  # Cria uma função auxiliar para buscar os serviços no banco.
    db = get_db()  # Abre uma conexão com o banco de dados.
    return db.execute('SELECT * FROM servicos ORDER BY id').fetchall()  # Retorna todos os serviços cadastrados, ordenados pelo id.


@publico.route('/')  # Define a rota da página inicial do site.
def index():  # Cria a função que responde quando a cliente acessa a página inicial.
    servicos = buscar_servicos()  # Busca os serviços para mostrar na página inicial.
    galeria = [  # Cria uma lista com as imagens da galeria pública.
        {'arquivo': 'trabalho1.png', 'titulo': 'Esmaltação marrom nude elegante'},  # Define a primeira imagem da galeria.
        {'arquivo': 'trabalho2.png', 'titulo': 'Atendimento com cuidado e técnica'},  # Define a segunda imagem da galeria.
        {'arquivo': 'trabalho3.png', 'titulo': 'Nude com brilho delicado'}  # Define a terceira imagem da galeria.
    ]  # Fecha a lista da galeria.
    return render_template('index.html', servicos=servicos, empresa=EMPRESA, galeria=galeria)  # Abre o template index.html e envia serviços, empresa e fotos.


@publico.route('/agendar', methods=['GET'])  # Define a rota GET de agendamento, usada para abrir o formulário.
def agendar_get():  # Cria a função que mostra a página de agendamento vazia.
    servicos = buscar_servicos()  # Busca os serviços cadastrados para preencher o select.
    dados = {'nome': '', 'telefone': '', 'email': '', 'servico_id': '', 'data': '', 'horario': ''}  # Cria dados vazios para evitar erro no HTML.
    return render_template('agendamento.html', servicos=servicos, empresa=EMPRESA, horarios=HORARIOS, horarios_ocupados=[], dados=dados, erro=None)  # Abre o formulário sem erro e sem horários ocupados.


@publico.route('/agendar', methods=['POST'])  # Define a rota POST de agendamento, usada quando o formulário é enviado.
def agendar_post():  # Cria a função que processa os dados enviados pela cliente.
    db = get_db()  # Abre uma conexão com o banco de dados.
    nome = request.form.get('nome', '').strip()  # Recebe o nome digitado e remove espaços extras.
    telefone = request.form.get('telefone', '').strip()  # Recebe o telefone digitado e remove espaços extras.
    email = request.form.get('email', '').strip().lower()  # Recebe o email, remove espaços e coloca em minúsculo.
    servico_id = request.form.get('servico_id', '').strip()  # Recebe o id do serviço escolhido.
    data = request.form.get('data', '').strip()  # Recebe a data escolhida.
    horario = request.form.get('horario', '').strip()  # Recebe o horário escolhido.
    dados = {'nome': nome, 'telefone': telefone, 'email': email, 'servico_id': servico_id, 'data': data, 'horario': horario}  # Guarda os dados para manter o formulário preenchido se houver erro.

    def erro_form(msg):  # Cria uma função interna para recarregar o formulário mostrando uma mensagem de erro.
        agendados = db.execute('SELECT horario FROM agendamentos WHERE data = ? AND status != ?', (data, 'cancelado')).fetchall()  # Busca horários ocupados nessa data, ignorando cancelados.
        horarios_ocupados = {row['horario'] for row in agendados}  # Transforma os horários ocupados em um conjunto para facilitar a verificação.
        return render_template('agendamento.html', servicos=buscar_servicos(), empresa=EMPRESA, horarios=HORARIOS, horarios_ocupados=horarios_ocupados, dados=dados, erro=msg)  # Retorna o formulário com a mensagem de erro.

    if len(nome) < 2:  # Verifica se o nome tem pelo menos 2 caracteres.
        return erro_form('Informe um nome válido.')  # Retorna erro se o nome estiver inválido.
    if len(telefone) < 8:  # Verifica se o telefone tem tamanho mínimo aceitável.
        return erro_form('Informe um telefone válido.')  # Retorna erro se o telefone estiver inválido.
    if email != '' and ('@' not in email or '.' not in email):  # Verifica se o email preenchido tem formato básico com arroba e ponto.
        return erro_form('Informe um email válido.')  # Retorna erro se o email estiver inválido.
    if servico_id == '':  # Verifica se a cliente escolheu algum serviço.
        return erro_form('Selecione um serviço.')  # Retorna erro se nenhum serviço foi selecionado.
    if data == '':  # Verifica se a data foi informada.
        return erro_form('Selecione uma data.')  # Retorna erro se a data estiver vazia.
    if horario == '':  # Verifica se o horário foi escolhido.
        return erro_form('Selecione um horário.')  # Retorna erro se o horário estiver vazio.

    conflito = db.execute('SELECT id FROM agendamentos WHERE data = ? AND horario = ? AND status != ?', (data, horario, 'cancelado')).fetchone()  # Procura se já existe agendamento no mesmo dia e horário.
    if conflito:  # Verifica se encontrou conflito no banco.
        return erro_form('Horário indisponível para a data selecionada.')  # Retorna erro se o horário já estiver ocupado.

    cliente = db.execute('SELECT id FROM clientes WHERE telefone = ?', (telefone,)).fetchone()  # Procura se já existe cliente com esse telefone.
    if cliente:  # Verifica se o cliente já existe.
        cliente_id = cliente['id']  # Usa o id do cliente já cadastrado.
    else:  # Executa caso o cliente ainda não exista.
        cursor = db.execute('INSERT INTO clientes (nome, telefone, email) VALUES (?, ?, ?)', (nome, telefone, email))  # Cadastra um novo cliente no banco.
        cliente_id = cursor.lastrowid  # Pega o id do cliente recém-cadastrado.

    db.execute('INSERT INTO agendamentos (cliente_id, servico_id, data, horario, status) VALUES (?, ?, ?, ?, ?)', (cliente_id, servico_id, data, horario, 'pendente'))  # Cadastra o agendamento como pendente.
    db.commit()  # Salva oficialmente as alterações no banco.
    return redirect(url_for('publico.confirmacao'))  # Redireciona para a página de confirmação.


@publico.route('/confirmacao')  # Define a rota da página de confirmação.
def confirmacao():  # Cria a função que mostra a confirmação do agendamento.
    return render_template('confirmacao.html', empresa=EMPRESA)  # Abre o template de confirmação e envia os dados da empresa.


@publico.route('/horarios-disponiveis')  # Define uma rota auxiliar que devolve horários livres em JSON.
def horarios_disponiveis():  # Cria a função que consulta horários disponíveis.
    data = request.args.get('data')  # Recebe a data enviada pela URL.
    db = get_db()  # Abre uma conexão com o banco.
    agendados = db.execute('SELECT horario FROM agendamentos WHERE data = ? AND status != ?', (data, 'cancelado')).fetchall()  # Busca horários já agendados para a data.
    horarios_ocupados = {row['horario'] for row in agendados}  # Cria um conjunto com horários ocupados.
    disponiveis = [h for h in HORARIOS if h not in horarios_ocupados]  # Monta a lista de horários ainda livres.
    return jsonify(disponiveis)  # Retorna os horários livres no formato JSON.


ADMIN_USUARIO = 'admin'  # Define o usuário de acesso administrativo.
ADMIN_SENHA = 'esmalteria123'  # Define a senha de acesso administrativo.


@admin.route('/login', methods=['GET', 'POST'])  # Define a rota de login do admin, aceitando abrir página e enviar formulário.
def login():  # Cria a função de login administrativo.
    if request.method == 'POST':  # Verifica se o formulário de login foi enviado.
        usuario = request.form.get('usuario', '')  # Recebe o usuário digitado.
        senha = request.form.get('senha', '')  # Recebe a senha digitada.
        if usuario == ADMIN_USUARIO and senha == ADMIN_SENHA:  # Confere se usuário e senha estão corretos.
            session['logado'] = True  # Salva na sessão que o admin está logado.
            return redirect(url_for('admin.dashboard'))  # Redireciona para o painel administrativo.
        return render_template('admin/login.html', erro='Usuário ou senha inválidos.', empresa=EMPRESA)  # Mostra erro se o login estiver incorreto.
    return render_template('admin/login.html', empresa=EMPRESA)  # Abre a tela de login quando o acesso é GET.


@admin.route('/logout')  # Define a rota para sair da área administrativa.
def logout():  # Cria a função de logout.
    session.clear()  # Limpa todos os dados da sessão.
    return redirect(url_for('admin.login'))  # Redireciona para a página de login.


@admin.route('/dashboard')  # Define a rota do painel de agendamentos.
def dashboard():  # Cria a função que mostra o dashboard.
    if not session.get('logado'):  # Verifica se o usuário não está logado.
        return redirect(url_for('admin.login'))  # Redireciona para login se não estiver autenticado.
    filtro_status = request.args.get('status', '').strip()  # Recebe o filtro de status vindo da URL.
    filtro_data = request.args.get('data', '').strip()  # Recebe o filtro de data vindo da URL.
    sql = '''SELECT a.id, a.data, a.horario, a.status,
                    c.nome AS cliente_nome, c.telefone, c.email,
                    s.nome AS servico_nome, s.preco, s.duracao_min
             FROM agendamentos a
             JOIN clientes c ON c.id = a.cliente_id
             JOIN servicos s ON s.id = a.servico_id'''  # Monta a consulta SQL para juntar agendamento, cliente e serviço.
    where = []  # Cria uma lista para guardar filtros SQL.
    params = []  # Cria uma lista para guardar os valores dos filtros.
    if filtro_status in ('pendente', 'confirmado', 'cancelado'):  # Verifica se o status informado é permitido.
        where.append('a.status = ?')  # Adiciona o filtro de status no SQL.
        params.append(filtro_status)  # Adiciona o valor do status nos parâmetros.
    if filtro_data:  # Verifica se uma data foi informada.
        where.append('a.data = ?')  # Adiciona o filtro de data no SQL.
        params.append(filtro_data)  # Adiciona o valor da data nos parâmetros.
    if where:  # Verifica se existe algum filtro para aplicar.
        sql += ' WHERE ' + ' AND '.join(where)  # Junta os filtros na consulta SQL.
    sql += ' ORDER BY a.data, a.horario'  # Ordena os resultados por data e horário.
    db = get_db()  # Abre uma conexão com o banco.
    agendamentos = db.execute(sql, params).fetchall()  # Executa a consulta e busca os agendamentos.
    return render_template('admin/dashboard.html', agendamentos=agendamentos, filtro_status=filtro_status, filtro_data=filtro_data, empresa=EMPRESA)  # Abre o dashboard com os agendamentos e filtros.


@admin.route('/agendamento/<int:id>/status', methods=['POST'])  # Define a rota que altera o status de um agendamento.
def atualizar_status(id):  # Cria a função que atualiza o status.
    if not session.get('logado'):  # Verifica se o admin não está logado.
        return redirect(url_for('admin.login'))  # Redireciona para login se necessário.
    novo_status = request.form.get('novo_status')  # Recebe o novo status enviado pelo formulário.
    db = get_db()  # Abre uma conexão com o banco.
    db.execute('UPDATE agendamentos SET status = ? WHERE id = ?', (novo_status, id))  # Atualiza o status do agendamento no banco.
    db.commit()  # Salva a alteração no banco.
    return redirect(url_for('admin.dashboard'))  # Volta para o dashboard.


@admin.route('/servicos')  # Define a rota administrativa que lista os serviços.
def servicos():  # Cria a função que mostra os serviços no admin.
    if not session.get('logado'):  # Verifica se o admin não está logado.
        return redirect(url_for('admin.login'))  # Redireciona para login caso não esteja logado.
    lista = buscar_servicos()  # Busca os serviços cadastrados.
    return render_template('admin/servicos.html', servicos=lista, empresa=EMPRESA)  # Abre o template de serviços.


def _parse_servico_form():  # Cria uma função auxiliar para ler e validar formulário de serviço.
    nome = request.form.get('nome', '').strip()  # Recebe o nome do serviço.
    preco_raw = request.form.get('preco', '').strip().replace(',', '.')  # Recebe o preço e troca vírgula por ponto.
    duracao_raw = request.form.get('duracao_min', '').strip()  # Recebe a duração em minutos.
    erro = None  # Cria uma variável para guardar erro, começando sem erro.
    preco = duracao = None  # Cria as variáveis preço e duração começando vazias.
    try:  # Inicia tentativa de converter os valores para número.
        preco = float(preco_raw)  # Converte o preço para número decimal.
        duracao = int(duracao_raw)  # Converte a duração para número inteiro.
    except ValueError:  # Captura erro caso preço ou duração não sejam números.
        erro = 'Preço e duração precisam ser numéricos.'  # Define uma mensagem de erro.
    if not erro:  # Continua a validação se ainda não existe erro.
        if not nome:  # Verifica se o nome está vazio.
            erro = 'Nome é obrigatório.'  # Define erro de nome obrigatório.
        elif preco < 0:  # Verifica se o preço é negativo.
            erro = 'Preço não pode ser negativo.'  # Define erro de preço negativo.
        elif duracao <= 0:  # Verifica se a duração é zero ou negativa.
            erro = 'Duração deve ser maior que zero.'  # Define erro de duração inválida.
    return nome, preco, duracao, erro  # Retorna os dados tratados e a mensagem de erro, se existir.


@admin.route('/servicos/novo', methods=['GET', 'POST'])  # Define a rota para criar novo serviço.
def servico_novo():  # Cria a função de cadastro de serviço.
    if not session.get('logado'):  # Verifica se o admin está logado.
        return redirect(url_for('admin.login'))  # Redireciona para login se não estiver logado.
    if request.method == 'POST':  # Verifica se o formulário foi enviado.
        nome, preco, duracao, erro = _parse_servico_form()  # Lê e valida os dados do formulário.
        if erro:  # Verifica se houve erro na validação.
            return render_template('admin/servico_form.html', servico=None, form=request.form, erro=erro, empresa=EMPRESA)  # Reabre o formulário com erro.
        db = get_db()  # Abre conexão com o banco.
        db.execute('INSERT INTO servicos (nome, preco, duracao_min) VALUES (?, ?, ?)', (nome, preco, duracao))  # Insere o novo serviço.
        db.commit()  # Salva o novo serviço no banco.
        flash(f'Serviço "{nome}" criado com sucesso.', 'success')  # Mostra mensagem de sucesso.
        return redirect(url_for('admin.servicos'))  # Volta para a lista de serviços.
    return render_template('admin/servico_form.html', servico=None, form=None, empresa=EMPRESA)  # Abre formulário vazio quando a requisição é GET.


@admin.route('/servicos/<int:id>/editar', methods=['GET', 'POST'])  # Define a rota para editar serviço existente.
def servico_editar(id):  # Cria a função de edição de serviço.
    if not session.get('logado'):  # Verifica se o admin está logado.
        return redirect(url_for('admin.login'))  # Redireciona para login se não estiver logado.
    db = get_db()  # Abre conexão com o banco.
    servico = db.execute('SELECT * FROM servicos WHERE id = ?', (id,)).fetchone()  # Busca o serviço pelo id.
    if servico is None:  # Verifica se o serviço não foi encontrado.
        flash('Serviço não encontrado.', 'error')  # Mostra mensagem de erro.
        return redirect(url_for('admin.servicos'))  # Volta para a lista de serviços.
    if request.method == 'POST':  # Verifica se o formulário foi enviado.
        nome, preco, duracao, erro = _parse_servico_form()  # Lê e valida os dados enviados.
        if erro:  # Verifica se houve erro na validação.
            return render_template('admin/servico_form.html', servico=servico, form=request.form, erro=erro, empresa=EMPRESA)  # Reabre o formulário com erro.
        db.execute('UPDATE servicos SET nome = ?, preco = ?, duracao_min = ? WHERE id = ?', (nome, preco, duracao, id))  # Atualiza o serviço no banco.
        db.commit()  # Salva a atualização.
        flash(f'Serviço "{nome}" atualizado.', 'success')  # Mostra mensagem de sucesso.
        return redirect(url_for('admin.servicos'))  # Volta para a lista de serviços.
    return render_template('admin/servico_form.html', servico=servico, form=None, empresa=EMPRESA)  # Abre o formulário preenchido quando a requisição é GET.


@admin.route('/servicos/<int:id>/excluir', methods=['POST'])  # Define a rota para excluir um serviço.
def servico_excluir(id):  # Cria a função de exclusão de serviço.
    if not session.get('logado'):  # Verifica se o admin está logado.
        return redirect(url_for('admin.login'))  # Redireciona para login se não estiver logado.
    db = get_db()  # Abre conexão com o banco.
    servico = db.execute('SELECT * FROM servicos WHERE id = ?', (id,)).fetchone()  # Busca o serviço pelo id.
    if servico is None:  # Verifica se o serviço não existe.
        flash('Serviço não encontrado.', 'error')  # Mostra mensagem de erro.
        return redirect(url_for('admin.servicos'))  # Volta para a lista de serviços.
    em_uso = db.execute('SELECT COUNT(*) AS n FROM agendamentos WHERE servico_id = ?', (id,)).fetchone()['n']  # Conta agendamentos que usam esse serviço.
    if em_uso:  # Verifica se o serviço está sendo usado em agendamentos.
        flash(f'Não é possível excluir "{servico["nome"]}": existem {em_uso} agendamento(s) usando este serviço.', 'error')  # Mostra erro impedindo exclusão.
        return redirect(url_for('admin.servicos'))  # Volta para a lista de serviços.
    db.execute('DELETE FROM servicos WHERE id = ?', (id,))  # Exclui o serviço do banco.
    db.commit()  # Salva a exclusão.
    flash(f'Serviço "{servico["nome"]}" excluído.', 'success')  # Mostra mensagem de sucesso.
    return redirect(url_for('admin.servicos'))  # Volta para a lista de serviços.


app.register_blueprint(publico)  # Registra as rotas públicas na aplicação Flask.
app.register_blueprint(admin)  # Registra as rotas administrativas na aplicação Flask.


@app.teardown_appcontext  # Define uma função que roda ao final de cada requisição.
def close_db(e=None):  # Cria a função responsável por fechar a conexão com o banco.
    from flask import g  # Importa g para acessar a conexão guardada durante a requisição.
    db = g.pop('db', None)  # Remove a conexão do objeto g, se ela existir.
    if db is not None:  # Verifica se havia conexão aberta.
        db.close()  # Fecha a conexão com o banco.


if __name__ == '__main__':  # Garante que o servidor só rode quando este arquivo for executado diretamente.
    init_db()  # Cria as tabelas e serviços iniciais se ainda não existirem.
    app.run(debug=True)  # Inicia o servidor Flask em modo debug para facilitar testes.
from flask import Flask, Blueprint, render_template, request, redirect, url_for, jsonify, session, flash  # Importa ferramentas do Flask para criar rotas, páginas, formulários, redirecionamentos, JSON, login e mensagens.
from database import init_db, get_db  # Importa as funções do arquivo database.py para iniciar o banco e abrir conexão.

app = Flask(__name__)  # Cria a aplicação Flask, que funciona como o servidor do site.
app.config['SECRET_KEY'] = 'esmalteria-secret-key'  # Define uma chave secreta usada para salvar dados de sessão, como login do admin.

publico = Blueprint('publico', __name__)  # Cria um grupo de rotas públicas, acessíveis pelas clientes do site.
admin = Blueprint('admin', __name__, url_prefix='/admin')  # Cria um grupo de rotas administrativas, sempre começando por /admin.

EMPRESA = {  # Cria um dicionário com os dados fixos da empresa para usar nos templates HTML.
    'nome': 'Refúgio da Preta',  # Guarda o nome da empresa que aparece no site.
    'dona': 'Pamela Francisco',  # Guarda o nome da dona/profissional responsável.
    'telefone': '99220-4706',  # Guarda o telefone informado para contato e confirmação.
    'endereco': 'Rua Carapicuíba, 143 - BNH Grajaú',  # Guarda o endereço da empresa.
    'horarios': 'Terça a sábado, das 10h às 19h',  # Guarda o horário de funcionamento.
    'instagram_nome': '@refugiodapreta',  # Guarda o nome do perfil do Instagram.
    'instagram_url': 'https://www.instagram.com/refugiodapreta/',  # Guarda o link clicável do Instagram.
    'foto_dona': 'pamela_francisco.png',  # Guarda o nome da imagem da Pamela dentro da pasta static/img.
    'slogan': 'Beleza, cuidado e acolhimento.'  # Guarda uma frase curta para apresentar a identidade da marca.
}  # Fecha o dicionário EMPRESA.

HORARIOS = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00']  # Define os horários disponíveis para agendamento.


def buscar_servicos():  # Cria uma função auxiliar para buscar os serviços no banco.
    db = get_db()  # Abre uma conexão com o banco de dados.
    return db.execute('SELECT * FROM servicos ORDER BY id').fetchall()  # Retorna todos os serviços cadastrados, ordenados pelo id.


@publico.route('/')  # Define a rota da página inicial do site.
def index():  # Cria a função que responde quando a cliente acessa a página inicial.
    servicos = buscar_servicos()  # Busca os serviços para mostrar na página inicial.
    galeria = [  # Cria uma lista com as imagens da galeria pública.
        {'arquivo': 'trabalho1.png', 'titulo': 'Esmaltação marrom nude elegante'},  # Define a primeira imagem da galeria.
        {'arquivo': 'trabalho2.png', 'titulo': 'Atendimento com cuidado e técnica'},  # Define a segunda imagem da galeria.
        {'arquivo': 'trabalho3.png', 'titulo': 'Nude com brilho delicado'}  # Define a terceira imagem da galeria.
    ]  # Fecha a lista da galeria.
    return render_template('index.html', servicos=servicos, empresa=EMPRESA, galeria=galeria)  # Abre o template index.html e envia serviços, empresa e fotos.


@publico.route('/agendar', methods=['GET'])  # Define a rota GET de agendamento, usada para abrir o formulário.
def agendar_get():  # Cria a função que mostra a página de agendamento vazia.
    servicos = buscar_servicos()  # Busca os serviços cadastrados para preencher o select.
    dados = {'nome': '', 'telefone': '', 'email': '', 'servico_id': '', 'data': '', 'horario': ''}  # Cria dados vazios para evitar erro no HTML.
    return render_template('agendamento.html', servicos=servicos, empresa=EMPRESA, horarios=HORARIOS, horarios_ocupados=[], dados=dados, erro=None)  # Abre o formulário sem erro e sem horários ocupados.


@publico.route('/agendar', methods=['POST'])  # Define a rota POST de agendamento, usada quando o formulário é enviado.
def agendar_post():  # Cria a função que processa os dados enviados pela cliente.
    db = get_db()  # Abre uma conexão com o banco de dados.
    nome = request.form.get('nome', '').strip()  # Recebe o nome digitado e remove espaços extras.
    telefone = request.form.get('telefone', '').strip()  # Recebe o telefone digitado e remove espaços extras.
    email = request.form.get('email', '').strip().lower()  # Recebe o email, remove espaços e coloca em minúsculo.
    servico_id = request.form.get('servico_id', '').strip()  # Recebe o id do serviço escolhido.
    data = request.form.get('data', '').strip()  # Recebe a data escolhida.
    horario = request.form.get('horario', '').strip()  # Recebe o horário escolhido.
    dados = {'nome': nome, 'telefone': telefone, 'email': email, 'servico_id': servico_id, 'data': data, 'horario': horario}  # Guarda os dados para manter o formulário preenchido se houver erro.

    def erro_form(msg):  # Cria uma função interna para recarregar o formulário mostrando uma mensagem de erro.
        agendados = db.execute('SELECT horario FROM agendamentos WHERE data = ? AND status != ?', (data, 'cancelado')).fetchall()  # Busca horários ocupados nessa data, ignorando cancelados.
        horarios_ocupados = {row['horario'] for row in agendados}  # Transforma os horários ocupados em um conjunto para facilitar a verificação.
        return render_template('agendamento.html', servicos=buscar_servicos(), empresa=EMPRESA, horarios=HORARIOS, horarios_ocupados=horarios_ocupados, dados=dados, erro=msg)  # Retorna o formulário com a mensagem de erro.

    if len(nome) < 2:  # Verifica se o nome tem pelo menos 2 caracteres.
        return erro_form('Informe um nome válido.')  # Retorna erro se o nome estiver inválido.
    if len(telefone) < 8:  # Verifica se o telefone tem tamanho mínimo aceitável.
        return erro_form('Informe um telefone válido.')  # Retorna erro se o telefone estiver inválido.
    if email != '' and ('@' not in email or '.' not in email):  # Verifica se o email preenchido tem formato básico com arroba e ponto.
        return erro_form('Informe um email válido.')  # Retorna erro se o email estiver inválido.
    if servico_id == '':  # Verifica se a cliente escolheu algum serviço.
        return erro_form('Selecione um serviço.')  # Retorna erro se nenhum serviço foi selecionado.
    if data == '':  # Verifica se a data foi informada.
        return erro_form('Selecione uma data.')  # Retorna erro se a data estiver vazia.
    if horario == '':  # Verifica se o horário foi escolhido.
        return erro_form('Selecione um horário.')  # Retorna erro se o horário estiver vazio.

    conflito = db.execute('SELECT id FROM agendamentos WHERE data = ? AND horario = ? AND status != ?', (data, horario, 'cancelado')).fetchone()  # Procura se já existe agendamento no mesmo dia e horário.
    if conflito:  # Verifica se encontrou conflito no banco.
        return erro_form('Horário indisponível para a data selecionada.')  # Retorna erro se o horário já estiver ocupado.

    cliente = db.execute('SELECT id FROM clientes WHERE telefone = ?', (telefone,)).fetchone()  # Procura se já existe cliente com esse telefone.
    if cliente:  # Verifica se o cliente já existe.
        cliente_id = cliente['id']  # Usa o id do cliente já cadastrado.
    else:  # Executa caso o cliente ainda não exista.
        cursor = db.execute('INSERT INTO clientes (nome, telefone, email) VALUES (?, ?, ?)', (nome, telefone, email))  # Cadastra um novo cliente no banco.
        cliente_id = cursor.lastrowid  # Pega o id do cliente recém-cadastrado.

    db.execute('INSERT INTO agendamentos (cliente_id, servico_id, data, horario, status) VALUES (?, ?, ?, ?, ?)', (cliente_id, servico_id, data, horario, 'pendente'))  # Cadastra o agendamento como pendente.
    db.commit()  # Salva oficialmente as alterações no banco.
    return redirect(url_for('publico.confirmacao'))  # Redireciona para a página de confirmação.


@publico.route('/confirmacao')  # Define a rota da página de confirmação.
def confirmacao():  # Cria a função que mostra a confirmação do agendamento.
    return render_template('confirmacao.html', empresa=EMPRESA)  # Abre o template de confirmação e envia os dados da empresa.


@publico.route('/horarios-disponiveis')  # Define uma rota auxiliar que devolve horários livres em JSON.
def horarios_disponiveis():  # Cria a função que consulta horários disponíveis.
    data = request.args.get('data')  # Recebe a data enviada pela URL.
    db = get_db()  # Abre uma conexão com o banco.
    agendados = db.execute('SELECT horario FROM agendamentos WHERE data = ? AND status != ?', (data, 'cancelado')).fetchall()  # Busca horários já agendados para a data.
    horarios_ocupados = {row['horario'] for row in agendados}  # Cria um conjunto com horários ocupados.
    disponiveis = [h for h in HORARIOS if h not in horarios_ocupados]  # Monta a lista de horários ainda livres.
    return jsonify(disponiveis)  # Retorna os horários livres no formato JSON.


ADMIN_USUARIO = 'admin'  # Define o usuário de acesso administrativo.
ADMIN_SENHA = 'esmalteria123'  # Define a senha de acesso administrativo.


@admin.route('/login', methods=['GET', 'POST'])  # Define a rota de login do admin, aceitando abrir página e enviar formulário.
def login():  # Cria a função de login administrativo.
    if request.method == 'POST':  # Verifica se o formulário de login foi enviado.
        usuario = request.form.get('usuario', '')  # Recebe o usuário digitado.
        senha = request.form.get('senha', '')  # Recebe a senha digitada.
        if usuario == ADMIN_USUARIO and senha == ADMIN_SENHA:  # Confere se usuário e senha estão corretos.
            session['logado'] = True  # Salva na sessão que o admin está logado.
            return redirect(url_for('admin.dashboard'))  # Redireciona para o painel administrativo.
        return render_template('admin/login.html', erro='Usuário ou senha inválidos.', empresa=EMPRESA)  # Mostra erro se o login estiver incorreto.
    return render_template('admin/login.html', empresa=EMPRESA)  # Abre a tela de login quando o acesso é GET.


@admin.route('/logout')  # Define a rota para sair da área administrativa.
def logout():  # Cria a função de logout.
    session.clear()  # Limpa todos os dados da sessão.
    return redirect(url_for('admin.login'))  # Redireciona para a página de login.


@admin.route('/dashboard')  # Define a rota do painel de agendamentos.
def dashboard():  # Cria a função que mostra o dashboard.
    if not session.get('logado'):  # Verifica se o usuário não está logado.
        return redirect(url_for('admin.login'))  # Redireciona para login se não estiver autenticado.
    filtro_status = request.args.get('status', '').strip()  # Recebe o filtro de status vindo da URL.
    filtro_data = request.args.get('data', '').strip()  # Recebe o filtro de data vindo da URL.
    sql = '''SELECT a.id, a.data, a.horario, a.status,
                    c.nome AS cliente_nome, c.telefone, c.email,
                    s.nome AS servico_nome, s.preco, s.duracao_min
             FROM agendamentos a
             JOIN clientes c ON c.id = a.cliente_id
             JOIN servicos s ON s.id = a.servico_id'''  # Monta a consulta SQL para juntar agendamento, cliente e serviço.
    where = []  # Cria uma lista para guardar filtros SQL.
    params = []  # Cria uma lista para guardar os valores dos filtros.
    if filtro_status in ('pendente', 'confirmado', 'cancelado'):  # Verifica se o status informado é permitido.
        where.append('a.status = ?')  # Adiciona o filtro de status no SQL.
        params.append(filtro_status)  # Adiciona o valor do status nos parâmetros.
    if filtro_data:  # Verifica se uma data foi informada.
        where.append('a.data = ?')  # Adiciona o filtro de data no SQL.
        params.append(filtro_data)  # Adiciona o valor da data nos parâmetros.
    if where:  # Verifica se existe algum filtro para aplicar.
        sql += ' WHERE ' + ' AND '.join(where)  # Junta os filtros na consulta SQL.
    sql += ' ORDER BY a.data, a.horario'  # Ordena os resultados por data e horário.
    db = get_db()  # Abre uma conexão com o banco.
    agendamentos = db.execute(sql, params).fetchall()  # Executa a consulta e busca os agendamentos.
    return render_template('admin/dashboard.html', agendamentos=agendamentos, filtro_status=filtro_status, filtro_data=filtro_data, empresa=EMPRESA)  # Abre o dashboard com os agendamentos e filtros.


@admin.route('/agendamento/<int:id>/status', methods=['POST'])  # Define a rota que altera o status de um agendamento.
def atualizar_status(id):  # Cria a função que atualiza o status.
    if not session.get('logado'):  # Verifica se o admin não está logado.
        return redirect(url_for('admin.login'))  # Redireciona para login se necessário.
    novo_status = request.form.get('novo_status')  # Recebe o novo status enviado pelo formulário.
    db = get_db()  # Abre uma conexão com o banco.
    db.execute('UPDATE agendamentos SET status = ? WHERE id = ?', (novo_status, id))  # Atualiza o status do agendamento no banco.
    db.commit()  # Salva a alteração no banco.
    return redirect(url_for('admin.dashboard'))  # Volta para o dashboard.


@admin.route('/servicos')  # Define a rota administrativa que lista os serviços.
def servicos():  # Cria a função que mostra os serviços no admin.
    if not session.get('logado'):  # Verifica se o admin não está logado.
        return redirect(url_for('admin.login'))  # Redireciona para login caso não esteja logado.
    lista = buscar_servicos()  # Busca os serviços cadastrados.
    return render_template('admin/servicos.html', servicos=lista, empresa=EMPRESA)  # Abre o template de serviços.


def _parse_servico_form():  # Cria uma função auxiliar para ler e validar formulário de serviço.
    nome = request.form.get('nome', '').strip()  # Recebe o nome do serviço.
    preco_raw = request.form.get('preco', '').strip().replace(',', '.')  # Recebe o preço e troca vírgula por ponto.
    duracao_raw = request.form.get('duracao_min', '').strip()  # Recebe a duração em minutos.
    erro = None  # Cria uma variável para guardar erro, começando sem erro.
    preco = duracao = None  # Cria as variáveis preço e duração começando vazias.
    try:  # Inicia tentativa de converter os valores para número.
        preco = float(preco_raw)  # Converte o preço para número decimal.
        duracao = int(duracao_raw)  # Converte a duração para número inteiro.
    except ValueError:  # Captura erro caso preço ou duração não sejam números.
        erro = 'Preço e duração precisam ser numéricos.'  # Define uma mensagem de erro.
    if not erro:  # Continua a validação se ainda não existe erro.
        if not nome:  # Verifica se o nome está vazio.
            erro = 'Nome é obrigatório.'  # Define erro de nome obrigatório.
        elif preco < 0:  # Verifica se o preço é negativo.
            erro = 'Preço não pode ser negativo.'  # Define erro de preço negativo.
        elif duracao <= 0:  # Verifica se a duração é zero ou negativa.
            erro = 'Duração deve ser maior que zero.'  # Define erro de duração inválida.
    return nome, preco, duracao, erro  # Retorna os dados tratados e a mensagem de erro, se existir.


@admin.route('/servicos/novo', methods=['GET', 'POST'])  # Define a rota para criar novo serviço.
def servico_novo():  # Cria a função de cadastro de serviço.
    if not session.get('logado'):  # Verifica se o admin está logado.
        return redirect(url_for('admin.login'))  # Redireciona para login se não estiver logado.
    if request.method == 'POST':  # Verifica se o formulário foi enviado.
        nome, preco, duracao, erro = _parse_servico_form()  # Lê e valida os dados do formulário.
        if erro:  # Verifica se houve erro na validação.
            return render_template('admin/servico_form.html', servico=None, form=request.form, erro=erro, empresa=EMPRESA)  # Reabre o formulário com erro.
        db = get_db()  # Abre conexão com o banco.
        db.execute('INSERT INTO servicos (nome, preco, duracao_min) VALUES (?, ?, ?)', (nome, preco, duracao))  # Insere o novo serviço.
        db.commit()  # Salva o novo serviço no banco.
        flash(f'Serviço "{nome}" criado com sucesso.', 'success')  # Mostra mensagem de sucesso.
        return redirect(url_for('admin.servicos'))  # Volta para a lista de serviços.
    return render_template('admin/servico_form.html', servico=None, form=None, empresa=EMPRESA)  # Abre formulário vazio quando a requisição é GET.


@admin.route('/servicos/<int:id>/editar', methods=['GET', 'POST'])  # Define a rota para editar serviço existente.
def servico_editar(id):  # Cria a função de edição de serviço.
    if not session.get('logado'):  # Verifica se o admin está logado.
        return redirect(url_for('admin.login'))  # Redireciona para login se não estiver logado.
    db = get_db()  # Abre conexão com o banco.
    servico = db.execute('SELECT * FROM servicos WHERE id = ?', (id,)).fetchone()  # Busca o serviço pelo id.
    if servico is None:  # Verifica se o serviço não foi encontrado.
        flash('Serviço não encontrado.', 'error')  # Mostra mensagem de erro.
        return redirect(url_for('admin.servicos'))  # Volta para a lista de serviços.
    if request.method == 'POST':  # Verifica se o formulário foi enviado.
        nome, preco, duracao, erro = _parse_servico_form()  # Lê e valida os dados enviados.
        if erro:  # Verifica se houve erro na validação.
            return render_template('admin/servico_form.html', servico=servico, form=request.form, erro=erro, empresa=EMPRESA)  # Reabre o formulário com erro.
        db.execute('UPDATE servicos SET nome = ?, preco = ?, duracao_min = ? WHERE id = ?', (nome, preco, duracao, id))  # Atualiza o serviço no banco.
        db.commit()  # Salva a atualização.
        flash(f'Serviço "{nome}" atualizado.', 'success')  # Mostra mensagem de sucesso.
        return redirect(url_for('admin.servicos'))  # Volta para a lista de serviços.
    return render_template('admin/servico_form.html', servico=servico, form=None, empresa=EMPRESA)  # Abre o formulário preenchido quando a requisição é GET.


@admin.route('/servicos/<int:id>/excluir', methods=['POST'])  # Define a rota para excluir um serviço.
def servico_excluir(id):  # Cria a função de exclusão de serviço.
    if not session.get('logado'):  # Verifica se o admin está logado.
        return redirect(url_for('admin.login'))  # Redireciona para login se não estiver logado.
    db = get_db()  # Abre conexão com o banco.
    servico = db.execute('SELECT * FROM servicos WHERE id = ?', (id,)).fetchone()  # Busca o serviço pelo id.
    if servico is None:  # Verifica se o serviço não existe.
        flash('Serviço não encontrado.', 'error')  # Mostra mensagem de erro.
        return redirect(url_for('admin.servicos'))  # Volta para a lista de serviços.
    em_uso = db.execute('SELECT COUNT(*) AS n FROM agendamentos WHERE servico_id = ?', (id,)).fetchone()['n']  # Conta agendamentos que usam esse serviço.
    if em_uso:  # Verifica se o serviço está sendo usado em agendamentos.
        flash(f'Não é possível excluir "{servico["nome"]}": existem {em_uso} agendamento(s) usando este serviço.', 'error')  # Mostra erro impedindo exclusão.
        return redirect(url_for('admin.servicos'))  # Volta para a lista de serviços.
    db.execute('DELETE FROM servicos WHERE id = ?', (id,))  # Exclui o serviço do banco.
    db.commit()  # Salva a exclusão.
    flash(f'Serviço "{servico["nome"]}" excluído.', 'success')  # Mostra mensagem de sucesso.
    return redirect(url_for('admin.servicos'))  # Volta para a lista de serviços.


app.register_blueprint(publico)  # Registra as rotas públicas na aplicação Flask.
app.register_blueprint(admin)  # Registra as rotas administrativas na aplicação Flask.


@app.teardown_appcontext  # Define uma função que roda ao final de cada requisição.
def close_db(e=None):  # Cria a função responsável por fechar a conexão com o banco.
    from flask import g  # Importa g para acessar a conexão guardada durante a requisição.
    db = g.pop('db', None)  # Remove a conexão do objeto g, se ela existir.
    if db is not None:  # Verifica se havia conexão aberta.
        db.close()  # Fecha a conexão com o banco.


if __name__ == '__main__':  # Garante que o servidor só rode quando este arquivo for executado diretamente.
    init_db()  # Cria as tabelas e serviços iniciais se ainda não existirem.
    app.run(debug=True)  # Inicia o servidor Flask em modo debug para facilitar testes.
