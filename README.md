# Estoca 2.0 — Controle de Estoque e Pedidos

Sistema web para controle de estoque e gerenciamento de pedidos, desenvolvido como projeto de portfólio com foco em **desenvolvimento backend, regras de negócio, persistência de dados, autenticação, controle de acesso e testes**.

O backend foi desenvolvido em **Python**, utilizando a biblioteca padrão da linguagem, com persistência em **SQLite**. A interface utiliza **HTML, CSS e JavaScript**.

---

## Tecnologias

### Backend
- Python 3.10+
- SQLite
- Servidor HTTP em Python
- API HTTP
- Autenticação baseada em sessão
- Controle de acesso por perfil

### Frontend
- HTML5
- CSS3
- JavaScript

### Qualidade
- Testes automatizados com `unittest`
- Testes de JavaScript com Node.js
- Testes manuais documentados
- Git e GitHub

---

## Principais funcionalidades

- Cadastro e edição de produtos.
- Cadastro e edição de fornecedores.
- Ativação e desativação de produtos e fornecedores.
- Busca de produtos por nome ou SKU.
- Controle de entradas e saídas de estoque.
- Proteção contra estoque negativo.
- Criação de pedidos com múltiplos itens.
- Edição de pedidos em rascunho.
- Finalização de pedidos com baixa automática no estoque.
- Cancelamento de pedidos com estorno automático dos produtos.
- Histórico de movimentações.
- Indicadores de estoque e vendas.
- Filtros de produtos, pedidos e movimentações.
- Paginação de tabelas.
- Exportação de relatórios em CSV.
- Cadastro de usuários.
- Autenticação.
- Controle de permissões.
- Troca de senha.
- Backup do banco de dados.
- Recuperação local de senha.

---

## Perfis de acesso

| Perfil | Permissões |
| --- | --- |
| **Administrador** | Acesso completo e gerenciamento de usuários |
| **Operador** | Produtos, fornecedores, movimentações, pedidos e relatórios |
| **Consulta** | Visualização de dados, pedidos e relatórios |

As permissões são verificadas no backend.

Usuários desativados têm suas sessões revogadas e cada usuário pode alterar sua própria senha.

---

## Segurança

O sistema implementa diferentes mecanismos de segurança:

- Hash de senha com `PBKDF2-HMAC-SHA256`.
- Salt individual para cada senha.
- 600.000 iterações no processo de hash.
- Sessões com duração máxima de 8 horas.
- Armazenamento do hash do token de sessão.
- Cookies `HttpOnly`.
- Cookies com `SameSite=Strict`.
- Proteção CSRF para operações autenticadas.
- Validação de `Host`.
- Validação de `Origin`.
- Limitação de tentativas de login.
- Queries SQL parametrizadas.
- Controle de permissões no servidor.
- Revogação de sessões de usuários desativados.

> O Estoca 2.0 foi desenvolvido para execução local. Uma publicação externa exigiria adaptações adicionais de infraestrutura e segurança.

---

## Como executar

### Requisitos

- Python 3.10 ou superior

Não é necessário executar `pip install` ou `npm install` para utilizar a aplicação.

---

### Windows

Clone ou baixe o projeto e abra a pasta no terminal.

Opcionalmente, carregue os dados fictícios:

```powershell
py seed.py
