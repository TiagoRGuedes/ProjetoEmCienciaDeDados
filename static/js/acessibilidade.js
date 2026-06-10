(function () {
  'use strict';

  var CHAVE = 'rp_acessibilidade';
  var ZOOM_MIN = 1;
  var ZOOM_MAX = 1.5;
  var ZOOM_PASSO = 0.1;
  var padrao = {
    altoContraste: false,
    focoForte: false,
    sublinhaLinks: false,
    semAnimacao: false,
    zoom: 1,
  };

  function carregar() {
    try {
      var dados = JSON.parse(localStorage.getItem(CHAVE) || '{}');
      return Object.assign({}, padrao, dados);
    } catch (e) {
      return Object.assign({}, padrao);
    }
  }

  function salvar(estado) {
    try { localStorage.setItem(CHAVE, JSON.stringify(estado)); } catch (e) {}
  }

  function aplicar(estado) {
    var b = document.body;
    b.classList.toggle('a11y-alto-contraste', !!estado.altoContraste);
    b.classList.toggle('a11y-foco-forte', !!estado.focoForte);
    b.classList.toggle('a11y-sublinha-links', !!estado.sublinhaLinks);
    b.classList.toggle('a11y-sem-animacao', !!estado.semAnimacao);
    b.style.zoom = estado.zoom && estado.zoom !== 1 ? estado.zoom : '';
  }

  function montar(estado) {
    var skip = document.createElement('a');
    skip.className = 'a11y-skip';
    skip.href = '#conteudo-principal';
    skip.textContent = 'Pular para o conteúdo principal';
    document.body.insertBefore(skip, document.body.firstChild);

    var fab = document.createElement('button');
    fab.type = 'button';
    fab.className = 'a11y-fab';
    fab.setAttribute('aria-label', 'Abrir painel de acessibilidade');
    fab.setAttribute('aria-controls', 'a11y-painel');
    fab.setAttribute('aria-expanded', 'false');
    fab.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="currentColor"><circle cx="12" cy="4.5" r="2"/><path d="M19 8h-5v13h-2v-6h-1v6H9V8H4V6h15v2z"/></svg>';
    document.body.appendChild(fab);

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

  function refletir(estado, painel) {
    var toggles = painel.querySelectorAll('.a11y-toggle[data-toggle]');
    toggles.forEach(function (botao) {
      var chave = botao.getAttribute('data-toggle');
      botao.setAttribute('aria-pressed', estado[chave] ? 'true' : 'false');
    });
    var rotulo = painel.querySelector('[data-rotulo="zoom"]');
    if (rotulo) { rotulo.textContent = Math.round(estado.zoom * 100) + '%'; }
  }

  function alternar(fab, painel, mostrar) {
    var aberto = typeof mostrar === 'boolean' ? mostrar : painel.hidden;
    painel.hidden = !aberto;
    fab.setAttribute('aria-expanded', aberto ? 'true' : 'false');
    if (aberto) {
      var primeiro = painel.querySelector('button');
      if (primeiro) { primeiro.focus(); }
    }
  }

  function iniciar() {
    var estado = carregar();
    aplicar(estado);
    var partes = montar(estado);
    var fab = partes.fab;
    var painel = partes.painel;
    refletir(estado, painel);

    fab.addEventListener('click', function () { alternar(fab, painel); });

    painel.querySelector('.a11y-fechar').addEventListener('click', function () { alternar(fab, painel, false); fab.focus(); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !painel.hidden) { alternar(fab, painel, false); fab.focus(); }
    });
    document.addEventListener('click', function (e) {
      if (painel.hidden) { return; }
      if (painel.contains(e.target) || fab.contains(e.target)) { return; }
      alternar(fab, painel, false);
    });

    painel.querySelectorAll('.a11y-toggle[data-toggle]').forEach(function (botao) {
      botao.addEventListener('click', function () {
        var chave = botao.getAttribute('data-toggle');
        estado[chave] = !estado[chave];
        aplicar(estado); refletir(estado, painel); salvar(estado);
      });
    });

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
