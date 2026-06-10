from dotenv import load_dotenv
load_dotenv()

from flask import Flask, Blueprint, render_template, request, redirect, url_for, jsonify, session, flash, abort

from flask_wtf.csrf import CSRFProtect

from database import init_db, get_db, FOTOS_INICIAIS

from datetime import date, datetime, timedelta

import calendar

import os

import re

import uuid

from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-troque-em-producao')  # Nunca use o valor padrão em produção; defina SECRET_KEY no .env

csrf = CSRFProtect(app)

app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

PASTA_UPLOAD = os.path.join(app.static_folder, 'img', 'uploads')

EXTENSOES_IMAGEM = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

publico = Blueprint('publico', __name__)

admin = Blueprint('admin', __name__, url_prefix='/admin')

profissional = Blueprint('profissional', __name__, url_prefix='/profissional')


@app.context_processor
def injetar_configuracoes():
    try:
        return {
            'config_visual': carregar_configuracoes_visuais(),
            'css_aparencia': gerar_css_aparencia(),
            'pagina_atual': pagina_atual(),
            'textos': carregar_textos(),
            'existe_profissional_com_senha': existe_profissional_com_senha(),
        }
    except Exception:
        return {'config_visual': {}, 'css_aparencia': '', 'pagina_atual': '', 'textos': TEXTOS_PADRAO, 'existe_profissional_com_senha': False}


EMPRESA = {
    'nome': 'Refúgio da Preta',
    'marca_subtitulo': 'Studio de manicure e beleza',
    'dona': 'Pamela Francisco',
    'telefone': '(11) 99220-4706',
    'atendimento': 'Atendimento a domicílio e na residência da profissional',
    'horarios': 'Terça a sábado, das 10h às 19h',
    'instagram_nome': '@refugiodapreta',
    'instagram_url': 'https://www.instagram.com/refugiodapreta/',
    'foto_dona': 'pamela_francisco.png',
    'slogan': 'Beleza, cuidado e acolhimento.',
}


TEXTOS_CAMPOS = [
    ('Informações da empresa', [
        ('empresa.nome', 'Nome da empresa', 'Refúgio da Preta', 'text'),
        ('empresa.marca_subtitulo', 'Subtítulo no topo do site', 'Studio de manicure e beleza', 'text'),
        ('empresa.dona', 'Nome da responsável', 'Pamela Francisco', 'text'),
        ('empresa.slogan', 'Slogan (rodapé)', 'Beleza, cuidado e acolhimento.', 'text'),
        ('empresa.telefone', 'Telefone', '(11) 99220-4706', 'text'),
        ('empresa.horarios', 'Horários de atendimento', 'Terça a sábado, das 10h às 19h', 'text'),
        ('empresa.atendimento', 'Como é o atendimento', 'Atendimento a domicílio e na residência da profissional', 'text'),
        ('empresa.instagram_nome', 'Instagram (@)', '@refugiodapreta', 'text'),
        ('empresa.instagram_url', 'Link do Instagram', 'https://www.instagram.com/refugiodapreta/', 'text'),
    ]),
    ('Início — Destaque (topo)', [
        ('texto.hero_subtitulo', 'Frase pequena acima do nome', 'Cuidado estético especializado', 'text'),
        ('texto.hero_p1', 'Primeiro parágrafo', 'Um espaço dedicado ao cuidado das mãos e unhas, com atendimento personalizado, técnica e atenção aos detalhes.', 'textarea'),
        ('texto.hero_p2', 'Segundo parágrafo', 'Escolha o serviço desejado, selecione a profissional disponível e reserve o melhor horário de forma prática.', 'textarea'),
        ('texto.hero_botao', 'Texto do botão principal', 'Agendar horário', 'text'),
        ('texto.hero_botao_insta', 'Texto do botão do Instagram', 'Conhecer trabalhos', 'text'),
    ]),
    ('Início — Chamada de agendamento', [
        ('texto.chamada_subtitulo', 'Subtítulo', 'Agendamento prático', 'text'),
        ('texto.chamada_titulo', 'Título', 'Reserve seu atendimento com organização e conforto', 'text'),
        ('texto.chamada_texto', 'Texto', 'O sistema exibe profissionais e horários disponíveis conforme o serviço selecionado.', 'textarea'),
    ]),
    ('Início — Serviços', [
        ('texto.servicos_titulo', 'Título', 'Serviços', 'text'),
        ('texto.servicos_texto', 'Descrição', 'Confira algumas opções disponíveis para reserva.', 'textarea'),
    ]),
    ('Início — Galeria', [
        ('texto.galeria_titulo', 'Título', 'Galeria de trabalhos', 'text'),
        ('texto.galeria_texto', 'Descrição', 'Resultados que demonstram cuidado, acabamento e atenção aos detalhes.', 'textarea'),
    ]),
    ('Início — Responsável', [
        ('texto.responsavel_subtitulo', 'Subtítulo', 'Responsável pelo atendimento', 'text'),
        ('texto.responsavel_p1', 'Primeiro parágrafo', 'Responsável pelo Refúgio da Preta, Pamela conduz o atendimento com profissionalismo, cordialidade e precisão técnica.', 'textarea'),
        ('texto.responsavel_p2', 'Segundo parágrafo', 'A proposta do espaço é oferecer uma experiência agradável, organizada e cuidadosa em cada detalhe.', 'textarea'),
        ('texto.responsavel_botao', 'Texto do botão', 'Agendar atendimento', 'text'),
    ]),
    ('Página de agendamento', [
        ('texto.agendamento_subtitulo', 'Subtítulo', 'Agendamento online', 'text'),
        ('texto.agendamento_titulo', 'Título', 'Vamos começar o seu agendamento', 'text'),
        ('texto.agendamento_intro', 'Texto de introdução', 'Informe seu nome e telefone para contato. Em seguida vamos escolher serviço, profissional, data e horário em etapas rápidas.', 'textarea'),
    ]),
]

TEXTOS_PADRAO = {chave: padrao for _grupo, campos in TEXTOS_CAMPOS for chave, _rotulo, padrao, _tipo in campos}


