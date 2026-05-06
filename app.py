{% extends "base.html" %} <!-- Usa o layout base do site. -->
{% block conteudo %} <!-- Começa o conteúdo específico da confirmação. -->
<section class="secao chamada-final"> <!-- Cria uma seção centralizada de confirmação. -->
    <div class="container"> <!-- Centraliza o conteúdo na tela. -->
        <h2>Agendamento enviado com sucesso!</h2> <!-- Mostra a mensagem principal de sucesso. -->
        <p>Seu pedido foi registrado como pendente e a equipe do {{ empresa.nome }} entrará em contato para confirmar o atendimento.</p> <!-- Explica que o agendamento ainda será confirmado. -->
        <p><strong>Contato:</strong> {{ empresa.telefone }}</p> <!-- Mostra o telefone da empresa. -->
        <a class="botao" href="{{ url_for('publico.index') }}">Voltar ao início</a> <!-- Botão para voltar à página inicial. -->
        <a class="botao-secundario" href="{{ url_for('publico.agendar_get') }}">Fazer novo agendamento</a> <!-- Botão para novo agendamento. -->
    </div> <!-- Fecha o container. -->
</section> <!-- Fecha a seção de confirmação. -->
{% endblock %} <!-- Finaliza o conteúdo específico da confirmação. -->
