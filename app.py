from flask import Flask, Blueprint, render_template, request, redirect, url_for, jsonify, session, flash
# Importa do Flask as ferramentas usadas para criar o site, rotas, páginas HTML, formulários, JSON, sessão e mensagens.

from database import init_db, get_db
# Importa do arquivo database.py as funções responsáveis por criar e acessar o banco SQLite.

from datetime import date, datetime, timedelta
# Importa date para validar dias de funcionamento, datetime para combinar dia/horário e timedelta para janelas no dashboard.

import calendar
# Importa calendar para descobrir quantos dias existem em cada mês.

import os
# Importa os para montar caminhos de pastas e salvar as fotos enviadas pelo admin.

import re
# Importa re para validar se uma cor enviada está no formato hexadecimal seguro.

import uuid
# Importa uuid para gerar nomes únicos de arquivo e evitar que uploads se sobrescrevam.

from werkzeug.utils import secure_filename
# Importa secure_filename para limpar o nome dos arquivos enviados e evitar caminhos maliciosos.

app = Flask(__name__)
# Cria a aplicação Flask, que funciona como o servidor principal do projeto.

app.config['SECRET_KEY'] = 'esmalteria-secret-key'
# Define uma chave secreta para proteger a sessão de login do painel administrativo.

app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
# Limita o tamanho de cada upload a 5 MB para evitar arquivos gigantes.

PASTA_UPLOAD = os.path.join(app.static_folder, 'img', 'uploads')
# Define a pasta onde as fotos enviadas pelo admin serão salvas (static/img/uploads).

EXTENSOES_IMAGEM = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
# Define quais extensões de imagem são aceitas no upload.

publico = Blueprint('publico', __name__)
# Cria o grupo de rotas públicas, usadas pelas clientes no site.

admin = Blueprint('admin', __name__, url_prefix='/admin')
# Cria o grupo de rotas administrativas, todas começando com /admin.

profissional = Blueprint('profissional', __name__, url_prefix='/profissional')
# Cria o grupo de rotas restritas para as profissionais não-admin.


@app.context_processor
def injetar_configuracoes():
    # Disponibiliza as configurações visuais para qualquer template renderizado.
    try:
        # Protege contra falhas em rotas que rodam antes do banco existir.
        return {
            # Devolve as preferências visuais e os dados de aparência para o template usar.
            'config_visual': carregar_configuracoes_visuais(),
            # Dicionário com fonte e cores globais (compatível com o que já existia).
            'css_aparencia': gerar_css_aparencia(),
            # Bloco de CSS gerado a partir das cores por página/área escolhidas no admin.
            'pagina_atual': pagina_atual(),
            # Nome curto da página atual, usado para aplicar as cores só na página certa.
            'textos': carregar_textos(),
            # Textos editáveis do site (títulos, parágrafos) já com os padrões aplicados.
            'existe_profissional_com_senha': existe_profissional_com_senha(),
            # Controla se o link da área da profissional aparece no rodapé.
        }
    except Exception:
        # Em caso de erro (banco indisponível), devolve valores vazios e seguros.
        return {'config_visual': {}, 'css_aparencia': '', 'pagina_atual': '', 'textos': TEXTOS_PADRAO, 'existe_profissional_com_senha': False}
        # Templates ficam usando os defaults do próprio CSS e os textos padrão.


