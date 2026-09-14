# MerendaNaMedida v2 — com banco de dados

Esta versão usa **Flask + SQLite**.

## 1. Instalação

No Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

No Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Depois abra no navegador:

`http://127.0.0.1:5000`

O arquivo `merenda.db` é criado automaticamente.

## 2. Onde adicionar os dados

Depois de abrir o sistema, use:

- `/turmas` para adicionar turmas
- `/alunos` para adicionar alunos
- `/professores` para adicionar professores
- `/ingredientes` para adicionar ingredientes e quantidade por refeição
- `/cardapio` para cadastrar o cardápio
- `/presenca` para marcar a presença diária
- `/config` para alterar o nome da escola e a margem

## 3. Banco de dados

O SQLite cria as tabelas automaticamente:

- escola
- turmas
- alunos
- professores
- ingredientes
- cardapios
- presencas_alunos
- presencas_professores
- consumo_merenda

Você pode abrir `merenda.db` com um programa como **DB Browser for SQLite** se quiser editar os dados diretamente.

## 4. Observação importante

Este é um sistema local/MVP. Antes de colocar na internet ou usar com dados reais de alunos, é necessário adicionar autenticação, permissões, proteção de dados, backup e controles de segurança.

## 5. API de cálculo

Também existe:

`/api/calculo?data=2026-09-13`

Ela retorna JSON com alunos, professores, refeições e ingredientes calculados.

---

Developed by **@alvelin0**
