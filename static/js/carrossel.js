// Controla todos os carrosséis de fotos da parte pública do site.
(function () {
  // Procura cada carrossel marcado com o atributo data-carrossel.
  document.querySelectorAll('[data-carrossel]').forEach(function (carrossel) {
    // Pega a trilha que desliza com as fotos.
    var trilha = carrossel.querySelector('.carrossel-trilha');
    // Pega todos os slides (figuras) do carrossel.
    var itens = carrossel.querySelectorAll('.carrossel-item');
    // Pega o botão de voltar.
    var anterior = carrossel.querySelector('.carrossel-prev');
    // Pega o botão de avançar.
    var proximo = carrossel.querySelector('.carrossel-next');
    // Pega a área onde ficam os pontinhos de navegação.
    var pontos = carrossel.querySelector('.carrossel-pontos');
    // Guarda o índice da foto atual.
    var indice = 0;

    // Se não houver fotos, não faz nada.
    if (!trilha || itens.length === 0) {
      return;
    }

    // Cria um pontinho clicável para cada foto.
    if (pontos) {
      itens.forEach(function (item, i) {
        // Cria o botão do pontinho.
        var ponto = document.createElement('button');
        // Define a classe visual do pontinho.
        ponto.className = 'carrossel-ponto';
        // Acessibilidade: descreve para qual foto o pontinho leva.
        ponto.setAttribute('aria-label', 'Ir para a foto ' + (i + 1));
        // Ao clicar, vai direto para a foto correspondente.
        ponto.addEventListener('click', function () {
          indice = i;
          atualizar();
        });
        // Adiciona o pontinho na área de pontos.
        pontos.appendChild(ponto);
      });
    }

    // Aplica visualmente a posição atual do carrossel.
    function atualizar() {
      // Desliza a trilha para mostrar a foto do índice atual.
      trilha.style.transform = 'translateX(' + (-indice * 100) + '%)';
      // Atualiza qual pontinho aparece ativo.
      if (pontos) {
        pontos.querySelectorAll('.carrossel-ponto').forEach(function (ponto, i) {
          ponto.classList.toggle('ativo', i === indice);
        });
      }
    }

    // Botão voltar: vai para a foto anterior (volta para a última se estiver na primeira).
    if (anterior) {
      anterior.addEventListener('click', function () {
        indice = (indice - 1 + itens.length) % itens.length;
        atualizar();
      });
    }

    // Botão avançar: vai para a próxima foto (volta para a primeira ao passar da última).
    if (proximo) {
      proximo.addEventListener('click', function () {
        indice = (indice + 1) % itens.length;
        atualizar();
      });
    }

    // Esconde as setas e os pontos quando só existe uma foto.
    if (itens.length <= 1) {
      if (anterior) anterior.style.display = 'none';
      if (proximo) proximo.style.display = 'none';
      if (pontos) pontos.style.display = 'none';
    }

    // Deixa o carrossel na posição inicial.
    atualizar();
  });
})();