EMPRESA = {
    # Cria um dicionário com as informações padrão da empresa (podem ser editadas pelo admin e gravadas no banco).
    'nome': 'Refúgio da Preta',
    # Define o nome da empresa que aparece no site.
    'marca_subtitulo': 'Studio de manicure e beleza',
    # Define o subtítulo que aparece acima do nome no topo do site.
    'dona': 'Pamela Francisco',
    # Define o nome da dona/profissional principal.
    'telefone': '(11) 99220-4706',
    # Define o telefone de contato da empresa.
    'atendimento': 'Atendimento a domicílio e na residência da profissional',
    # Substitui o antigo endereço fixo: agora o atendimento é a domicílio ou na casa da profissional, sem endereço público.
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


TEXTOS_CAMPOS = [
    # Define os textos editáveis do site, agrupados por seção (chave, rótulo, valor padrão, tipo do campo).
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
# Fecha a lista de textos editáveis.

TEXTOS_PADRAO = {chave: padrao for _grupo, campos in TEXTOS_CAMPOS for chave, _rotulo, padrao, _tipo in campos}
# Cria um dicionário simples chave->valor padrão para uso rápido.


def carregar_textos():
    # Lê os textos salvos no banco e completa com os padrões, devolvendo tudo pronto para os templates.
    db = get_db()
    # Abre o banco.
    salvos = {linha['chave']: linha['valor'] for linha in db.execute("SELECT chave, valor FROM configuracoes WHERE chave LIKE 'texto.%' OR chave LIKE 'empresa.%'").fetchall()}
    # Busca o que já foi personalizado (textos e dados da empresa).
    completo = dict(TEXTOS_PADRAO)
    # Começa com todos os valores padrão.
    completo.update({c: v for c, v in salvos.items() if v})
    # Sobrescreve com os valores personalizados que não estão vazios.
    return completo
    # Devolve os textos prontos (chave -> valor).


def dados_empresa():
    # Monta as informações da empresa juntando os padrões com o que foi personalizado no admin.
    dados = dict(EMPRESA)
    # Começa com os valores padrão.
    try:
        # Protege contra banco indisponível.
        db = get_db()
        # Abre o banco.
        linhas = db.execute("SELECT chave, valor FROM configuracoes WHERE chave LIKE 'empresa.%'").fetchall()
        # Busca as informações personalizadas da empresa.
        for linha in linhas:
            # Percorre cada personalização.
            if linha['valor']:
                # Só usa quando há valor preenchido.
                dados[linha['chave'].split('.', 1)[1]] = linha['valor']
                # Substitui o valor padrão pelo personalizado (campo depois de 'empresa.').
    except Exception:
        # Em caso de erro, mantém apenas os padrões.
        pass
        # Não interrompe a renderização.
    return dados
    # Devolve o dicionário final da empresa.


def existe_profissional_com_senha():
    # Verifica se há alguma profissional ativa com senha definida (controla a exibição do link da área restrita).
    try:
        # Protege contra banco indisponível.
        db = get_db()
        # Abre o banco.
        total = db.execute("SELECT COUNT(*) FROM profissionais WHERE ativo = 1 AND senha IS NOT NULL AND senha != ''").fetchone()[0]
        # Conta profissionais ativas que já têm senha.
        return total > 0
        # Retorna True quando existe ao menos uma.
    except Exception:
        # Em caso de erro, esconde o link por segurança.
        return False
        # Não mostra o acesso da profissional.


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


def profissional_logada_id():
    # Retorna o id da profissional logada na área restrita, ou None se não houver sessão.
    return session.get('profissional_id')
    # A chave profissional_id só é setada pela rota /profissional/login.


def buscar_profissional_logada():
    # Carrega os dados completos da profissional atualmente logada.
    pid = profissional_logada_id()
    # Pega o id da sessão.
    if not pid:
        # Sem id, não há profissional logada.
        return None
    db = get_db()
    # Abre o banco.
    return db.execute('SELECT * FROM profissionais WHERE id = ?', (pid,)).fetchone()
    # Retorna a linha da profissional ou None se ela tiver sido removida.


def carregar_configuracoes_visuais():
    # Lê todas as preferências visuais salvas no banco como dicionário.
    db = get_db()
    # Abre o banco.
    linhas = db.execute('SELECT chave, valor FROM configuracoes').fetchall()
    # Busca todas as preferências cadastradas.
    return {linha['chave']: linha['valor'] for linha in linhas}
    # Converte para dicionário simples para o template usar.


PROP_CSS = {
    # Liga cada propriedade editável à propriedade CSS correspondente.
    'cor_fundo': 'background-color',
    # cor_fundo vira a cor de fundo do elemento.
    'cor_texto': 'color',
    # cor_texto vira a cor do texto do elemento.
}
# Fecha o mapa de propriedade para CSS.

PROP_ROTULO = {
    # Define o rótulo amigável de cada propriedade para mostrar no painel admin.
    'cor_fundo': 'Cor de fundo',
    # Texto exibido ao lado do seletor de cor de fundo.
    'cor_texto': 'Cor do texto',
    # Texto exibido ao lado do seletor de cor de texto.
}
# Fecha o mapa de rótulos das propriedades.

PROP_PADRAO = {
    # Define um valor inicial sugerido para cada propriedade no seletor de cor.
    'cor_fundo': '#efe0d1',
    # Bege padrão do tema como ponto de partida do seletor de fundo.
    'cor_texto': '#3f2d25',
    # Marrom escuro padrão do tema como ponto de partida do seletor de texto.
}
# Fecha o mapa de cores padrão.

APARENCIA_PAGINAS = {
    # Define quais páginas e áreas do site a Pamela pode personalizar (seleção de página -> área -> cores).
    'global': {
        # Grupo de áreas que valem para o site inteiro, em qualquer página.
        'rotulo': 'Geral (todas as páginas)',
        # Nome do grupo mostrado no seletor de página.
        'escopo': None,
        # escopo None significa que as cores valem em todas as páginas.
        'areas': {
            # Áreas globais editáveis.
            'corpo': {'rotulo': 'Fundo e texto gerais', 'seletor': 'body', 'props': ['cor_fundo', 'cor_texto']},
            # Fundo e texto padrão de todo o site.
            'topo': {'rotulo': 'Topo / cabeçalho', 'seletor': '.topo', 'props': ['cor_fundo', 'cor_texto']},
            # Cabeçalho fixo no topo do site.
            'rodape': {'rotulo': 'Rodapé', 'seletor': '.rodape', 'props': ['cor_fundo', 'cor_texto']},
            # Rodapé com contato e informações.
            'botoes': {'rotulo': 'Botões e destaques', 'seletor': '.botao, .botao-principal, .botao-destaque, .nav-destaque, button[type="submit"]', 'props': ['cor_fundo', 'cor_texto']},
            # Botões principais e elementos de destaque.
        },
    },
    'inicio': {
        # Áreas exclusivas da página inicial.
        'rotulo': 'Página Início',
        # Nome amigável da página.
        'escopo': 'inicio',
        # escopo 'inicio' faz as cores valerem só na página inicial.
        'areas': {
            # Áreas editáveis da página inicial.
            'hero': {'rotulo': 'Destaque principal (topo da página)', 'seletor': '.hero', 'props': ['cor_fundo', 'cor_texto']},
            # Seção de abertura com o nome e os botões.
            'chamada': {'rotulo': 'Chamada de agendamento', 'seletor': '.chamada-agendamento', 'props': ['cor_fundo', 'cor_texto']},
            # Faixa que reforça o agendamento.
            'servicos': {'rotulo': 'Seção de serviços', 'seletor': '#servicos', 'props': ['cor_fundo', 'cor_texto']},
            # Lista de serviços oferecidos.
            'galeria': {'rotulo': 'Seção da galeria', 'seletor': '#galeria', 'props': ['cor_fundo', 'cor_texto']},
            # Galeria de trabalhos (carrossel).
            'responsavel': {'rotulo': 'Seção da responsável', 'seletor': '#dona', 'props': ['cor_fundo', 'cor_texto']},
            # Bloco que apresenta a Pamela.
        },
    },
    'agendamento': {
        # Área da página de agendamento.
        'rotulo': 'Página de Agendamento',
        # Nome amigável da página.
        'escopo': 'agendamento',
        # escopo 'agendamento' aplica as cores só na página de agendamento.
        'areas': {
            # Áreas editáveis do agendamento.
            'conteudo': {'rotulo': 'Fundo do conteúdo', 'seletor': 'main', 'props': ['cor_fundo', 'cor_texto']},
            # Área principal onde fica o formulário de agendamento.
        },
    },
}
# Fecha o mapa de páginas/áreas editáveis.

FOTOS_LOCAIS = {
    # Define os locais de fotos que o admin pode gerenciar e se aceitam várias fotos (carrossel).
    'galeria': {'rotulo': 'Galeria de trabalhos (página inicial)', 'multiplas': True},
    # A galeria aceita várias fotos e vira um carrossel com adicionar/remover.
    'responsavel': {'rotulo': 'Foto da responsável (Pamela)', 'multiplas': False},
    # A foto da responsável é única e apenas substituída.
}
# Fecha o mapa de locais de fotos.


def cor_valida(valor):
    # Verifica se a cor está no formato hexadecimal seguro (#rgb ou #rrggbb) antes de salvar/usar no CSS.
    return bool(valor) and bool(re.fullmatch(r'#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?', valor))
    # Retorna True só para valores como #fff ou #6f4f3f, evitando injeção de CSS.


def carregar_aparencia():
    # Lê do banco apenas as preferências de aparência por página/área (chaves que começam com 'aparencia.').
    db = get_db()
    # Abre o banco.
    linhas = db.execute("SELECT chave, valor FROM configuracoes WHERE chave LIKE 'aparencia.%'").fetchall()
    # Busca só as chaves de aparência por área.
    return {linha['chave']: linha['valor'] for linha in linhas}
    # Devolve um dicionário chave->cor para o template e o gerador de CSS usarem.


def gerar_css_aparencia():
    # Monta o bloco de CSS final a partir das cores escolhidas para cada página/área.
    valores = carregar_aparencia()
    # Carrega as cores salvas.
    regras = []
    # Lista que vai acumular as regras CSS.
    for pagina, info in APARENCIA_PAGINAS.items():
        # Percorre cada página configurável.
        escopo = info.get('escopo')
        # Descobre se as cores valem só em uma página.
        prefixo = '.pagina-' + escopo + ' ' if escopo else ''
        # Quando há escopo, prefixa o seletor com a classe da página (aplicada no body).
        for area, dados in info['areas'].items():
            # Percorre cada área da página.
            declaracoes = []
            # Lista de declarações CSS daquela área.
            for prop in dados['props']:
                # Percorre cada propriedade editável da área.
                valor = valores.get('aparencia.' + pagina + '.' + area + '.' + prop)
                # Busca a cor salva para essa página/área/propriedade.
                if cor_valida(valor):
                    # Só usa o valor se for uma cor hexadecimal válida.
                    declaracoes.append(PROP_CSS[prop] + ': ' + valor + ';')
                    # Adiciona a declaração CSS correspondente.
            if declaracoes:
                # Se a área tem ao menos uma cor personalizada, gera a regra.
                regras.append(prefixo + dados['seletor'] + ' { ' + ' '.join(declaracoes) + ' }')
                # Junta seletor + declarações em uma regra CSS.
    return '\n'.join(regras)
    # Devolve o CSS completo (string vazia se nada foi personalizado).


def pagina_atual():
    # Descobre um nome curto da página atual para aplicar as cores certas no body.
    endpoint = request.endpoint or ''
    # Lê o endpoint da rota atual (ex: 'publico.index').
    if endpoint == 'publico.index':
        # Página inicial.
        return 'inicio'
    if endpoint.startswith('publico.agendar'):
        # Qualquer etapa do agendamento.
        return 'agendamento'
    if endpoint == 'publico.confirmacao':
        # Página de confirmação.
        return 'confirmacao'
    return ''
    # Demais páginas não recebem escopo específico.


def buscar_fotos(local):
    # Busca as fotos de um local específico já na ordem de exibição.
    db = get_db()
    # Abre o banco.
    return db.execute('SELECT * FROM fotos WHERE local = ? ORDER BY ordem, id', (local,)).fetchall()
    # Retorna a lista de fotos ordenada por ordem e depois id.


def extensao_permitida(nome_arquivo):
    # Confere se o arquivo enviado tem uma extensão de imagem aceita.
    return '.' in nome_arquivo and nome_arquivo.rsplit('.', 1)[1].lower() in EXTENSOES_IMAGEM
    # Retorna True apenas para png, jpg, jpeg, webp ou gif.


def salvar_foto_upload(arquivo):
    # Salva uma foto enviada pelo formulário e devolve o caminho relativo a static/img.
    if not arquivo or arquivo.filename == '':
        # Sai cedo se nenhum arquivo foi enviado.
        return None
        # Sem arquivo, não há o que salvar.
    if not extensao_permitida(arquivo.filename):
        # Recusa arquivos que não sejam imagens permitidas.
        return None
        # Retorna None para o chamador mostrar erro.
    os.makedirs(PASTA_UPLOAD, exist_ok=True)
    # Garante que a pasta de uploads exista.
    extensao = arquivo.filename.rsplit('.', 1)[1].lower()
    # Pega a extensão original do arquivo.
    base = secure_filename(arquivo.filename.rsplit('.', 1)[0]) or 'foto'
    # Limpa o nome base do arquivo, usando 'foto' como reserva.
    nome_final = base + '_' + uuid.uuid4().hex[:8] + '.' + extensao
    # Monta um nome único para não sobrescrever outras fotos.
    arquivo.save(os.path.join(PASTA_UPLOAD, nome_final))
    # Salva o arquivo dentro de static/img/uploads.
    return 'uploads/' + nome_final
    # Devolve o caminho relativo usado nos templates (img/ + este valor).


def remover_arquivo_foto(caminho):
    # Apaga do disco apenas arquivos que foram enviados pelo admin (pasta uploads), preservando as imagens originais do projeto.
    if not caminho or not caminho.startswith('uploads/'):
        # Não apaga imagens originais (ex: trabalho1.png) que são compartilhadas e versionadas.
        return
        # Sai sem fazer nada.
    caminho_completo = os.path.join(app.static_folder, 'img', caminho)
    # Monta o caminho absoluto do arquivo enviado.
    try:
        # Protege contra arquivo já inexistente.
        os.remove(caminho_completo)
        # Remove o arquivo do disco.
    except OSError:
        # Ignora erros (arquivo ausente, permissão), pois a remoção do banco é o que importa.
        pass
        # Não interrompe o fluxo do admin.


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
    galeria = buscar_fotos('galeria')
    # Busca as fotos da galeria no banco (gerenciadas pelo admin) para montar o carrossel.
    fotos_responsavel = buscar_fotos('responsavel')
    # Busca a foto da responsável cadastrada pelo admin.
    foto_dona = fotos_responsavel[0]['arquivo'] if fotos_responsavel else EMPRESA['foto_dona']
    # Usa a foto cadastrada ou cai no arquivo padrão caso ainda não haja nenhuma.
    return render_template('index.html', servicos=servicos, empresa=dados_empresa(), galeria=galeria, foto_dona=foto_dona)
    # Abre o template index.html e envia serviços, empresa, galeria e a foto da responsável para o HTML.


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
    return render_template('agendamento.html', servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, empresa=dados_empresa(), horarios=HORARIOS, horarios_ocupados=[], dados=dados, erro=None)
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
        return render_template('agendamento.html', servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, empresa=dados_empresa(), horarios=HORARIOS, horarios_ocupados=horarios_ocupados, dados=dados, erro=msg)
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
    return render_template('confirmacao.html', empresa=dados_empresa())
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
        return render_template('admin/login.html', erro='Usuário ou senha inválidos.', empresa=dados_empresa())
        # Reabre o login com erro se os dados estiverem incorretos.
    return render_template('admin/login.html', empresa=dados_empresa())
    # Mostra o formulário de login.


@admin.route('/logout')
# Cria a rota para sair do painel.
def logout():
    # Define a função de logout.
    session.clear()
    # Limpa os dados de sessão.
    return redirect(url_for('admin.login'))
    # Volta para a tela de login.


@admin.route('/agenda')
# Cria a rota da agenda do admin com fluxo de pop-ups (profissional, calendário, lista de horários).
def agenda():
    # Define a função que mostra a agenda das profissionais.
    if not esta_logado():
        # Bloqueia acesso sem login.
        return redirect(url_for('admin.login'))
        # Envia para o login quando não há sessão.
    profissionais = buscar_profissionais(False)
    # Busca todas as profissionais (inclusive inativas) para o admin escolher.
    return render_template('admin/agenda.html', profissionais=profissionais, empresa=dados_empresa())
    # Renderiza a página de agenda do admin.


@admin.route('/agenda/dia')
# Cria a rota JSON que devolve os horários do dia com dados completos do agendamento.
def agenda_dia():
    # Define a função usada pelo JavaScript da agenda para listar horários do dia.
    if not esta_logado():
        # Bloqueia consultas sem login válido.
        return jsonify({'erro': 'nao_autenticado'}), 401
        # Devolve 401 quando o admin não está autenticado.
    data_texto = request.args.get('data', '').strip()
    # Recebe a data escolhida no calendário.
    profissional_id = request.args.get('profissional_id', '').strip()
    # Recebe o id da profissional escolhida.
    if not data_texto or not profissional_id:
        # Garante que ambos os parâmetros foram informados.
        return jsonify({'data': data_texto, 'horarios': []})
        # Retorna lista vazia quando algo importante está faltando.
    aberto = dia_funciona(data_texto)
    # Verifica se o dia escolhido tem funcionamento.
    db = get_db()
    # Abre a conexão com o banco.
    sql = '''SELECT a.id, a.horario, a.status,
                    c.nome AS cliente_nome, c.telefone,
                    s.nome AS servico_nome, s.preco, s.duracao_min
             FROM agendamentos a
             JOIN clientes c ON c.id = a.cliente_id
             JOIN servicos s ON s.id = a.servico_id
             WHERE a.data = ? AND a.profissional_id = ? AND a.status != ?'''
    # Busca agendamentos do dia para a profissional, ignorando cancelados.
    linhas = db.execute(sql, (data_texto, profissional_id, 'cancelado')).fetchall()
    # Executa a consulta e guarda as linhas encontradas.
    ocupados = {linha['horario']: linha for linha in linhas}
    # Cria um dicionário pelo horário para localizar o agendamento de cada slot.
    bloqueios = buscar_bloqueios(data_texto, profissional_id)
    # Carrega bloqueios manuais para mostrar slots marcados como folga.
    resposta = []
    # Cria lista para devolver no formato JSON.
    for horario in HORARIOS:
        # Percorre todos os horários padrão do dia.
        ocupado = ocupados.get(horario)
        # Pega o agendamento daquele horário, se existir.
        slot = {'horario': horario, 'aberto': aberto, 'bloqueado': horario in bloqueios, 'agendamento': None}
        # Cria o slot base com informações de funcionamento e bloqueio.
        if ocupado:
            # Verifica se há agendamento naquele horário.
            slot['agendamento'] = {
                'id': ocupado['id'],
                'cliente_nome': ocupado['cliente_nome'],
                'telefone': ocupado['telefone'],
                'servico_nome': ocupado['servico_nome'],
                'preco': float(ocupado['preco']),
                'duracao_min': ocupado['duracao_min'],
                'status': ocupado['status'],
            }
            # Adiciona os dados completos do agendamento ao slot.
        resposta.append(slot)
        # Inclui o slot na resposta.
    return jsonify({'data': data_texto, 'aberto': aberto, 'horarios': resposta})
    # Retorna a agenda do dia em JSON.


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
    where = ['a.arquivado = 0']
    # O dashboard sempre esconde agendamentos arquivados (eles vivem em /admin/historico).
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
    sql += ' WHERE ' + ' AND '.join(where)
    # Junta os filtros na consulta SQL (sempre há pelo menos o filtro de arquivado).
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
    hoje_iso = date.today().isoformat()
    # Captura a data de hoje para liberar o botão "mover para histórico" só nos atendimentos passados.
    tem_completos_para_arquivar = db.execute(
        # Verifica se existe algum confirmado com data anterior a hoje ainda no dashboard.
        "SELECT COUNT(*) AS n FROM agendamentos WHERE arquivado = 0 AND status = 'confirmado' AND data < ?",
        (hoje_iso,)
    ).fetchone()['n'] > 0
    # Guarda como booleano para o template decidir mostrar o aviso/botão em massa.
    return render_template('admin/dashboard.html', agendamentos=agendamentos, profissionais=profissionais, filtro_status=filtro_status, filtro_data=filtro_data, filtro_profissional=filtro_profissional, empresa=dados_empresa(), kpis=kpis, hoje=hoje_iso, tem_completos_para_arquivar=tem_completos_para_arquivar)
    # Renderiza o dashboard com KPIs, lista filtrada e dados auxiliares para o botão de histórico.


def calcular_kpis_dashboard(db):
    # Cria função auxiliar que monta um pequeno painel de números do dia/semana.
    hoje = date.today().isoformat()
    # Pega a data de hoje no formato AAAA-MM-DD para usar nas consultas.
    inicio_semana = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    # Calcula a segunda-feira da semana corrente para servir de janela.
    fim_semana = (date.today() + timedelta(days=6 - date.today().weekday())).isoformat()
    # Calcula o domingo da semana corrente como fim da janela.
    total_hoje = db.execute(
        # Conta quantos agendamentos não cancelados estão marcados para hoje (ignora arquivados).
        "SELECT COUNT(*) AS n FROM agendamentos WHERE data = ? AND status != 'cancelado' AND arquivado = 0",
        (hoje,)
    ).fetchone()['n']
    # Salva o número de atendimentos do dia para o KPI.
    confirmados_hoje = db.execute(
        # Conta apenas os agendamentos de hoje já confirmados (ignora arquivados).
        "SELECT COUNT(*) AS n FROM agendamentos WHERE data = ? AND status = 'confirmado' AND arquivado = 0",
        (hoje,)
    ).fetchone()['n']
    # Salva o número de confirmados.
    pendentes = db.execute(
        # Conta quantos agendamentos futuros ainda estão pendentes (ignora arquivados).
        "SELECT COUNT(*) AS n FROM agendamentos WHERE status = 'pendente' AND data >= ? AND arquivado = 0",
        (hoje,)
    ).fetchone()['n']
    # Salva pendentes para o KPI.
    receita_semana = db.execute(
        # Soma a receita estimada da semana, considerando apenas agendamentos não cancelados e não arquivados.
        """SELECT COALESCE(SUM(s.preco), 0) AS total
           FROM agendamentos a
           JOIN servicos s ON s.id = a.servico_id
           WHERE a.data BETWEEN ? AND ? AND a.status != 'cancelado' AND a.arquivado = 0""",
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
            return render_template('admin/agendamento_form.html', agendamento=agendamento, servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, lista_horarios=lista_horarios, empresa=dados_empresa())
            # Reabre formulário.
        if not profissional_atende_servico(profissional_id, servico_id):
            # Verifica se o serviço e a profissional combinam.
            flash('A profissional escolhida não atende esse serviço.', 'error')
            # Mostra mensagem de erro.
            lista_horarios = montar_lista_horarios(data_texto, profissional_id, ignorar_agendamento_id=id)
            # Recalcula a disponibilidade para devolver ao formulário.
            return render_template('admin/agendamento_form.html', agendamento=agendamento, servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, lista_horarios=lista_horarios, empresa=dados_empresa())
            # Reabre formulário.
        if status != 'cancelado' and conflito_agenda(data_texto, horario, profissional_id, id):
            # Verifica conflito ao remarcar, ignorando o próprio agendamento.
            flash('Este horário está indisponível para a profissional escolhida.', 'error')
            # Mostra erro.
            lista_horarios = montar_lista_horarios(data_texto, profissional_id, ignorar_agendamento_id=id)
            # Recalcula a disponibilidade do horário para mostrar no formulário.
            return render_template('admin/agendamento_form.html', agendamento=agendamento, servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, lista_horarios=lista_horarios, empresa=dados_empresa())
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
    return render_template('admin/agendamento_form.html', agendamento=agendamento, servicos=servicos, profissionais=profissionais, profissionais_servicos=profissionais_servicos, lista_horarios=lista_horarios, empresa=dados_empresa())
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
    return render_template('admin/servicos.html', servicos=lista, empresa=dados_empresa())
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
            return render_template('admin/servico_form.html', servico=None, form=request.form, erro=erro, profissionais=profissionais, profissionais_selecionadas=set(ids_profissionais), empresa=dados_empresa())
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
    return render_template('admin/servico_form.html', servico=None, form=None, profissionais=profissionais, profissionais_selecionadas=set(), empresa=dados_empresa())
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
            return render_template('admin/servico_form.html', servico=servico, form=request.form, erro=erro, profissionais=profissionais, profissionais_selecionadas=set(ids_profissionais), empresa=dados_empresa())
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
    return render_template('admin/servico_form.html', servico=servico, form=None, profissionais=profissionais, profissionais_selecionadas=vinculadas_atual, empresa=dados_empresa())
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
    return render_template('admin/bloqueios.html', bloqueios=bloqueios_lista, profissionais=profissionais, horarios=HORARIOS, empresa=dados_empresa())
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
    return render_template('admin/profissionais.html', profissionais=lista, empresa=dados_empresa())
    # Renderiza a página de profissionais.


def _parse_profissional_form():
    # Cria função auxiliar para ler o formulário de profissional.
    nome = request.form.get('nome', '').strip()
    # Lê o nome digitado.
    especialidade = request.form.get('especialidade', '').strip()
    # Lê a especialidade.
    foto = request.form.get('foto', '').strip()
    # Lê o nome do arquivo de foto já existente (campo de texto, opcional quando há upload).
    caminho_upload = salvar_foto_upload(request.files.get('foto_upload'))
    # Tenta salvar uma foto enviada pelo formulário; devolve o caminho ou None.
    if caminho_upload:
        # Quando o admin enviou uma imagem nova.
        foto = caminho_upload
        # Usa o arquivo enviado no lugar do nome digitado.
    ativo = 1 if request.form.get('ativo') == 'on' else 0
    # Converte o checkbox em 0 ou 1 para o banco.
    senha = request.form.get('senha', '').strip()
    # Lê a senha opcional para o login da profissional na área restrita.
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
        # Verifica se há foto (enviada agora ou nome de arquivo existente).
        erro = 'Envie uma foto ou informe o nome de um arquivo já existente (ex: pamela_francisco.png).'
        # Define mensagem padrão sobre a foto.
    return nome, especialidade, foto, ativo, senha, erro
    # Retorna os dados normalizados, a senha e o erro de validação.


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
        nome, especialidade, foto, ativo, senha, erro = _parse_profissional_form()
        # Lê e valida os dados do formulário, incluindo a senha opcional.
        ids_servicos = request.form.getlist('servicos_ids')
        # Lê quais serviços foram marcados para essa profissional.
        if erro:
            # Verifica se houve erro de validação.
            return render_template('admin/profissional_form.html', profissional=None, form=request.form, erro=erro, servicos=servicos, servicos_selecionados=set(ids_servicos), empresa=dados_empresa())
            # Reabre o formulário com erro mantendo o que foi digitado.
        cursor = db.execute(
            # Insere a profissional no banco.
            'INSERT INTO profissionais (nome, especialidade, foto, ativo, senha) VALUES (?, ?, ?, ?, ?)',
            # Usa parâmetros para evitar injeção de SQL.
            (nome, especialidade, foto, ativo, senha or None)
            # Envia os dados; senha vazia vira NULL para indicar "sem login".
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
    return render_template('admin/profissional_form.html', profissional=None, form=None, servicos=servicos, servicos_selecionados=set(), empresa=dados_empresa())
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
        nome, especialidade, foto, ativo, senha, erro = _parse_profissional_form()
        # Lê e valida os dados, incluindo a senha opcional.
        ids_servicos = request.form.getlist('servicos_ids')
        # Lê os serviços marcados.
        if erro:
            # Verifica erro de validação.
            return render_template('admin/profissional_form.html', profissional=profissional, form=request.form, erro=erro, servicos=servicos, servicos_selecionados=set(ids_servicos), empresa=dados_empresa())
            # Reabre o formulário mantendo o que foi digitado.
        if senha:
            # Quando o admin digita uma nova senha, atualiza inclusive a coluna senha.
            db.execute(
                # Atualiza todos os campos da profissional.
                'UPDATE profissionais SET nome = ?, especialidade = ?, foto = ?, ativo = ?, senha = ? WHERE id = ?',
                # Inclui a nova senha no UPDATE.
                (nome, especialidade, foto, ativo, senha, id)
                # Envia os dados.
            )
            # Finaliza o UPDATE com senha.
        else:
            # Senha em branco: preserva a senha atual e atualiza apenas o resto.
            db.execute(
                # Atualiza somente os campos comuns.
                'UPDATE profissionais SET nome = ?, especialidade = ?, foto = ?, ativo = ? WHERE id = ?',
                # Mantém a senha intacta.
                (nome, especialidade, foto, ativo, id)
                # Envia os dados.
            )
            # Finaliza o UPDATE sem mexer na senha.
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
    return render_template('admin/profissional_form.html', profissional=profissional, form=None, servicos=servicos, servicos_selecionados=vinculadas_atual, empresa=dados_empresa())
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
    return render_template('admin/clientes.html', clientes=lista, busca=busca, empresa=dados_empresa())
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
    return render_template('admin/cliente_detalhe.html', cliente=cliente, agendamentos=agendamentos, empresa=dados_empresa())
    # Renderiza a página de detalhe.


@admin.route('/agendamento/<int:id>/arquivar', methods=['POST'])
# Cria a rota que move um único atendimento confirmado e já passado para o histórico.
def agendamento_arquivar(id):
    # Define a função de arquivamento individual.
    if not esta_logado():
        # Bloqueia acesso sem login.
        return redirect(url_for('admin.login'))
        # Envia para o login.
    db = get_db()
    # Abre a conexão com o banco.
    hoje = date.today().isoformat()
    # Pega a data de hoje para validar que o atendimento já passou.
    cur = db.execute(
        # Faz UPDATE protegido: só arquiva quem é confirmado, com data passada e ainda não arquivado.
        """UPDATE agendamentos
              SET arquivado = 1
            WHERE id = ?
              AND status = 'confirmado'
              AND data < ?
              AND arquivado = 0""",
        (id, hoje)
    )
    # Executa o UPDATE com a regra de negócio embutida.
    db.commit()
    # Confirma a mudança no banco.
    if cur.rowcount:
        # Verifica se uma linha foi efetivamente arquivada.
        flash('Atendimento movido para o histórico.', 'success')
        # Mostra mensagem de sucesso.
    else:
        # Entra aqui quando nenhuma linha bateu na condição.
        flash('Esse atendimento não pode ser arquivado (precisa estar confirmado e com data passada).', 'error')
        # Avisa o admin que a regra não permite arquivar.
    return redirect(url_for('admin.dashboard'))
    # Volta para o dashboard.


@admin.route('/agendamentos/arquivar-completos', methods=['POST'])
# Cria a rota que arquiva em massa todos os atendimentos confirmados e já passados.
def agendamentos_arquivar_completos():
    # Define a função de arquivamento em massa.
    if not esta_logado():
        # Bloqueia acesso sem login.
        return redirect(url_for('admin.login'))
        # Envia para o login.
    db = get_db()
    # Abre o banco.
    hoje = date.today().isoformat()
    # Captura a data de hoje para o filtro.
    cur = db.execute(
        # Arquiva todos os confirmados com data passada que ainda estão no dashboard.
        """UPDATE agendamentos
              SET arquivado = 1
            WHERE status = 'confirmado'
              AND data < ?
              AND arquivado = 0""",
        (hoje,)
    )
    # Executa o UPDATE em massa.
    db.commit()
    # Salva no banco.
    if cur.rowcount:
        # Verifica se algum atendimento foi arquivado.
        flash(f'{cur.rowcount} atendimento(s) movido(s) para o histórico.', 'success')
        # Mostra a contagem para o admin.
    else:
        # Entra aqui quando não havia nada para arquivar.
        flash('Nenhum atendimento completo para arquivar.', 'info')
        # Informa que não havia trabalho a fazer.
    return redirect(url_for('admin.dashboard'))
    # Volta para o dashboard.


@admin.route('/historico')
# Cria a rota da página de Histórico (lista atendimentos arquivados).
def historico():
    # Define a função que lista o histórico.
    if not esta_logado():
        # Bloqueia acesso sem login.
        return redirect(url_for('admin.login'))
        # Envia para o login.
    filtro_data_inicio = request.args.get('data_inicio', '').strip()
    # Recebe filtro opcional de data inicial.
    filtro_data_fim = request.args.get('data_fim', '').strip()
    # Recebe filtro opcional de data final.
    filtro_profissional = request.args.get('profissional_id', '').strip()
    # Recebe filtro opcional de profissional.
    filtro_q = request.args.get('q', '').strip()
    # Recebe busca opcional por nome ou telefone do cliente.
    try:
        # Tenta converter o número da página para inteiro.
        pagina = max(1, int(request.args.get('pagina', '1')))
        # Garante que a página é pelo menos 1.
    except ValueError:
        # Entra aqui se a página veio em formato inválido.
        pagina = 1
        # Volta para a primeira página por segurança.
    por_pagina = 20
    # Define o tamanho da página.
    where = ['a.arquivado = 1']
    # O histórico só mostra arquivados.
    params = []
    # Lista de parâmetros da consulta.
    if filtro_data_inicio:
        # Aplica o filtro de data inicial se informado.
        where.append('a.data >= ?')
        # Adiciona condição de data mínima.
        params.append(filtro_data_inicio)
        # Envia o valor para a consulta.
    if filtro_data_fim:
        # Aplica o filtro de data final se informado.
        where.append('a.data <= ?')
        # Adiciona condição de data máxima.
        params.append(filtro_data_fim)
        # Envia o valor para a consulta.
    if filtro_profissional:
        # Aplica o filtro de profissional se informado.
        where.append('a.profissional_id = ?')
        # Adiciona condição de profissional.
        params.append(filtro_profissional)
        # Envia o id da profissional.
    if filtro_q:
        # Aplica busca textual por cliente.
        where.append('(c.nome LIKE ? OR c.telefone LIKE ?)')
        # Procura no nome ou no telefone.
        like = f'%{filtro_q}%'
        # Monta o padrão LIKE.
        params.extend([like, like])
        # Adiciona dois valores (um para nome, outro para telefone).
    where_sql = ' WHERE ' + ' AND '.join(where)
    # Junta a cláusula WHERE final.
    db = get_db()
    # Abre o banco.
    total = db.execute(
        # Conta o total de registros arquivados que batem nos filtros para calcular paginação.
        f"""SELECT COUNT(*) AS n
              FROM agendamentos a
              JOIN clientes c ON c.id = a.cliente_id
            {where_sql}""",
        params
    ).fetchone()['n']
    # Total de itens compatíveis com os filtros.
    offset = (pagina - 1) * por_pagina
    # Calcula o offset da página atual.
    rows = db.execute(
        # Busca a página atual com todos os dados que o template precisa.
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
    # Lista paginada de atendimentos arquivados.
    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)
    # Calcula o número total de páginas (mínimo 1).
    profissionais = buscar_profissionais(False)
    # Lista profissionais (ativas e inativas) para o select de filtro.
    return render_template('admin/historico.html',
                           agendamentos=rows, profissionais=profissionais,
                           filtro_data_inicio=filtro_data_inicio, filtro_data_fim=filtro_data_fim,
                           filtro_profissional=filtro_profissional, filtro_q=filtro_q,
                           pagina=pagina, total_paginas=total_paginas, total=total,
                           empresa=dados_empresa())
    # Renderiza a página de Histórico.


@admin.route('/agendamento/<int:id>/restaurar', methods=['POST'])
# Cria a rota que devolve um atendimento arquivado para o dashboard.
def agendamento_restaurar(id):
    # Define a função de restauração.
    if not esta_logado():
        # Bloqueia acesso sem login.
        return redirect(url_for('admin.login'))
        # Envia para o login.
    db = get_db()
    # Abre o banco.
    db.execute('UPDATE agendamentos SET arquivado = 0 WHERE id = ?', (id,))
    # Marca o atendimento como não-arquivado para reaparecer no dashboard.
    db.commit()
    # Salva a alteração.
    flash('Atendimento restaurado para o dashboard.', 'success')
    # Confirma para o admin.
    return redirect(url_for('admin.historico'))
    # Volta para a tela de histórico.


@admin.route('/configuracoes', methods=['GET', 'POST'])
# Cria a rota de configurações visuais globais (admin define fonte e cores).
def configuracoes():
    # Define a função que mostra/grava as preferências visuais.
    if not esta_logado():
        # Bloqueia acesso sem login.
        return redirect(url_for('admin.login'))
        # Envia para o login.
    db = get_db()
    # Abre o banco.
    if request.method == 'POST':
        # Verifica se o admin enviou o formulário.
        novas = {
            # Lê cada campo de configuração enviado.
            'fonte': request.form.get('fonte', '').strip() or 'Arial, Helvetica, sans-serif',
            # Mantém um fallback caso o campo venha vazio.
            'cor_texto': request.form.get('cor_texto', '').strip() or '#3f2d25',
            # Cor principal de texto.
            'cor_fundo': request.form.get('cor_fundo', '').strip() or '#efe0d1',
            # Cor de fundo geral.
            'cor_destaque': request.form.get('cor_destaque', '').strip() or '#6f4f3f',
            # Cor dos botões e destaques.
        }
        # Fecha o dicionário com as novas preferências.
        for chave, valor in novas.items():
            # Salva cada par no banco.
            db.execute(
                # Cria ou atualiza a linha.
                'INSERT INTO configuracoes (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor',
                # SQLite suporta ON CONFLICT a partir da 3.24.
                (chave, valor)
                # Envia chave e valor.
            )
            # Finaliza o upsert.
        for pagina, info in APARENCIA_PAGINAS.items():
            # Percorre cada página configurável para salvar as cores por área.
            for area, dados in info['areas'].items():
                # Percorre cada área da página.
                for prop in dados['props']:
                    # Percorre cada propriedade de cor da área.
                    base = pagina + '__' + area + '__' + prop
                    # Monta o sufixo usado nos campos do formulário.
                    chave = 'aparencia.' + pagina + '.' + area + '.' + prop
                    # Monta a chave salva no banco.
                    if request.form.get('usar__' + base) == 'on':
                        # Só personaliza a cor quando a caixinha "personalizar" estiver marcada.
                        valor = request.form.get('cor__' + base, '').strip()
                        # Lê a cor escolhida no seletor.
                        if cor_valida(valor):
                            # Garante que é uma cor hexadecimal válida antes de salvar.
                            db.execute(
                                # Cria ou atualiza a cor daquela área.
                                'INSERT INTO configuracoes (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor',
                                # Faz upsert na tabela de configurações.
                                (chave, valor)
                                # Envia chave e cor.
                            )
                            # Finaliza o upsert da cor.
                    else:
                        # Caixinha desmarcada significa "voltar ao padrão do tema".
                        db.execute('DELETE FROM configuracoes WHERE chave = ?', (chave,))
                        # Remove a personalização para a área usar a cor padrão do CSS.
        db.commit()
        # Confirma a gravação.
        flash('Configurações visuais atualizadas.', 'success')
        # Mostra mensagem de sucesso.
        return redirect(url_for('admin.configuracoes'))
        # Recarrega a página com os novos valores aplicados.
    config = carregar_configuracoes_visuais()
    # GET: carrega valores atuais para preencher o formulário.
    aparencia_valores = carregar_aparencia()
    # Carrega as cores por área já salvas para preencher o formulário.
    return render_template(
        # Renderiza a página de configurações com tudo que o painel precisa.
        'admin/configuracoes.html',
        config=config,
        empresa=dados_empresa(),
        aparencia_paginas=APARENCIA_PAGINAS,
        aparencia_valores=aparencia_valores,
        prop_rotulo=PROP_ROTULO,
        prop_padrao=PROP_PADRAO,
    )
    # Renderiza a página de configurações.


@admin.route('/conteudo', methods=['GET', 'POST'])
# Cria a rota do editor de textos e informações do site.
def conteudo():
    # Define a função que mostra e grava os textos editáveis.
    if not esta_logado():
        # Bloqueia acesso sem login.
        return redirect(url_for('admin.login'))
        # Envia para o login.
    db = get_db()
    # Abre o banco.
    if request.method == 'POST':
        # Verifica se o admin enviou o formulário.
        for _grupo, campos in TEXTOS_CAMPOS:
            # Percorre cada grupo de campos.
            for chave, _rotulo, _padrao, _tipo in campos:
                # Percorre cada campo editável do grupo.
                valor = request.form.get(chave, '').strip()
                # Lê o valor enviado para essa chave.
                if valor:
                    # Quando há conteúdo, salva (cria ou atualiza).
                    db.execute(
                        'INSERT INTO configuracoes (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor',
                        (chave, valor)
                    )
                    # Finaliza o upsert.
                else:
                    # Campo vazio volta ao texto padrão removendo a personalização.
                    db.execute('DELETE FROM configuracoes WHERE chave = ?', (chave,))
                    # Remove a chave personalizada.
        db.commit()
        # Salva todas as alterações.
        flash('Textos e informações do site atualizados.', 'success')
        # Mostra mensagem de sucesso.
        return redirect(url_for('admin.conteudo'))
        # Recarrega a página com os novos valores.
    valores = carregar_textos()
    # GET: carrega os textos atuais (salvos ou padrão) para preencher o formulário.
    return render_template('admin/conteudo.html', grupos=TEXTOS_CAMPOS, valores=valores, empresa=dados_empresa())
    # Renderiza o editor de textos e informações.


@admin.route('/fotos')
# Cria a rota que lista e gerencia as fotos do site (galeria, responsável, etc.).
def gerenciar_fotos():
    # Define a função que mostra a página de gestão de fotos.
    if not esta_logado():
        # Bloqueia acesso sem login.
        return redirect(url_for('admin.login'))
        # Envia para o login.
    locais = {}
    # Dicionário que junta, para cada local, suas informações e suas fotos atuais.
    for chave, info in FOTOS_LOCAIS.items():
        # Percorre cada local de fotos configurável.
        locais[chave] = {'info': info, 'fotos': buscar_fotos(chave)}
        # Guarda os dados do local e a lista de fotos já cadastradas.
    return render_template('admin/fotos.html', locais=locais, empresa=dados_empresa())
    # Renderiza a página de gestão de fotos.


@admin.route('/fotos/<local>/adicionar', methods=['POST'])
# Cria a rota que adiciona (ou substitui) uma foto em um local.
def adicionar_foto(local):
    # Define a função que recebe o upload de uma nova foto.
    if not esta_logado():
        # Bloqueia acesso sem login.
        return redirect(url_for('admin.login'))
        # Envia para o login.
    if local not in FOTOS_LOCAIS:
        # Recusa locais que não existem no mapa.
        flash('Local de foto inválido.', 'error')
        # Avisa o admin.
        return redirect(url_for('admin.gerenciar_fotos'))
        # Volta para a página de fotos.
    db = get_db()
    # Abre o banco.
    caminho = salvar_foto_upload(request.files.get('foto'))
    # Salva o arquivo enviado e recebe o caminho relativo (ou None se inválido).
    if not caminho:
        # Quando o upload falha ou não é imagem válida.
        flash('Selecione uma imagem válida (png, jpg, jpeg, webp ou gif, até 5 MB).', 'error')
        # Mostra a mensagem de erro.
        return redirect(url_for('admin.gerenciar_fotos'))
        # Volta para a página de fotos.
    titulo = request.form.get('titulo', '').strip()
    # Lê a legenda opcional da foto.
    if not FOTOS_LOCAIS[local]['multiplas']:
        # Quando o local aceita apenas uma foto (ex: responsável).
        antigas = buscar_fotos(local)
        # Busca as fotos atuais para remover antes de inserir a nova.
        for foto in antigas:
            # Percorre as fotos antigas.
            remover_arquivo_foto(foto['arquivo'])
            # Apaga o arquivo enviado anteriormente (preserva imagens originais do projeto).
        db.execute('DELETE FROM fotos WHERE local = ?', (local,))
        # Remove os registros antigos para manter apenas a foto nova.
    proxima_ordem = db.execute('SELECT COALESCE(MAX(ordem), 0) + 1 FROM fotos WHERE local = ?', (local,)).fetchone()[0]
    # Calcula a próxima posição na ordem do local.
    db.execute(
        # Insere a nova foto no banco.
        'INSERT INTO fotos (local, arquivo, titulo, ordem) VALUES (?, ?, ?, ?)',
        # Usa parâmetros para evitar injeção de SQL.
        (local, caminho, titulo, proxima_ordem)
        # Envia os dados da foto.
    )
    # Finaliza a inserção.
    db.commit()
    # Salva no banco.
    flash('Foto adicionada com sucesso.', 'success')
    # Confirma para o admin.
    return redirect(url_for('admin.gerenciar_fotos'))
    # Volta para a página de fotos.


@admin.route('/fotos/<int:id>/remover', methods=['POST'])
# Cria a rota que remove uma foto específica.
def remover_foto(id):
    # Define a função que apaga uma foto.
    if not esta_logado():
        # Bloqueia acesso sem login.
        return redirect(url_for('admin.login'))
        # Envia para o login.
    db = get_db()
    # Abre o banco.
    foto = db.execute('SELECT * FROM fotos WHERE id = ?', (id,)).fetchone()
    # Busca a foto pelo id.
    if foto is None:
        # Quando a foto não existe.
        flash('Foto não encontrada.', 'error')
        # Avisa o admin.
        return redirect(url_for('admin.gerenciar_fotos'))
        # Volta para a página de fotos.
    remover_arquivo_foto(foto['arquivo'])
    # Apaga o arquivo do disco apenas se foi um upload do admin.
    db.execute('DELETE FROM fotos WHERE id = ?', (id,))
    # Remove o registro do banco.
    db.commit()
    # Salva a remoção.
    flash('Foto removida.', 'success')
    # Confirma para o admin.
    return redirect(url_for('admin.gerenciar_fotos'))
    # Volta para a página de fotos.


@admin.route('/fotos/<int:id>/mover', methods=['POST'])
# Cria a rota que reordena uma foto dentro do carrossel (subir/descer).
def mover_foto(id):
    # Define a função que troca a ordem de duas fotos vizinhas.
    if not esta_logado():
        # Bloqueia acesso sem login.
        return redirect(url_for('admin.login'))
        # Envia para o login.
    db = get_db()
    # Abre o banco.
    foto = db.execute('SELECT * FROM fotos WHERE id = ?', (id,)).fetchone()
    # Busca a foto que será movida.
    if foto is None:
        # Quando a foto não existe.
        return redirect(url_for('admin.gerenciar_fotos'))
        # Volta sem alterar nada.
    direcao = request.form.get('direcao', '')
    # Lê se a foto deve subir ou descer.
    if direcao == 'subir':
        # Para subir, procura a foto imediatamente anterior na ordem.
        vizinha = db.execute(
            'SELECT * FROM fotos WHERE local = ? AND (ordem < ? OR (ordem = ? AND id < ?)) ORDER BY ordem DESC, id DESC LIMIT 1',
            (foto['local'], foto['ordem'], foto['ordem'], foto['id'])
        ).fetchone()
        # Pega a vizinha de cima.
    else:
        # Para descer, procura a foto imediatamente seguinte na ordem.
        vizinha = db.execute(
            'SELECT * FROM fotos WHERE local = ? AND (ordem > ? OR (ordem = ? AND id > ?)) ORDER BY ordem ASC, id ASC LIMIT 1',
            (foto['local'], foto['ordem'], foto['ordem'], foto['id'])
        ).fetchone()
        # Pega a vizinha de baixo.
    if vizinha is not None:
        # Só troca se existir uma vizinha para o lado pedido.
        db.execute('UPDATE fotos SET ordem = ? WHERE id = ?', (vizinha['ordem'], foto['id']))
        # Coloca a foto na posição da vizinha.
        db.execute('UPDATE fotos SET ordem = ? WHERE id = ?', (foto['ordem'], vizinha['id']))
        # Coloca a vizinha na posição da foto.
        db.commit()
        # Salva a nova ordem.
    return redirect(url_for('admin.gerenciar_fotos'))
    # Volta para a página de fotos.


# =================== BLUEPRINT DA ÁREA RESTRITA DA PROFISSIONAL =================== #

@profissional.route('/login', methods=['GET', 'POST'])
# Cria a rota de login da profissional não-admin.
def login_profissional():
    # Define a função de login da área restrita.
    db = get_db()
    # Abre o banco.
    profissionais_lista = db.execute('SELECT id, nome FROM profissionais WHERE ativo = 1 AND senha IS NOT NULL AND senha != "" ORDER BY nome').fetchall()
    # Lista somente profissionais ativas que já têm senha definida pelo admin.
    if request.method == 'POST':
        # Verifica envio do formulário.
        profissional_id = request.form.get('profissional_id', '').strip()
        # Recebe o id da profissional escolhida.
        senha = request.form.get('senha', '')
        # Recebe a senha digitada.
        if profissional_id and senha:
            # Valida campos preenchidos.
            linha = db.execute('SELECT * FROM profissionais WHERE id = ? AND ativo = 1', (profissional_id,)).fetchone()
            # Busca a profissional pelo id apenas se estiver ativa.
            if linha and linha['senha'] and linha['senha'] == senha:
                # Confere senha exata.
                session.clear()
                # Garante que não fica nada de sessão anterior.
                session['profissional_id'] = linha['id']
                # Marca a sessão como pertencente a esta profissional.
                return redirect(url_for('profissional.agenda_profissional'))
                # Envia para a agenda dela.
        return render_template('profissional/login.html', profissionais=profissionais_lista, erro='Profissional ou senha inválida.', empresa=dados_empresa())
        # Reabre o login com mensagem de erro.
    return render_template('profissional/login.html', profissionais=profissionais_lista, erro=None, empresa=dados_empresa())
    # GET: mostra o formulário vazio.


@profissional.route('/logout')
# Cria a rota de saída da área restrita.
def logout_profissional():
    # Define a função de logout.
    session.pop('profissional_id', None)
    # Remove só a chave da profissional (não mexe na sessão do admin se houver).
    return redirect(url_for('profissional.login_profissional'))
    # Volta para a tela de login.


@profissional.route('/agenda')
# Cria a rota da agenda própria da profissional logada.
def agenda_profissional():
    # Define a função que mostra a agenda da profissional.
    prof = buscar_profissional_logada()
    # Carrega a profissional logada.
    if not prof:
        # Sem profissional logada, redireciona para o login.
        return redirect(url_for('profissional.login_profissional'))
        # Envia para o login.
    return render_template('profissional/agenda.html', profissional=prof, empresa=dados_empresa())
    # Renderiza a página de agenda.


@profissional.route('/agenda/dia')
# Cria a rota JSON com os horários do dia, restrita à profissional logada.
def agenda_profissional_dia():
    # Define a função usada pelo JavaScript da agenda.
    prof = buscar_profissional_logada()
    # Carrega a profissional.
    if not prof:
        # Sem login, devolve 401.
        return jsonify({'erro': 'nao_autenticado'}), 401
        # Bloqueia consulta sem autenticação.
    data_texto = request.args.get('data', '').strip()
    # Recebe a data escolhida.
    if not data_texto:
        # Data obrigatória.
        return jsonify({'data': data_texto, 'horarios': []})
        # Devolve lista vazia se faltar.
    aberto = dia_funciona(data_texto)
    # Verifica funcionamento do dia.
    db = get_db()
    # Abre o banco.
    sql = '''SELECT a.id, a.horario, a.status,
                    c.nome AS cliente_nome, c.telefone,
                    s.nome AS servico_nome, s.preco, s.duracao_min
             FROM agendamentos a
             JOIN clientes c ON c.id = a.cliente_id
             JOIN servicos s ON s.id = a.servico_id
             WHERE a.data = ? AND a.profissional_id = ? AND a.status != ?'''
    # Busca atendimentos do dia para esta profissional (sem cancelados).
    linhas = db.execute(sql, (data_texto, prof['id'], 'cancelado')).fetchall()
    # Executa a consulta.
    ocupados = {linha['horario']: linha for linha in linhas}
    # Indexa por horário.
    bloqueios = buscar_bloqueios(data_texto, str(prof['id']))
    # Carrega bloqueios cadastrados.
    bloqueios_horarios = {b['horario']: b for b in bloqueios}
    # Indexa bloqueios por horário (vazio significa dia inteiro).
    dia_bloqueado_inteiro = '' in bloqueios_horarios
    # Marca se o dia foi bloqueado por inteiro.
    resposta = []
    # Lista a devolver.
    for horario in HORARIOS:
        # Percorre os horários padrão.
        ocupado = ocupados.get(horario)
        # Localiza agendamento daquele horário.
        slot = {
            # Monta cada slot.
            'horario': horario,
            'aberto': aberto and not dia_bloqueado_inteiro,
            'bloqueado': horario in bloqueios_horarios or dia_bloqueado_inteiro,
            'agendamento': None,
        }
        # Fecha o slot base.
        if ocupado:
            # Inclui detalhes do cliente.
            slot['agendamento'] = {
                'id': ocupado['id'],
                'cliente_nome': ocupado['cliente_nome'],
                'telefone': ocupado['telefone'],
                'servico_nome': ocupado['servico_nome'],
                'preco': float(ocupado['preco']),
                'duracao_min': ocupado['duracao_min'],
                'status': ocupado['status'],
            }
            # Fecha o dicionário do agendamento.
        resposta.append(slot)
        # Adiciona ao retorno.
    return jsonify({'data': data_texto, 'aberto': aberto, 'horarios': resposta})
    # Retorna agenda do dia.


@profissional.route('/disponibilidade-mes')
# Calendário mensal restrito à profissional logada.
def profissional_disponibilidade_mes():
    # Define a função.
    prof = buscar_profissional_logada()
    # Carrega a profissional.
    if not prof:
        # Sem login, bloqueia.
        return jsonify({'erro': 'nao_autenticado'}), 401
        # Devolve 401.
    ano = int(request.args.get('ano', date.today().year))
    # Recebe o ano.
    mes = int(request.args.get('mes', date.today().month))
    # Recebe o mês.
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    # Último dia do mês.
    resposta = {}
    # Dicionário de saída.
    for dia in range(1, ultimo_dia + 1):
        # Percorre cada dia.
        data_texto = f'{ano:04d}-{mes:02d}-{dia:02d}'
        # Monta a data.
        aberto = dia_funciona(data_texto)
        # Funcionamento do dia.
        livres = contar_horarios_disponiveis(data_texto, str(prof['id'])) if aberto else 0
        # Quantos slots livres existem.
        resposta[data_texto] = {'aberto': aberto, 'livres': livres, 'total': len(HORARIOS)}
        # Salva o resumo do dia.
    return jsonify(resposta)
    # Retorna o calendário.


@profissional.route('/bloqueios', methods=['GET', 'POST'])
# Página onde a profissional vê/cria bloqueios próprios.
def bloqueios_profissional():
    # Define a função.
    prof = buscar_profissional_logada()
    # Carrega a profissional.
    if not prof:
        # Sem login, redireciona.
        return redirect(url_for('profissional.login_profissional'))
        # Envia para o login.
    db = get_db()
    # Abre o banco.
    if request.method == 'POST':
        # Trata envio do formulário.
        data_texto = request.form.get('data', '').strip()
        # Recebe a data.
        horario = request.form.get('horario', '').strip()
        # Recebe o horário (ou 'dia_inteiro').
        motivo = request.form.get('motivo', '').strip()
        # Recebe o motivo livre.
        if not data_texto:
            # Data obrigatória.
            flash('Informe a data que você não vai poder comparecer.', 'error')
            # Mostra erro.
        else:
            # Tudo certo, salva no banco.
            horario_salvo = '' if (horario == 'dia_inteiro' or horario == '') else horario
            # Vazio significa "dia inteiro" no schema.
            motivo_salvo = motivo if motivo else 'Indisponibilidade'
            # Texto padrão se não informar motivo.
            db.execute(
                # Insere bloqueio no banco.
                'INSERT INTO bloqueios_agenda (profissional_id, data, horario, motivo) VALUES (?, ?, ?, ?)',
                # Os 4 valores na ordem do schema.
                (prof['id'], data_texto, horario_salvo, motivo_salvo)
                # Profissional é sempre a logada.
            )
            # Finaliza o INSERT.
            db.commit()
            # Salva.
            flash('Bloqueio cadastrado com sucesso.', 'success')
            # Confirma para a profissional.
        return redirect(url_for('profissional.bloqueios_profissional'))
        # Volta para a tela de bloqueios.
    lista = db.execute(
        # Lista somente bloqueios da profissional logada.
        '''SELECT id, data, horario, motivo
             FROM bloqueios_agenda
            WHERE profissional_id = ?
            ORDER BY data DESC, horario''',
        (prof['id'],)
    ).fetchall()
    # Carrega a lista.
    return render_template('profissional/bloqueios.html', profissional=prof, bloqueios=lista, horarios=HORARIOS, empresa=dados_empresa())
    # Renderiza a tela.


@profissional.route('/bloqueios/<int:bid>/excluir', methods=['POST'])
# Permite a profissional remover um bloqueio próprio.
def bloqueio_profissional_excluir(bid):
    # Define a função.
    prof = buscar_profissional_logada()
    # Carrega a profissional.
    if not prof:
        # Sem login, redireciona.
        return redirect(url_for('profissional.login_profissional'))
        # Envia para o login.
    db = get_db()
    # Abre o banco.
    db.execute('DELETE FROM bloqueios_agenda WHERE id = ? AND profissional_id = ?', (bid, prof['id']))
    # Garante que só apaga se for da própria profissional.
    db.commit()
    # Salva a exclusão.
    flash('Bloqueio removido.', 'success')
    # Confirma.
    return redirect(url_for('profissional.bloqueios_profissional'))
    # Volta para a lista.


app.register_blueprint(publico)
# Registra as rotas públicas dentro do Flask.

app.register_blueprint(admin)
# Registra as rotas administrativas dentro do Flask.

app.register_blueprint(profissional)
# Registra as rotas da área restrita das profissionais.


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