def carregar_textos():
    db = get_db()
    salvos = {linha['chave']: linha['valor'] for linha in db.execute("SELECT chave, valor FROM configuracoes WHERE chave LIKE 'texto.%' OR chave LIKE 'empresa.%'").fetchall()}
    completo = dict(TEXTOS_PADRAO)
    completo.update({c: v for c, v in salvos.items() if v})
    return completo


def dados_empresa():
    dados = dict(EMPRESA)
    try:
        db = get_db()
        linhas = db.execute("SELECT chave, valor FROM configuracoes WHERE chave LIKE 'empresa.%'").fetchall()
        for linha in linhas:
            if linha['valor']:
                dados[linha['chave'].split('.', 1)[1]] = linha['valor']
    except Exception:
        pass
    return dados


def existe_profissional_com_senha():
    try:
        db = get_db()
        total = db.execute("SELECT COUNT(*) FROM profissionais WHERE ativo = 1 AND senha IS NOT NULL AND senha != ''").fetchone()[0]
        return total > 0
    except Exception:
        return False


HORARIOS = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00']

DIAS_FUNCIONAMENTO = {1, 2, 3, 4, 5}  # weekday(): 0=segunda, 1=terça, 2=quarta, 3=quinta, 4=sexta, 5=sábado

ADMIN_USUARIO = os.getenv('ADMIN_USUARIO', 'admin')

ADMIN_SENHA = os.getenv('ADMIN_SENHA', 'esmalteria123')


def esta_logado():
    return session.get('logado') is True


def profissional_logada_id():
    return session.get('profissional_id')


def buscar_profissional_logada():
    pid = profissional_logada_id()
    if not pid:
        return None
    db = get_db()
    return db.execute('SELECT * FROM profissionais WHERE id = ?', (pid,)).fetchone()


def carregar_configuracoes_visuais():
    db = get_db()
    linhas = db.execute('SELECT chave, valor FROM configuracoes').fetchall()
    return {linha['chave']: linha['valor'] for linha in linhas}


PROP_CSS = {
    'cor_fundo': 'background',
    'cor_texto': 'color',
}

PROP_ROTULO = {
    'cor_fundo': 'Cor de fundo',
    'cor_texto': 'Cor do texto',
}

PROP_PADRAO = {
    'cor_fundo': '#efe0d1',
    'cor_texto': '#3f2d25',
}

APARENCIA_PAGINAS = {
    'global': {
        'rotulo': 'Geral (todas as páginas)',
        'escopo': None,
        'areas': {
            'corpo': {'rotulo': 'Fundo e texto gerais', 'seletor': 'body', 'props': ['cor_fundo', 'cor_texto']},
            'topo': {'rotulo': 'Topo / cabeçalho', 'seletor': '.topo', 'props': ['cor_fundo', 'cor_texto']},
            'rodape': {'rotulo': 'Rodapé', 'seletor': '.rodape', 'props': ['cor_fundo', 'cor_texto']},
            'botoes': {'rotulo': 'Botões e destaques', 'seletor': '.botao, .botao-principal, .botao-destaque, .nav-destaque, button[type="submit"]', 'props': ['cor_fundo', 'cor_texto']},
        },
    },
    'inicio': {
        'rotulo': 'Página Início',
        'escopo': 'inicio',
        'areas': {
            'hero': {'rotulo': 'Destaque principal (topo da página)', 'seletor': '.hero', 'props': ['cor_fundo', 'cor_texto']},
            'chamada': {'rotulo': 'Chamada de agendamento', 'seletor': '.chamada-agendamento', 'props': ['cor_fundo', 'cor_texto']},
            'servicos': {'rotulo': 'Seção de serviços', 'seletor': '#servicos', 'props': ['cor_fundo', 'cor_texto']},
            'galeria': {'rotulo': 'Seção da galeria', 'seletor': '#galeria', 'props': ['cor_fundo', 'cor_texto']},
            'responsavel': {'rotulo': 'Seção da responsável', 'seletor': '#dona', 'props': ['cor_fundo', 'cor_texto']},
        },
    },
    'agendamento': {
        'rotulo': 'Página de Agendamento',
        'escopo': 'agendamento',
        'areas': {
            'conteudo': {'rotulo': 'Fundo do conteúdo', 'seletor': 'main', 'props': ['cor_fundo', 'cor_texto']},
        },
    },
}

FOTOS_LOCAIS = {
    'galeria': {'rotulo': 'Galeria de trabalhos (página inicial)', 'multiplas': True},
    'responsavel': {'rotulo': 'Foto da responsável (Pamela)', 'multiplas': False},
}


def cor_valida(valor):
    # Valida formato hex (#rgb ou #rrggbb) para evitar injeção de CSS via inputs de cor do admin
    return bool(valor) and bool(re.fullmatch(r'#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?', valor))


def carregar_aparencia():
    db = get_db()
    linhas = db.execute("SELECT chave, valor FROM configuracoes WHERE chave LIKE 'aparencia.%'").fetchall()
    return {linha['chave']: linha['valor'] for linha in linhas}


def gerar_css_aparencia():
    valores = carregar_aparencia()
    regras = []
    for pagina, info in APARENCIA_PAGINAS.items():
        escopo = info.get('escopo')
        prefixo = '.pagina-' + escopo + ' ' if escopo else ''
        for area, dados in info['areas'].items():
            declaracoes = []
            for prop in dados['props']:
                valor = valores.get('aparencia.' + pagina + '.' + area + '.' + prop)
                if cor_valida(valor):
                    declaracoes.append(PROP_CSS[prop] + ': ' + valor + ';')
            if declaracoes:
                regras.append(prefixo + dados['seletor'] + ' { ' + ' '.join(declaracoes) + ' }')
    return '\n'.join(regras)


def pagina_atual():
    endpoint = request.endpoint or ''
    if endpoint == 'publico.index':
        return 'inicio'
    if endpoint.startswith('publico.agendar'):
        return 'agendamento'
    if endpoint == 'publico.confirmacao':
        return 'confirmacao'
    return ''


def buscar_fotos(local):
    db = get_db()
    return db.execute('SELECT * FROM fotos WHERE local = ? ORDER BY ordem, id', (local,)).fetchall()


def extensao_permitida(nome_arquivo):
    return '.' in nome_arquivo and nome_arquivo.rsplit('.', 1)[1].lower() in EXTENSOES_IMAGEM


