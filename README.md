# Refúgio da Preta — Sistema de Agendamento

## Sobre o projeto

Site completo para estúdio de manicure com sistema de agendamento online, painel administrativo e gestão de profissionais. Desenvolvido como projeto acadêmico.

## Funcionalidades

- Landing page com serviços, galeria de trabalhos e informações do estúdio
- Agendamento online com calendário visual, seleção de profissional e horários disponíveis
- Bloqueio automático de horários já reservados
- Painel administrativo com login protegido
- Gestão de agendamentos (confirmar, cancelar, remarcar)
- Gestão de serviços (criar, editar, excluir)
- Gestão de profissionais e seus vínculos com serviços
- Bloqueio de horários e folgas pelo administrador
- Proteção CSRF em todos os formulários

## Tecnologias

- Python / Flask
- SQLite
- HTML, CSS
- JavaScript

## Como rodar localmente

1. Clone o repositório
2. Instale as dependências: `pip install -r requirements.txt`
3. Crie o arquivo `.env` baseado no `.env.example` e preencha os valores
4. Rode o servidor: `python app.py`
5. Acesse http://localhost:5000

## Variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto com base no `.env.example`:

| Variável | Descrição |
|---|---|
| `SECRET_KEY` | Chave secreta do Flask |
| `ADMIN_USUARIO` | Usuário do painel admin |
| `ADMIN_SENHA` | Senha do painel admin |
| `FLASK_DEBUG` | `True` para desenvolvimento, `False` para produção |

## Equipe

- **Nicolas** — Backend + testes
- **Bruno** — Frontend (páginas do cliente)
- **Tiago** — Frontend (painel admin)
