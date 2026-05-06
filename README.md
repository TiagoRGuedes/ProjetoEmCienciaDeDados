# Projeto Refúgio da Preta integrado ao backend

Este pacote já encaixa a parte do frontend do Integrante 2 dentro do programa enviado com `app.py`, `database.py`, `schema.sql`, `templates` e painel admin.

## Como rodar

```bash
cd projeto_refugio_integrado_backend
pip install -r requirements.txt
python app.py
```

Abra no navegador:

```text
http://127.0.0.1:5000
```

## Login do admin

```text
Usuário: admin
Senha: esmalteria123
```

## O que foi ajustado

- Mantive a estrutura com Blueprints `publico` e `admin`.
- Adaptei a página inicial para o Refúgio da Preta.
- Adaptei a página de serviços.
- Adaptei o agendamento para horários de terça a sábado, das 10h às 19h.
- Organizei os templates de admin dentro de `templates/admin/`.
- Adicionei CSS com tema marrom, rosa e nude.
- Adicionei as fotos dos trabalhos e a foto da Pamela Francisco.
- Mantive comentários explicativos no código.