def salvar_foto_upload(arquivo):
    if not arquivo or arquivo.filename == '':
        return None
    if not extensao_permitida(arquivo.filename):
        return None
    os.makedirs(PASTA_UPLOAD, exist_ok=True)
    extensao = arquivo.filename.rsplit('.', 1)[1].lower()
    base = secure_filename(arquivo.filename.rsplit('.', 1)[0]) or 'foto'
    nome_final = base + '_' + uuid.uuid4().hex[:8] + '.' + extensao
    arquivo.save(os.path.join(PASTA_UPLOAD, nome_final))
    return 'uploads/' + nome_final


def remover_arquivo_foto(caminho):
    # Só apaga arquivos em uploads/ — imagens originais do projeto são compartilhadas e não devem ser deletadas
    if not caminho or not caminho.startswith('uploads/'):
        return
    caminho_completo = os.path.join(app.static_folder, 'img', caminho)
    try:
        os.remove(caminho_completo)
    except OSError:
        pass


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
    galeria = buscar_fotos('galeria')
    fotos_responsavel = buscar_fotos('responsavel')
    foto_dona = fotos_responsavel[0]['arquivo'] if fotos_responsavel else EMPRESA['foto_dona']
    return render_template('index.html', servicos=servicos, empresa=dados_empresa(), galeria=galeria, foto_dona=foto_dona)


@publico.route('/agendar', methods=['GET'])
def agendar_get():
    servicos = buscar_servicos()
    profissionais = buscar_profissionais()
    profissionais_servicos = buscar_vinculos_profissionais_servicos()
    dados = {'nome': '', 'telefone': '', 'servico_id': '', 'profissional_id': '', 'data': '', 'horario': ''}
    return render_template('agendamento.html', servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, empresa=dados_empresa(), horarios=HORARIOS, horarios_ocupados=[], dados=dados, erro=None)


@publico.route('/agendar', methods=['POST'])
def agendar_post():
    db = get_db()
    nome = request.form.get('nome', '').strip()
    telefone = request.form.get('telefone', '').strip()
    servico_id = request.form.get('servico_id', '').strip()
    profissional_id = request.form.get('profissional_id', '').strip()
    data_texto = request.form.get('data', '').strip()
    horario = request.form.get('horario', '').strip()
    if servico_id and not servico_id.isdigit():
        abort(400)
    if profissional_id and not profissional_id.isdigit():
        abort(400)
    dados = {'nome': nome, 'telefone': telefone, 'servico_id': servico_id, 'profissional_id': profissional_id, 'data': data_texto, 'horario': horario}

    def erro_form(msg):
        servicos = buscar_servicos()
        profissionais = buscar_profissionais()
        profissionais_servicos = buscar_vinculos_profissionais_servicos()
        horarios_ocupados = buscar_horarios_indisponiveis(data_texto, profissional_id)
        return render_template('agendamento.html', servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, empresa=dados_empresa(), horarios=HORARIOS, horarios_ocupados=horarios_ocupados, dados=dados, erro=msg)

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
    return render_template('confirmacao.html', empresa=dados_empresa())


@publico.route('/horarios-disponiveis')
def horarios_disponiveis():
    data_texto = request.args.get('data', '').strip()
    profissional_id = request.args.get('profissional_id', '').strip()
    horarios = montar_lista_horarios(data_texto, profissional_id)
    return jsonify({'data': data_texto, 'horarios': horarios})


@publico.route('/disponibilidade-mes')
def disponibilidade_mes():
    try:
        ano = int(request.args.get('ano', date.today().year))
        mes = int(request.args.get('mes', date.today().month))
    except (ValueError, TypeError):
        return jsonify({'erro': 'parametros invalidos'}), 400
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
        return render_template('admin/login.html', erro='Usuário ou senha inválidos.', empresa=dados_empresa())
    return render_template('admin/login.html', empresa=dados_empresa())


@admin.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.login'))


@admin.route('/agenda')
def agenda():
    if not esta_logado():
        return redirect(url_for('admin.login'))
    profissionais = buscar_profissionais(False)
    return render_template('admin/agenda.html', profissionais=profissionais, empresa=dados_empresa())


@admin.route('/agenda/dia')
def agenda_dia():
    if not esta_logado():
        return jsonify({'erro': 'nao_autenticado'}), 401
    data_texto = request.args.get('data', '').strip()
    profissional_id = request.args.get('profissional_id', '').strip()
    if not data_texto or not profissional_id:
        return jsonify({'data': data_texto, 'horarios': []})
    aberto = dia_funciona(data_texto)
    db = get_db()
    sql = '''SELECT a.id, a.horario, a.status,
                    c.nome AS cliente_nome, c.telefone,
                    s.nome AS servico_nome, s.preco, s.duracao_min
             FROM agendamentos a
             JOIN clientes c ON c.id = a.cliente_id
             JOIN servicos s ON s.id = a.servico_id
             WHERE a.data = ? AND a.profissional_id = ? AND a.status != ?'''
    linhas = db.execute(sql, (data_texto, profissional_id, 'cancelado')).fetchall()
    ocupados = {linha['horario']: linha for linha in linhas}
    bloqueios = buscar_bloqueios(data_texto, profissional_id)
    resposta = []
    for horario in HORARIOS:
        ocupado = ocupados.get(horario)
        slot = {'horario': horario, 'aberto': aberto, 'bloqueado': horario in bloqueios, 'agendamento': None}
        if ocupado:
            slot['agendamento'] = {
                'id': ocupado['id'],
                'cliente_nome': ocupado['cliente_nome'],
                'telefone': ocupado['telefone'],
                'servico_nome': ocupado['servico_nome'],
                'preco': float(ocupado['preco']),
                'duracao_min': ocupado['duracao_min'],
                'status': ocupado['status'],
            }
        resposta.append(slot)
    return jsonify({'data': data_texto, 'aberto': aberto, 'horarios': resposta})


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
    where = ['a.arquivado = 0']
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
    sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY a.data, a.horario'
    db = get_db()
    agendamentos = db.execute(sql, params).fetchall()
    profissionais = buscar_profissionais(False)
    kpis = calcular_kpis_dashboard(db)
    hoje_iso = date.today().isoformat()
    tem_completos_para_arquivar = db.execute(
        "SELECT COUNT(*) AS n FROM agendamentos WHERE arquivado = 0 AND status = 'confirmado' AND data < ?",
        (hoje_iso,)
    ).fetchone()['n'] > 0
    return render_template('admin/dashboard.html', agendamentos=agendamentos, profissionais=profissionais, filtro_status=filtro_status, filtro_data=filtro_data, filtro_profissional=filtro_profissional, empresa=dados_empresa(), kpis=kpis, hoje=hoje_iso, tem_completos_para_arquivar=tem_completos_para_arquivar)


