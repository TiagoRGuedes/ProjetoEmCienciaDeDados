// Controla todos os carrosséis de fotos da parte pública do site.
(function () {
  // Descobre se a pessoa prefere menos animações (acessibilidade).
  var prefereMenosMovimento = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Procura cada carrossel marcado com o atributo data-carrossel.
  document.querySelectorAll('[data-carrossel]').forEach(function (carrossel) {
    var trilha = carrossel.querySelector('.carrossel-trilha'); // Trilha que desliza com as fotos.
    var itens = carrossel.querySelectorAll('.carrossel-item'); // Todos os slides.
    var anterior = carrossel.querySelector('.carrossel-prev'); // Botão de voltar.
    var proximo = carrossel.querySelector('.carrossel-next'); // Botão de avançar.
    var pontos = carrossel.querySelector('.carrossel-pontos'); // Área dos pontinhos.
    var legenda = carrossel.querySelector('.carrossel-legenda'); // Legenda da foto atual.
    var indice = 0; // Índice da foto atual.
    var timer = null; // Guarda o cronômetro da passagem automática.

    // Se não houver fotos, não faz nada.
    if (!trilha || itens.length === 0) { return; }

    // Cria um pontinho clicável para cada foto.
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

    // Aplica visualmente a posição atual: desliza a trilha, marca o pontinho e mostra a legenda.
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

    // Vai para uma foto específica (com volta circular) e reinicia o tempo do automático.
    function irPara(i) {
      indice = (i + itens.length) % itens.length;
      atualizar();
      reiniciarAuto();
    }

    if (anterior) { anterior.addEventListener('click', function () { irPara(indice - 1); }); }
    if (proximo) { proximo.addEventListener('click', function () { irPara(indice + 1); }); }

    // Passagem automática a cada 5 segundos (desligada se houver só 1 foto ou se preferir menos movimento).
    function iniciarAuto() {
      if (prefereMenosMovimento || itens.length <= 1) { return; }
      pararAuto();
      timer = setInterval(function () { indice = (indice + 1) % itens.length; atualizar(); }, 5000);
    }
    function pararAuto() { if (timer) { clearInterval(timer); timer = null; } }
    function reiniciarAuto() { if (timer) { iniciarAuto(); } }

    // Pausa o automático quando o mouse ou o teclado estão sobre o carrossel.
    carrossel.addEventListener('mouseenter', pararAuto);
    carrossel.addEventListener('mouseleave', iniciarAuto);
    carrossel.addEventListener('focusin', pararAuto);
    carrossel.addEventListener('focusout', iniciarAuto);

    // Esconde as setas e os pontos quando só existe uma foto.
    if (itens.length <= 1) {
      if (anterior) anterior.style.display = 'none';
      if (proximo) proximo.style.display = 'none';
      if (pontos) pontos.style.display = 'none';
    }

    // Posição inicial e início da passagem automática.
    atualizar();
    iniciarAuto();
  });
})();
