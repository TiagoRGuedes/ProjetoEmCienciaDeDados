(function () {
  var prefereMenosMovimento = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  document.querySelectorAll('[data-carrossel]').forEach(function (carrossel) {
    var trilha = carrossel.querySelector('.carrossel-trilha');
    var itens = carrossel.querySelectorAll('.carrossel-item');
    var anterior = carrossel.querySelector('.carrossel-prev');
    var proximo = carrossel.querySelector('.carrossel-next');
    var pontos = carrossel.querySelector('.carrossel-pontos');
    var legenda = carrossel.querySelector('.carrossel-legenda');
    var indice = 0;
    var timer = null;

    if (!trilha || itens.length === 0) { return; }

    if (pontos) {
      itens.forEach(function (item, i) {
        var ponto = document.createElement('button');
        ponto.className = 'carrossel-ponto';
        ponto.setAttribute('type', 'button');
        ponto.setAttribute('aria-label', 'Ir para a foto ' + (i + 1));
        ponto.addEventListener('click', function () { irPara(i); });
        pontos.appendChild(ponto);
      });
    }

    function atualizar() {
      trilha.style.transform = 'translateX(' + (-indice * 100) + '%)';
      if (pontos) {
        pontos.querySelectorAll('.carrossel-ponto').forEach(function (ponto, i) {
          ponto.classList.toggle('ativo', i === indice);
        });
      }
      if (legenda) {
        var img = itens[indice].querySelector('img');
        legenda.textContent = (img && img.getAttribute('data-legenda')) || '';
      }
    }

    function irPara(i) {
      indice = (i + itens.length) % itens.length;
      atualizar();
      reiniciarAuto();
    }

    if (anterior) { anterior.addEventListener('click', function () { irPara(indice - 1); }); }
    if (proximo) { proximo.addEventListener('click', function () { irPara(indice + 1); }); }

    function iniciarAuto() {
      if (prefereMenosMovimento || itens.length <= 1) { return; }
      pararAuto();
      timer = setInterval(function () { indice = (indice + 1) % itens.length; atualizar(); }, 5000);
    }
    function pararAuto() { if (timer) { clearInterval(timer); timer = null; } }
    function reiniciarAuto() { if (timer) { iniciarAuto(); } }

    carrossel.addEventListener('mouseenter', pararAuto);
    carrossel.addEventListener('mouseleave', iniciarAuto);
    carrossel.addEventListener('focusin', pararAuto);
    carrossel.addEventListener('focusout', iniciarAuto);

    if (itens.length <= 1) {
      if (anterior) anterior.style.display = 'none';
      if (proximo) proximo.style.display = 'none';
      if (pontos) pontos.style.display = 'none';
    }

    atualizar();
    iniciarAuto();
  });
})();
