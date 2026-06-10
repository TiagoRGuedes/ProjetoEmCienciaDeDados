// Widget de acessibilidade aplicado em todo o site (cliente, admin e profissional).
(function () {
  'use strict';

  var CHAVE = 'rp_acessibilidade';
  var ZOOM_MIN = 1;
  var ZOOM_MAX = 1.5;
  var ZOOM_PASSO = 0.1;
  // Estado padrão de cada opção.
  var padrao = {
    altoContraste: false,
    focoForte: false,
    sublinhaLinks: false,
    semAnimacao: false,
    zoom: 1,
  };

  // Lê preferências salvas (ou usa o padrão).
  function carregar() {
    try {
      var dados = JSON.parse(localStorage.getItem(CHAVE) || '{}');
      return Object.assign({}, padrao, dados);
    } catch (e) {
      return Object.assign({}, padrao);
    }
  }

  // Salva preferências.
  function salvar(estado) {
    try { localStorage.setItem(CHAVE, JSON.stringify(estado)); } catch (e) {}
  }

  // Aplica o estado atual ao body (classes + zoom).
  function aplicar(estado) {
    var b = document.body;
    b.classList.toggle('a11y-alto-contraste', !!estado.altoContraste);
    b.classList.toggle('a11y-foco-forte', !!estado.focoForte);
    b.classList.toggle('a11y-sublinha-links', !!estado.sublinhaLinks);
    b.classList.toggle('a11y-sem-animacao', !!estado.semAnimacao);
    // O zoom altera o tamanho geral do conteúdo. Valor 1 = sem alteração.
    b.style.zoom = estado.zoom && estado.zoom !== 1 ? estado.zoom : '';
  }

  // Cria os elementos do widget e do skip-link no início do body.
  function montar(estado) {
    // Link "pular para o conteúdo principal", para navegação por teclado.
    var skip = document.createElement('a');
    skip.className = 'a11y-skip';
    skip.href = '#conteudo-principal';
    skip.textContent = 'Pular para o conteúdo principal';
    document.body.insertBefore(skip, document.body.firstChild);

    // Botão flutuante.
    var fab = document.createElement('button');
    fab.type = 'button';
    fab.className = 'a11y-fab';
    fab.setAttribute('aria-label', 'Abrir painel de acessibilidade');
    fab.setAttribute('aria-controls', 'a11y-painel');
    fab.setAttribute('aria-expanded', 'false');
    fab.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="currentColor"><circle cx="12" cy="4.5" r="2"/><path d="M19 8h-5v13h-2v-6h-1v6H9V8H4V6h15v2z"/></svg>';
    document.body.appendChild(fab);

    // Painel.
    var painel = document.createElement('div');
    painel.className = 'a11y-painel';
    painel.id = 'a11y-painel';
    painel.setAttribute('role', 'dialog');
    painel.setAttribute('aria-label', 'Opções de acessibilidade');
    painel.hidden = true;
    painel.innerHTML = ''
      + '<div class="a11y-painel-cabecalho">'
      +   '<strong>Acessibilidade</strong>'
      +   '<button type="button" class="a11y-fechar" aria-label="Fechar painel">×</button>'
      + '</div>'
      + '<div class="a11y-grupo">'
      +   '<div class="a11y-grupo-titulo">Tamanho do texto</div>'
      +   '<div class="a11y-texto-controles">'
      +     '<button type="button" data-acao="diminuir" aria-label="Diminuir texto">A−</button>'
      +     '<span data-rotulo="zoom">100%</span>'
      +     '<button type="button" data-acao="aumentar" aria-label="Aumentar texto">A+</button>'
      +   '</div>'
      + '</div>'
      + '<div class="a11y-grupo">'
      +   '<div class="a11y-grupo-titulo">Visualização</div>'
      +   '<button type="button" class="a11y-toggle" data-toggle="altoContraste" aria-pressed="false">Alto contraste</button>'
      +   '<button type="button" class="a11y-toggle" data-toggle="focoForte" aria-pressed="false">Destacar foco</button>'
      +   '<button type="button" class="a11y-toggle" data-toggle="sublinhaLinks" aria-pressed="false">Sublinhar links</button>'
      +   '<button type="button" class="a11y-toggle" data-toggle="semAnimacao" aria-pressed="false">Reduzir animações</button>'
      + '</div>'
      + '<button type="button" class="a11y-reset" data-acao="reset">Redefinir tudo</button>';
    document.body.appendChild(painel);

    return { fab: fab, painel: painel };
  }

  // Sincroniza visualmente os toggles e o rótulo de zoom com o estado.
  function refletir(estado, painel) {
    var toggles = painel.querySelectorAll('.a11y-toggle[data-toggle]');
    toggles.forEach(function (botao) {
      var chave = botao.getAttribute('data-toggle');
      botao.setAttribute('aria-pressed', estado[chave] ? 'true' : 'false');
    });
    var rotulo = painel.querySelector('[data-rotulo="zoom"]');
    if (rotulo) { rotulo.textContent = Math.round(estado.zoom * 100) + '%'; }
  }

  // Abre/fecha o painel.
  function alternar(fab, painel, mostrar) {
    var aberto = typeof mostrar === 'boolean' ? mostrar : painel.hidden;
    painel.hidden = !aberto;
    fab.setAttribute('aria-expanded', aberto ? 'true' : 'false');
    if (aberto) {
      var primeiro = painel.querySelector('button');
      if (primeiro) { primeiro.focus(); }
    }
  }

  // Inicializa quando o DOM está pronto.
  function iniciar() {
    var estado = carregar();
    aplicar(estado);
    var partes = montar(estado);
    var fab = partes.fab;
    var painel = partes.painel;
    refletir(estado, painel);

    fab.addEventListener('click', function () { alternar(fab, painel); });

    // Fecha ao clicar no X ou pressionar Esc.
    painel.querySelector('.a11y-fechar').addEventListener('click', function () { alternar(fab, painel, false); fab.focus(); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !painel.hidden) { alternar(fab, painel, false); fab.focus(); }
    });
    // Fecha clicando fora.
    document.addEventListener('click', function (e) {
      if (painel.hidden) { return; }
      if (painel.contains(e.target) || fab.contains(e.target)) { return; }
      alternar(fab, painel, false);
    });

    // Toggles (alto contraste, foco, links, animação).
    painel.querySelectorAll('.a11y-toggle[data-toggle]').forEach(function (botao) {
      botao.addEventListener('click', function () {
        var chave = botao.getAttribute('data-toggle');
        estado[chave] = !estado[chave];
        aplicar(estado); refletir(estado, painel); salvar(estado);
      });
    });

    // Aumentar/diminuir texto.
    painel.querySelectorAll('[data-acao]').forEach(function (botao) {
      botao.addEventListener('click', function () {
        var acao = botao.getAttribute('data-acao');
        if (acao === 'aumentar') {
          estado.zoom = Math.min(ZOOM_MAX, +(estado.zoom + ZOOM_PASSO).toFixed(2));
        } else if (acao === 'diminuir') {
          estado.zoom = Math.max(ZOOM_MIN, +(estado.zoom - ZOOM_PASSO).toFixed(2));
        } else if (acao === 'reset') {
          estado = Object.assign({}, padrao);
        }
        aplicar(estado); refletir(estado, painel); salvar(estado);
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();
