# Refúgio da Preta — Agendamento com serviço e profissionais unidos

Projeto Flask do Integrante 2 para o frontend do Refúgio da Preta.

## Melhorias desta versão

- O campo de email foi removido do agendamento.
- A escolha de serviço e profissional foi unificada em um único passo.
- Depois que a cliente escolhe um serviço, aparecem somente as profissionais disponíveis para aquele procedimento.
- Cada profissional continua com agenda separada.
- O calendário mostra dias e horários disponíveis conforme a profissional escolhida.
- Horários reservados, bloqueios, folgas e feriados ficam indisponíveis.
- Quando o admin cancela ou remarca um agendamento, o horário antigo volta a ficar disponível automaticamente.
- A estética foi mantida em marrom e bege, com poucos detalhes rosa.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

Abra no navegador:

```text
http://127.0.0.1:5000
```

## Login admin

```text
Usuário: admin
Senha: esmalteria123
```

## Importante

Se você já tinha um banco antigo, apague o arquivo `esmalteria.db` antes de rodar esta versão, pois agora o banco possui vínculo entre profissionais e serviços.

Não envie para o GitHub:

```text
esmalteria.db
__pycache__/
```