def calcular_kpis_dashboard(db):
    hoje = date.today().isoformat()
    inicio_semana = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    fim_semana = (date.today() + timedelta(days=6 - date.today().weekday())).isoformat()
    total_hoje = db.execute(
        "SELECT COUNT(*) AS n FROM agendamentos WHERE data = ? AND status != 'cancelado' AND arquivado = 0",
        (hoje,)
    ).fetchone()['n']
    confirmados_hoje = db.execute(
        "SELECT COUNT(*) AS n FROM agendamentos WHERE data = ? AND status = 'confirmado' AND arquivado = 0",
        (hoje,)
    ).fetchone()['n']
    pendentes = db.execute(
        "SELECT COUNT(*) AS n FROM agendamentos WHERE status = 'pendente' AND data >= ? AND arquivado = 0",
        (hoje,)
    ).fetchone()['n']
    receita_semana = db.execute(
        """SELECT COALESCE(SUM(s.preco), 0) AS total
           FROM agendamentos a
           JOIN servicos s ON s.id = a.servico_id
           WHERE a.data BETWEEN ? AND ? AND a.status != 'cancelado' AND a.arquivado = 0""",
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
    if novo_status not in ('pendente', 'confirmado', 'concluido', 'cancelado'):
        flash('Status inválido.', 'error')
        return redirect(request.referrer or url_for('admin.dashboard'))
    db = get_db()
    db.execute('UPDATE agendamentos SET status = ? WHERE id = ?', (novo_status, id))
    db.commit()
    flash('Status do agendamento atualizado.', 'success')
    return redirect(request.referrer or url_for('admin.dashboard'))


@admin.route('/agendamento/<int:id>/pagamento', methods=['POST'])
def atualizar_pagamento(id):
    if not esta_logado():
        return redirect(url_for('admin.login'))
    pago = 1 if request.form.get('pago') == '1' else 0
    db = get_db()
    # Marca pago e arquiva (vai para o histórico) ou desmarca pago e restaura para os ativos.
    db.execute('UPDATE agendamentos SET pago = ?, arquivado = ? WHERE id = ?', (pago, pago, id))
    db.commit()
    flash('Atendimento marcado como pago e movido para o histórico.' if pago else 'Marcação de pago removida e atendimento restaurado.', 'success')
    return redirect(request.referrer or url_for('admin.atendimentos'))


def buscar_atendimentos(condicao, params):
    db = get_db()
    sql = '''SELECT a.id, a.data, a.horario, a.status, a.pago,
                    c.nome AS cliente_nome, c.telefone,
                    s.nome AS servico_nome, s.preco, s.duracao_min,
                    p.nome AS profissional_nome
             FROM agendamentos a
             JOIN clientes c ON c.id = a.cliente_id
             JOIN servicos s ON s.id = a.servico_id
             JOIN profissionais p ON p.id = a.profissional_id
             WHERE ''' + condicao + ' ORDER BY a.data, a.horario'
    return db.execute(sql, params).fetchall()


@admin.route('/confirmacoes')
def confirmacoes():
    # Mantém URL antiga apontando para os agendamentos pendentes no dashboard unificado.
    return redirect(url_for('admin.dashboard', status='pendente'))


@admin.route('/atendimentos')
def atendimentos():
    if not esta_logado():
        return redirect(url_for('admin.login'))
    aba = request.args.get('aba', 'confirmados')
    if aba not in ('confirmados', 'concluidos', 'pagos'):
        aba = 'confirmados'
    if aba == 'confirmados':
        itens = buscar_atendimentos("a.arquivado = 0 AND a.status = 'confirmado'", [])
        secao = {'titulo': 'Confirmados', 'descricao': 'Clientes confirmados que vão acontecer. Marque como concluído depois de atender.', 'itens': itens, 'acoes': ['concluir', 'cancelar'], 'vazio': 'Nenhum cliente confirmado no momento.'}
    elif aba == 'concluidos':
        itens = buscar_atendimentos("a.arquivado = 0 AND a.status = 'concluido' AND a.pago = 0", [])
        secao = {'titulo': 'Concluídos aguardando pagamento', 'descricao': 'Atendimentos realizados. Ao marcar como pago, vão automaticamente para o histórico.', 'itens': itens, 'acoes': ['pagamento'], 'vazio': 'Nenhum atendimento aguardando pagamento.'}
    else:
        itens = buscar_atendimentos("a.pago = 1", [])
        secao = {'titulo': 'Atendimentos pagos', 'descricao': 'Histórico de pagamentos. Use "Desfazer pago" se marcou por engano.', 'itens': itens, 'acoes': ['despagar'], 'vazio': 'Nenhum atendimento marcado como pago ainda.'}
    tabs = [
        {'aba': 'agendamentos', 'rotulo': 'Agendamentos', 'url': url_for('admin.dashboard')},
        {'aba': 'confirmados', 'rotulo': 'Confirmados', 'url': url_for('admin.atendimentos', aba='confirmados')},
        {'aba': 'concluidos', 'rotulo': 'Concluídos', 'url': url_for('admin.atendimentos', aba='concluidos')},
        {'aba': 'pagos', 'rotulo': 'Pagos', 'url': url_for('admin.atendimentos', aba='pagos')},
    ]
    return render_template(
        'admin/atendimentos.html',
        titulo='Atendimentos',
        descricao='Acompanhe o ciclo: confirmado → concluído → pago. Marcar como pago move automaticamente para o histórico.',
        secoes=[secao],
        tabs=tabs,
        aba_atual=aba,
        empresa=dados_empresa(),
    )


@admin.route('/concluidos')
def concluidos():
    # Mantém URL antiga apontando para a tab correspondente do dashboard unificado.
    return redirect(url_for('admin.atendimentos', aba='concluidos'))


@admin.route('/pagos')
def pagos():
    # Mantém URL antiga apontando para a tab correspondente do dashboard unificado.
    return redirect(url_for('admin.atendimentos', aba='pagos'))


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
        if (servico_id and not servico_id.isdigit()) or (profissional_id and not profissional_id.isdigit()):
            abort(400)
        if servico_id == '' or profissional_id == '' or data_texto == '' or horario == '' or status == '':
            flash('Preencha todos os campos do agendamento.', 'error')
            lista_horarios = montar_lista_horarios(data_texto, profissional_id, ignorar_agendamento_id=id)
            return render_template('admin/agendamento_form.html', agendamento=agendamento, servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, lista_horarios=lista_horarios, empresa=dados_empresa())
        if not profissional_atende_servico(profissional_id, servico_id):
            flash('A profissional escolhida não atende esse serviço.', 'error')
            lista_horarios = montar_lista_horarios(data_texto, profissional_id, ignorar_agendamento_id=id)
            return render_template('admin/agendamento_form.html', agendamento=agendamento, servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, lista_horarios=lista_horarios, empresa=dados_empresa())
        if status != 'cancelado' and conflito_agenda(data_texto, horario, profissional_id, id):
            flash('Este horário está indisponível para a profissional escolhida.', 'error')
            lista_horarios = montar_lista_horarios(data_texto, profissional_id, ignorar_agendamento_id=id)
            return render_template('admin/agendamento_form.html', agendamento=agendamento, servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, lista_horarios=lista_horarios, empresa=dados_empresa())
        db.execute('UPDATE agendamentos SET servico_id = ?, profissional_id = ?, data = ?, horario = ?, status = ? WHERE id = ?', (servico_id, profissional_id, data_texto, horario, status, id))
        db.commit()
        flash('Agendamento atualizado com sucesso.', 'success')
        return redirect(url_for('admin.dashboard'))
    lista_horarios = montar_lista_horarios(agendamento['data'], str(agendamento['profissional_id']), ignorar_agendamento_id=id)
    return render_template('admin/agendamento_form.html', agendamento=agendamento, servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, lista_horarios=lista_horarios, empresa=dados_empresa())


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
    return render_template('admin/servicos.html', servicos=lista, empresa=dados_empresa())


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
            return render_template('admin/servico_form.html', servico=None, form=request.form, erro=erro, profissionais=profissionais, profissionais_selecionadas=set(ids_profissionais), empresa=dados_empresa())
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
    return render_template('admin/servico_form.html', servico=None, form=None, profissionais=profissionais, profissionais_selecionadas=set(), empresa=dados_empresa())


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
            return render_template('admin/servico_form.html', servico=servico, form=request.form, erro=erro, profissionais=profissionais, profissionais_selecionadas=set(ids_profissionais), empresa=dados_empresa())
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
    return render_template('admin/servico_form.html', servico=servico, form=None, profissionais=profissionais, profissionais_selecionadas=vinculadas_atual, empresa=dados_empresa())


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
    return render_template('admin/bloqueios.html', bloqueios=bloqueios_lista, profissionais=profissionais, horarios=HORARIOS, empresa=dados_empresa())


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
    return render_template('admin/profissionais.html', profissionais=lista, empresa=dados_empresa())


def _parse_profissional_form():
    nome = request.form.get('nome', '').strip()
    especialidade = request.form.get('especialidade', '').strip()
    foto = request.form.get('foto', '').strip()
    caminho_upload = salvar_foto_upload(request.files.get('foto_upload'))
    if caminho_upload:
        foto = caminho_upload
    ativo = 1 if request.form.get('ativo') == 'on' else 0
    senha = request.form.get('senha', '').strip()
    erro = None
    if len(nome) < 2:
        erro = 'Informe o nome da profissional.'
    elif len(especialidade) < 2:
        erro = 'Informe a especialidade.'
    elif foto == '':
        erro = 'Envie uma foto ou informe o nome de um arquivo já existente (ex: pamela_francisco.png).'
    return nome, especialidade, foto, ativo, senha, erro


@admin.route('/profissionais/nova', methods=['GET', 'POST'])
def profissional_nova():
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    servicos = buscar_servicos()
    if request.method == 'POST':
        nome, especialidade, foto, ativo, senha, erro = _parse_profissional_form()
        ids_servicos = request.form.getlist('servicos_ids')
        if erro:
            return render_template('admin/profissional_form.html', profissional=None, form=request.form, erro=erro, servicos=servicos, servicos_selecionados=set(ids_servicos), empresa=dados_empresa())
        cursor = db.execute(
            'INSERT INTO profissionais (nome, especialidade, foto, ativo, senha) VALUES (?, ?, ?, ?, ?)',
            (nome, especialidade, foto, ativo, generate_password_hash(senha) if senha else None)
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
    return render_template('admin/profissional_form.html', profissional=None, form=None, servicos=servicos, servicos_selecionados=set(), empresa=dados_empresa())


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
        nome, especialidade, foto, ativo, senha, erro = _parse_profissional_form()
        ids_servicos = request.form.getlist('servicos_ids')
        if erro:
            return render_template('admin/profissional_form.html', profissional=profissional, form=request.form, erro=erro, servicos=servicos, servicos_selecionados=set(ids_servicos), empresa=dados_empresa())
        if senha:
            db.execute(
                'UPDATE profissionais SET nome = ?, especialidade = ?, foto = ?, ativo = ?, senha = ? WHERE id = ?',
                (nome, especialidade, foto, ativo, generate_password_hash(senha), id)
            )
        else:
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
    return render_template('admin/profissional_form.html', profissional=profissional, form=None, servicos=servicos, servicos_selecionados=vinculadas_atual, empresa=dados_empresa())


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
    return render_template('admin/clientes.html', clientes=lista, busca=busca, empresa=dados_empresa())


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
    return render_template('admin/cliente_detalhe.html', cliente=cliente, agendamentos=agendamentos, empresa=dados_empresa())


@admin.route('/agendamento/<int:id>/arquivar', methods=['POST'])
def agendamento_arquivar(id):
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    hoje = date.today().isoformat()
    cur = db.execute(
        """UPDATE agendamentos
              SET arquivado = 1
            WHERE id = ?
              AND status = 'confirmado'
              AND data < ?
              AND arquivado = 0""",
        (id, hoje)
    )
    db.commit()
    if cur.rowcount:
        flash('Atendimento movido para o histórico.', 'success')
    else:
        flash('Esse atendimento não pode ser arquivado (precisa estar confirmado e com data passada).', 'error')
    return redirect(url_for('admin.dashboard'))


@admin.route('/agendamentos/arquivar-completos', methods=['POST'])
def agendamentos_arquivar_completos():
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    hoje = date.today().isoformat()
    cur = db.execute(
        """UPDATE agendamentos
              SET arquivado = 1
            WHERE status = 'confirmado'
              AND data < ?
              AND arquivado = 0""",
        (hoje,)
    )
    db.commit()
    if cur.rowcount:
        flash(f'{cur.rowcount} atendimento(s) movido(s) para o histórico.', 'success')
    else:
        flash('Nenhum atendimento completo para arquivar.', 'info')
    return redirect(url_for('admin.dashboard'))


@admin.route('/historico')
def historico():
    if not esta_logado():
        return redirect(url_for('admin.login'))
    filtro_data_inicio = request.args.get('data_inicio', '').strip()
    filtro_data_fim = request.args.get('data_fim', '').strip()
    filtro_profissional = request.args.get('profissional_id', '').strip()
    filtro_q = request.args.get('q', '').strip()
    try:
        pagina = max(1, int(request.args.get('pagina', '1')))
    except ValueError:
        pagina = 1
    por_pagina = 20
    where = ['a.arquivado = 1']
    params = []
    if filtro_data_inicio:
        where.append('a.data >= ?')
        params.append(filtro_data_inicio)
    if filtro_data_fim:
        where.append('a.data <= ?')
        params.append(filtro_data_fim)
    if filtro_profissional:
        where.append('a.profissional_id = ?')
        params.append(filtro_profissional)
    if filtro_q:
        where.append('(c.nome LIKE ? OR c.telefone LIKE ?)')
        like = f'%{filtro_q}%'
        params.extend([like, like])
    where_sql = ' WHERE ' + ' AND '.join(where)
    db = get_db()
    total = db.execute(
        f"""SELECT COUNT(*) AS n
              FROM agendamentos a
              JOIN clientes c ON c.id = a.cliente_id
            {where_sql}""",
        params
    ).fetchone()['n']
    offset = (pagina - 1) * por_pagina
    rows = db.execute(
        f"""SELECT a.id, a.data, a.horario, a.status,
                   c.nome AS cliente_nome, c.telefone,
                   s.nome AS servico_nome, s.preco, s.duracao_min,
                   p.nome AS profissional_nome
              FROM agendamentos a
              JOIN clientes c ON c.id = a.cliente_id
              JOIN servicos s ON s.id = a.servico_id
              JOIN profissionais p ON p.id = a.profissional_id
            {where_sql}
            ORDER BY a.data DESC, a.horario DESC
            LIMIT ? OFFSET ?""",
        params + [por_pagina, offset]
    ).fetchall()
    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)
    profissionais = buscar_profissionais(False)
    return render_template('admin/historico.html',
                           agendamentos=rows, profissionais=profissionais,
                           filtro_data_inicio=filtro_data_inicio, filtro_data_fim=filtro_data_fim,
                           filtro_profissional=filtro_profissional, filtro_q=filtro_q,
                           pagina=pagina, total_paginas=total_paginas, total=total,
                           empresa=dados_empresa())


@admin.route('/agendamento/<int:id>/restaurar', methods=['POST'])
def agendamento_restaurar(id):
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    db.execute('UPDATE agendamentos SET arquivado = 0 WHERE id = ?', (id,))
    db.commit()
    flash('Atendimento restaurado para o dashboard.', 'success')
    return redirect(url_for('admin.historico'))


@admin.route('/configuracoes', methods=['GET', 'POST'])
def configuracoes():
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    if request.method == 'POST':
        novas = {
            'fonte': request.form.get('fonte', '').strip() or 'Arial, Helvetica, sans-serif',
            'cor_texto': request.form.get('cor_texto', '').strip() or '#3f2d25',
            'cor_fundo': request.form.get('cor_fundo', '').strip() or '#efe0d1',
            'cor_destaque': request.form.get('cor_destaque', '').strip() or '#6f4f3f',
        }
        for chave, valor in novas.items():
            db.execute(
                'INSERT INTO configuracoes (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor',
                (chave, valor)
            )
        for pagina, info in APARENCIA_PAGINAS.items():
            for area, dados in info['areas'].items():
                for prop in dados['props']:
                    base = pagina + '__' + area + '__' + prop
                    chave = 'aparencia.' + pagina + '.' + area + '.' + prop
                    if request.form.get('usar__' + base) == 'on':
                        valor = request.form.get('cor__' + base, '').strip()
                        if cor_valida(valor):
                            db.execute(
                                'INSERT INTO configuracoes (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor',
                                (chave, valor)
                            )
                    else:
                        db.execute('DELETE FROM configuracoes WHERE chave = ?', (chave,))
        db.commit()
        flash('Configurações visuais atualizadas.', 'success')
        return redirect(url_for('admin.configuracoes'))
    config = carregar_configuracoes_visuais()
    aparencia_valores = carregar_aparencia()
    return render_template(
        'admin/configuracoes.html',
        config=config,
        empresa=dados_empresa(),
        aparencia_paginas=APARENCIA_PAGINAS,
        aparencia_valores=aparencia_valores,
        prop_rotulo=PROP_ROTULO,
        prop_padrao=PROP_PADRAO,
    )


@admin.route('/conteudo', methods=['GET', 'POST'])
def conteudo():
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    if request.method == 'POST':
        for _grupo, campos in TEXTOS_CAMPOS:
            for chave, _rotulo, _padrao, _tipo in campos:
                valor = request.form.get(chave, '').strip()
                if valor:
                    db.execute(
                        'INSERT INTO configuracoes (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor',
                        (chave, valor)
                    )
                else:
                    db.execute('DELETE FROM configuracoes WHERE chave = ?', (chave,))
        db.commit()
        flash('Textos e informações do site atualizados.', 'success')
        return redirect(url_for('admin.conteudo'))
    valores = carregar_textos()
    return render_template('admin/conteudo.html', grupos=TEXTOS_CAMPOS, valores=valores, empresa=dados_empresa())


@admin.route('/fotos')
def gerenciar_fotos():
    if not esta_logado():
        return redirect(url_for('admin.login'))
    locais = {}
    for chave, info in FOTOS_LOCAIS.items():
        locais[chave] = {'info': info, 'fotos': buscar_fotos(chave)}
    return render_template('admin/fotos.html', locais=locais, empresa=dados_empresa())


@admin.route('/fotos/<local>/adicionar', methods=['POST'])
def adicionar_foto(local):
    if not esta_logado():
        return redirect(url_for('admin.login'))
    if local not in FOTOS_LOCAIS:
        flash('Local de foto inválido.', 'error')
        return redirect(url_for('admin.gerenciar_fotos'))
    db = get_db()
    caminho = salvar_foto_upload(request.files.get('foto'))
    if not caminho:
        flash('Selecione uma imagem válida (png, jpg, jpeg, webp ou gif, até 5 MB).', 'error')
        return redirect(url_for('admin.gerenciar_fotos'))
    titulo = request.form.get('titulo', '').strip()
    if not FOTOS_LOCAIS[local]['multiplas']:
        antigas = buscar_fotos(local)
        for foto in antigas:
            remover_arquivo_foto(foto['arquivo'])
        db.execute('DELETE FROM fotos WHERE local = ?', (local,))
    proxima_ordem = db.execute('SELECT COALESCE(MAX(ordem), 0) + 1 FROM fotos WHERE local = ?', (local,)).fetchone()[0]
    db.execute(
        'INSERT INTO fotos (local, arquivo, titulo, ordem) VALUES (?, ?, ?, ?)',
        (local, caminho, titulo, proxima_ordem)
    )
    db.commit()
    flash('Foto adicionada com sucesso.', 'success')
    return redirect(url_for('admin.gerenciar_fotos'))


@admin.route('/fotos/<int:id>/remover', methods=['POST'])
def remover_foto(id):
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    foto = db.execute('SELECT * FROM fotos WHERE id = ?', (id,)).fetchone()
    if foto is None:
        flash('Foto não encontrada.', 'error')
        return redirect(url_for('admin.gerenciar_fotos'))
    remover_arquivo_foto(foto['arquivo'])
    db.execute('DELETE FROM fotos WHERE id = ?', (id,))
    db.commit()
    flash('Foto removida.', 'success')
    return redirect(url_for('admin.gerenciar_fotos'))


@admin.route('/fotos/<int:id>/mover', methods=['POST'])
def mover_foto(id):
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    foto = db.execute('SELECT * FROM fotos WHERE id = ?', (id,)).fetchone()
    if foto is None:
        return redirect(url_for('admin.gerenciar_fotos'))
    direcao = request.form.get('direcao', '')
    if direcao == 'subir':
        vizinha = db.execute(
            'SELECT * FROM fotos WHERE local = ? AND (ordem < ? OR (ordem = ? AND id < ?)) ORDER BY ordem DESC, id DESC LIMIT 1',
            (foto['local'], foto['ordem'], foto['ordem'], foto['id'])
        ).fetchone()
    else:
        vizinha = db.execute(
            'SELECT * FROM fotos WHERE local = ? AND (ordem > ? OR (ordem = ? AND id > ?)) ORDER BY ordem ASC, id ASC LIMIT 1',
            (foto['local'], foto['ordem'], foto['ordem'], foto['id'])
        ).fetchone()
    if vizinha is not None:
        db.execute('UPDATE fotos SET ordem = ? WHERE id = ?', (vizinha['ordem'], foto['id']))
        db.execute('UPDATE fotos SET ordem = ? WHERE id = ?', (foto['ordem'], vizinha['id']))
        db.commit()
    return redirect(url_for('admin.gerenciar_fotos'))


@admin.route('/redefinir/<aba>', methods=['POST'])
def redefinir_padrao(aba):
    if not esta_logado():
        return redirect(url_for('admin.login'))
    db = get_db()
    if aba == 'aparencia':
        padroes = {
            'fonte': 'Arial, Helvetica, sans-serif',
            'cor_texto': '#3f2d25',
            'cor_fundo': '#efe0d1',
            'cor_destaque': '#6f4f3f',
        }
        for chave, valor in padroes.items():
            db.execute(
                'INSERT INTO configuracoes (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor',
                (chave, valor)
            )
        db.execute("DELETE FROM configuracoes WHERE chave LIKE 'aparencia.%'")
        db.commit()
        flash('Aparência redefinida para os valores padrão.', 'success')
        return redirect(url_for('admin.configuracoes'))
    elif aba == 'fotos':
        fotos_atuais = db.execute('SELECT arquivo FROM fotos').fetchall()
        for foto in fotos_atuais:
            remover_arquivo_foto(foto['arquivo'])
        db.execute('DELETE FROM fotos')
        db.executemany(
            'INSERT INTO fotos (local, arquivo, titulo, ordem) VALUES (?, ?, ?, ?)',
            FOTOS_INICIAIS
        )
        db.commit()
        flash('Fotos redefinidas para as imagens padrão.', 'success')
        return redirect(url_for('admin.gerenciar_fotos'))
    elif aba == 'texto':
        db.execute("DELETE FROM configuracoes WHERE chave LIKE 'texto.%' OR chave LIKE 'empresa.%'")
        db.commit()
        flash('Textos redefinidos para os valores padrão.', 'success')
        return redirect(url_for('admin.conteudo'))
    else:
        flash('Aba inválida.', 'error')
        return redirect(url_for('admin.dashboard'))


@profissional.route('/login', methods=['GET', 'POST'])
def login_profissional():
    db = get_db()
    profissionais_lista = db.execute('SELECT id, nome FROM profissionais WHERE ativo = 1 AND senha IS NOT NULL AND senha != "" ORDER BY nome').fetchall()
    if request.method == 'POST':
        profissional_id = request.form.get('profissional_id', '').strip()
        senha = request.form.get('senha', '')
        if profissional_id and senha:
            linha = db.execute('SELECT * FROM profissionais WHERE id = ? AND ativo = 1', (profissional_id,)).fetchone()
            if linha and linha['senha'] and check_password_hash(linha['senha'], senha):
                session.clear()
                session['profissional_id'] = linha['id']
                return redirect(url_for('profissional.agenda_profissional'))
        return render_template('profissional/login.html', profissionais=profissionais_lista, erro='Profissional ou senha inválida.', empresa=dados_empresa())
    return render_template('profissional/login.html', profissionais=profissionais_lista, erro=None, empresa=dados_empresa())


@profissional.route('/logout')
def logout_profissional():
    session.pop('profissional_id', None)
    return redirect(url_for('profissional.login_profissional'))


@profissional.route('/agenda')
def agenda_profissional():
    prof = buscar_profissional_logada()
    if not prof:
        return redirect(url_for('profissional.login_profissional'))
    return render_template('profissional/agenda.html', profissional=prof, empresa=dados_empresa())


@profissional.route('/agenda/dia')
def agenda_profissional_dia():
    prof = buscar_profissional_logada()
    if not prof:
        return jsonify({'erro': 'nao_autenticado'}), 401
    data_texto = request.args.get('data', '').strip()
    if not data_texto:
        return jsonify({'data': data_texto, 'horarios': []})
    aberto = dia_funciona(data_texto)
    db = get_db()
    sql = '''SELECT a.id, a.horario, a.status,
                    c.nome AS cliente_nome, c.telefone,
                    s.nome AS servico_nome, s.preco, s.duracao_min
             FROM agendamentos a
             JOIN clientes c ON c.id = a.cliente_id
             JOIN servicos s ON s.id = a.servico_id
             WHERE a.data = ? AND a.profissional_id = ? AND a.status != ?'''
    linhas = db.execute(sql, (data_texto, prof['id'], 'cancelado')).fetchall()
    ocupados = {linha['horario']: linha for linha in linhas}
    bloqueios = buscar_bloqueios(data_texto, str(prof['id']))
    bloqueios_horarios = {b['horario']: b for b in bloqueios}
    dia_bloqueado_inteiro = '' in bloqueios_horarios
    resposta = []
    for horario in HORARIOS:
        ocupado = ocupados.get(horario)
        slot = {
            'horario': horario,
            'aberto': aberto and not dia_bloqueado_inteiro,
            'bloqueado': horario in bloqueios_horarios or dia_bloqueado_inteiro,
            'agendamento': None,
        }
        if ocupado:
            slot['agendamento'] = {
                'id': ocupado['id'],
                'cliente_nome': ocupado['cliente_nome'],
                'telefone': ocupado['telefone'],
                'servico_nome': ocupado['servico_nome'],
                'preco': float(ocupado['preco']),
                'duracao_min': ocupado['duracao_min'],
                'status': ocupado['status'],
            }
        resposta.append(slot)
    return jsonify({'data': data_texto, 'aberto': aberto, 'horarios': resposta})


@profissional.route('/disponibilidade-mes')
def profissional_disponibilidade_mes():
    prof = buscar_profissional_logada()
    if not prof:
        return jsonify({'erro': 'nao_autenticado'}), 401
    try:
        ano = int(request.args.get('ano', date.today().year))
        mes = int(request.args.get('mes', date.today().month))
    except (ValueError, TypeError):
        return jsonify({'erro': 'parametros invalidos'}), 400
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    resposta = {}
    for dia in range(1, ultimo_dia + 1):
        data_texto = f'{ano:04d}-{mes:02d}-{dia:02d}'
        aberto = dia_funciona(data_texto)
        livres = contar_horarios_disponiveis(data_texto, str(prof['id'])) if aberto else 0
        resposta[data_texto] = {'aberto': aberto, 'livres': livres, 'total': len(HORARIOS)}
    return jsonify(resposta)


@profissional.route('/bloqueios', methods=['GET', 'POST'])
def bloqueios_profissional():
    prof = buscar_profissional_logada()
    if not prof:
        return redirect(url_for('profissional.login_profissional'))
    db = get_db()
    if request.method == 'POST':
        data_texto = request.form.get('data', '').strip()
        horario = request.form.get('horario', '').strip()
        motivo = request.form.get('motivo', '').strip()
        if not data_texto:
            flash('Informe a data que você não vai poder comparecer.', 'error')
        else:
            horario_salvo = '' if (horario == 'dia_inteiro' or horario == '') else horario
            motivo_salvo = motivo if motivo else 'Indisponibilidade'
            db.execute(
                'INSERT INTO bloqueios_agenda (profissional_id, data, horario, motivo) VALUES (?, ?, ?, ?)',
                (prof['id'], data_texto, horario_salvo, motivo_salvo)
            )
            db.commit()
            flash('Bloqueio cadastrado com sucesso.', 'success')
        return redirect(url_for('profissional.bloqueios_profissional'))
    lista = db.execute(
        '''SELECT id, data, horario, motivo
             FROM bloqueios_agenda
            WHERE profissional_id = ?
            ORDER BY data DESC, horario''',
        (prof['id'],)
    ).fetchall()
    return render_template('profissional/bloqueios.html', profissional=prof, bloqueios=lista, horarios=HORARIOS, empresa=dados_empresa())


@profissional.route('/bloqueios/<int:bid>/excluir', methods=['POST'])
def bloqueio_profissional_excluir(bid):
    prof = buscar_profissional_logada()
    if not prof:
        return redirect(url_for('profissional.login_profissional'))
    db = get_db()
    db.execute('DELETE FROM bloqueios_agenda WHERE id = ? AND profissional_id = ?', (bid, prof['id']))
    db.commit()
    flash('Bloqueio removido.', 'success')
    return redirect(url_for('profissional.bloqueios_profissional'))


app.register_blueprint(publico)

app.register_blueprint(admin)

app.register_blueprint(profissional)

@app.teardown_appcontext
def close_db(e=None):
    from flask import g
    db = g.pop('db', None)
    if db is not None:
        db.close()


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_DEBUG', 'False') == 'True')
