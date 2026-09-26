# Estoca 2.0 — Controle de estoque e pedidos

Aplicação de portfólio com cadastro de produtos e fornecedores, movimentações de estoque e ciclo de pedidos. Backend em **Python**, persistência em **SQLite** e interface em **HTML, CSS e JavaScript**. Sem dependências externas para executar a aplicação.

**Versão 2.0:** acesso por usuário, três perfis de permissão, relatórios CSV, filtros, paginação na interface, backup e recuperação de senha. Para atualizar a versão anterior sem perder dados, leia `ATUALIZAR.md`.

## Abrir no VS Code — Windows

1. Instale Python **3.10 ou superior**, caso ainda não tenha. Na instalação, habilite a inclusão do Python no PATH.
2. Extraia o ZIP. No VS Code, escolha **Arquivo → Abrir Pasta** e selecione `estoque-pedidos`, a pasta que contém `app.py`.
3. Abra **Terminal → Novo Terminal**.
4. Opcionalmente, carregue os dados fictícios:

```powershell
py seed.py
```

5. Inicie o servidor:

```powershell
py app.py
```

6. Abra **http://localhost:8000** no navegador. No primeiro acesso, crie seu administrador com uma senha de no mínimo 10 caracteres. Não existe senha padrão.

No Windows, você também pode abrir `iniciar.bat` com dois cliques: ele inicia o servidor e abre o navegador. Fechar essa janela encerra o servidor.

Se `py` não for reconhecido e Python estiver instalado, use `python` no lugar de `py`. No macOS/Linux, use `python3`. Não é preciso executar `pip install` ou `npm install`.

**Este projeto precisa do servidor Python.** Abrir `index.html` diretamente ou usar somente Live Server não executa o backend.

Para encerrar: `Ctrl+C` no terminal. Se a porta estiver ocupada:

```powershell
py app.py --port 8001
```

Nesse caso, abra http://localhost:8001.

## Acesso e permissões

| Perfil | Permissões |
| --- | --- |
| Administrador | Toda a operação; cria, desativa e reativa usuários |
| Operador | Produtos, fornecedores, movimentos e pedidos; consulta e exporta |
| Consulta | Visualiza dados, detalhes dos pedidos e exporta relatórios |

As permissões são verificadas no servidor. O cadastro de administradores iniciais só fica disponível enquanto não há usuários. Cada usuário pode trocar sua senha; a troca encerra todas as suas sessões. A própria conta não pode ser desativada pelo usuário logado. Usuários desativados têm as sessões revogadas.

Senhas usam PBKDF2-HMAC-SHA256 com sal individual e 600.000 iterações. As sessões duram até 8 horas; o banco guarda o hash do token. Cookies são HttpOnly e SameSite=Strict. Escritas autenticadas exigem token CSRF. Tentativas de login/configuração são limitadas a 8 por minuto por endereço no processo atual. Reiniciar o servidor zera esse limitador.

## Experimentar o fluxo

Com os dados fictícios, há quatro produtos, um fornecedor, um pedido finalizado e um rascunho.

1. Em **Fornecedores**, cadastre ou edite um parceiro.
2. Em **Produtos**, cadastre nome, SKU único, preço de venda e estoque mínimo. O saldo inicial é zero.
3. Em **Movimentações**, registre uma entrada com quantidade e motivo.
4. Em **Pedidos**, crie um rascunho com cliente e vários produtos.
5. Clique em **Finalizar**: os itens são baixados juntos, desde que haja saldo para todos.
6. Cancele um pedido finalizado: o estoque é devolvido uma única vez.
7. Confira o histórico e os indicadores na **Visão geral**.

## Funcionalidades

- Cadastro, consulta, edição e desativação/reativação de produtos e fornecedores.
- Busca de produtos por nome ou SKU.
- Fornecedor opcional por produto.
- Preços armazenados em centavos inteiros.
- Movimentos manuais de entrada e saída, com motivo e saldo resultante.
- Pedidos com múltiplos itens, edição de rascunho e detalhes dos pedidos fechados.
- Filtros de pedidos por status e de movimentos por produto.
- Indicadores de estoque mínimo, valor em estoque e vendas finalizadas.
- Interface responsiva, campos identificados, diálogos e mensagens de erro.
- Filtros por nome/SKU, fornecedor, status e período das movimentações.
- Paginação das tabelas em grupos de dez registros, realizada no navegador.
- Relatórios de estoque atual, pedidos e movimentações em CSV com separador `;` e UTF-8 com BOM.
- Proteção de células textuais do CSV contra interpretação como fórmulas.
- Botão de atualização para recarregar os dados sem sair da tela.
- Cadastro de usuários, troca de senha e controle de acesso por perfil.

## Regras de negócio

- Quantidades representam **unidades inteiras**, não quilos ou metros fracionados.
- Nenhuma operação pode deixar o estoque negativo.
- Rascunhos não reservam nem baixam estoque.
- Finalização e cancelamento usam transações SQLite (`BEGIN IMMEDIATE`). Uma falha em qualquer item desfaz toda a operação, incluindo registros de histórico.
- Duas finalizações concorrentes não podem consumir o mesmo saldo disponível.
- Um pedido finalizado não pode ser editado ou finalizado novamente.
- Cancelar um rascunho não altera estoque; cancelar um finalizado devolve os itens. Um pedido cancelado não pode ser cancelado novamente.
- Linhas repetidas do mesmo produto são somadas ao salvar o pedido.
- O preço é copiado do catálogo quando o produto entra no pedido. Editar seu preço no catálogo não muda os itens existentes do pedido. No rascunho, editar quantidades preserva o preço registrado.
- Nome e SKU ficam registrados no item. Pedidos finalizados preservam esses dados; ao editar um rascunho, nome e SKU são atualizados a partir do catálogo.
- Produtos inativos não entram em novos pedidos nem podem ser baixados por finalização. Cancelamentos continuam permitindo estorno mesmo após desativação.
- A exclusão é lógica (desativação), para manter as referências do histórico. Não há exclusão física pela interface.
- Fornecedores inativos não podem receber novos vínculos. Vínculos já existentes são mantidos.
- “Valor em estoque” usa saldo × **preço de venda**, inclusive de produtos inativos. Não representa custo contábil ou lucro.
- “Vendas finalizadas” inclui apenas pedidos com status finalizado; cancelados são excluídos.

## Estrutura

| Caminho | Responsabilidade |
| --- | --- |
| `app.py` | Servidor HTTP local, rotas e respostas da API |
| `auth.py` | Usuários, senhas e sessões |
| `manage.py` | Backup e recuperação local de senha |
| `iniciar.bat` | Inicialização simplificada no Windows |
| `domain.py` | Validação, regras, transações e schema SQLite |
| `seed.py` | Dados fictícios para demonstração |
| `static/` | Interface web |
| `tests/test_domain.py` | Testes de regras, persistência e concorrência |
| `tests/test_http.py` | Testes de API e arquivos estáticos |
| `.vscode/` | Configuração opcional de execução/debug |
| `data/estoque.sqlite3` | Banco gerado na primeira execução; ignorado pelo Git |

Relacionamentos: fornecedor possui produtos; pedido possui itens que referenciam produtos; cada movimento referencia um produto e, quando aplicável, um pedido. Saldos são atualizados na mesma transação que grava o histórico. Queries parametrizadas tratam valores recebidos; os nomes de tabelas são constantes internas.

## Testes

No terminal, dentro da pasta do projeto:

```powershell
py -m unittest discover -s tests -v
```

Há também verificações do JavaScript com DOM mínimo, opcionais, usando Node.js 18 ou superior:

```powershell
node --test tests/frontend.test.cjs
```

Os testes utilizam bancos temporários, sem alterar o banco usado pela interface. A suíte cobre saldo negativo, reversão de transação, estorno único, concorrência, preços registrados, edição de rascunhos, produtos inativos, SKU único e fluxo HTTP, autenticação, permissões, CSRF, troca de senha, atualização do banco e backup.

Os testes automatizados não substituem uma revisão visual no navegador. Roteiro manual sugerido: experimentar as cinco telas no computador e no celular, criar um pedido com dois itens, provocar insuficiência de saldo, corrigir por entrada, finalizar, cancelar e conferir o histórico. Verificar navegação por teclado e mensagens de validação.

## API local

As rotas operacionais exigem sessão autenticada. As escritas exigem cabeçalho `X-CSRF-Token` retornado por `/api/auth/me` e usam POST com `Content-Type: application/json`. Erros de validação retornam HTTP 400 e `{"error":"mensagem"}`.

| Método e rota | Finalidade |
| --- | --- |
| `GET /api/auth/me` | Sessão atual e necessidade de configuração |
| `POST /api/auth/setup` e `/api/auth/login` | Configuração inicial e login |
| `POST /api/auth/logout` e `/api/auth/password` | Saída e troca de senha |
| `GET /api/users`, `POST /api/users` e `/api/users/{id}/active` | Administração de usuários |
| `GET /api/state` | Consultar produtos, fornecedores, pedidos e histórico |
| `POST /api/products` e `/api/products/{id}` | Criar e editar produto |
| `POST /api/suppliers` e `/api/suppliers/{id}` | Criar e editar fornecedor |
| `POST /api/products/{id}/active` | Alterar status, com `{"active":false}` |
| `POST /api/suppliers/{id}/active` | Alterar status do fornecedor |
| `POST /api/movements` | Registrar entrada ou saída |
| `POST /api/orders` e `/api/orders/{id}` | Criar e editar rascunho |
| `POST /api/orders/{id}/complete` | Finalizar pedido, corpo `{}` |
| `POST /api/orders/{id}/cancel` | Cancelar pedido, corpo `{}` |

Exemplo de produto:

```json
{"sku":"P-001","name":"Produto exemplo","price_cents":1990,"minimum":5,"supplier_id":null}
```

Exemplo de movimento:

```json
{"product_id":1,"kind":"in","quantity":10,"reason":"Recebimento de compra"}
```

Exemplo de pedido:

```json
{"customer":"Cliente fictício","items":[{"product_id":1,"quantity":2}]}
```

## Dados e publicação no GitHub

O banco é criado automaticamente e persiste entre reinícios. `seed.py` recusa bancos com registros para evitar duplicar a demonstração. Para criar um backup consistente (também funciona com o servidor aberto):

```powershell
python manage.py backup
```

A cópia será gravada em `backups/`, com data e hora no nome. Ela contém os dados e as contas; não publique banco ou backups no GitHub. Para restaurar, encerre o servidor, preserve uma cópia do banco atual e substitua `data/estoque.sqlite3` pelo backup escolhido.

Se esquecer a senha, com acesso ao computador e ao banco local:

```powershell
python manage.py reset-password --username seu_usuario
```

A senha será solicitada sem exibição no terminal. Não é um recurso de recuperação remota.

Envie o código, os testes, este README e o `.gitignore` para um repositório como `controle-estoque-pedidos`. Não envie o banco com seus dados reais. Este projeto não roda somente no GitHub Pages, pois precisa de um processo Python e de armazenamento persistente.

## Atualização e limites

A inicialização adiciona as tabelas de usuários e sessões sem apagar produtos, pedidos ou movimentos da versão 1. O schema passa a ter `user_version=2`. Faça backup antes de atualizar e siga `ATUALIZAR.md`.

Projeto de portfólio e execução **local**. O servidor escuta apenas em `127.0.0.1`; não foi preparado para exposição à internet. O cookie não usa Secure porque a aplicação local usa HTTP. Publicação externa requer servidor de aplicação adequado, HTTPS, configuração de cookies, gestão de segredos e revisão de segurança. As contas não protegem contra alguém com acesso direto aos arquivos do computador.

A API ainda retorna o conjunto completo de registros. A paginação é visual, no navegador; bases grandes exigem paginação no servidor. A sessão não identifica o autor de cada movimento: auditoria individual é uma próxima evolução. Não há edição de perfil de um usuário existente pela interface; crie uma conta com o perfil correto e desative a antiga quando apropriado.

Datas dos filtros e relatórios usam o fuso local do navegador. Relatórios de pedidos filtram pela data de criação, não pela finalização. O estoque exportado é a posição atual, não um saldo histórico. Os relatórios incluem todas as linhas que atendem aos filtros de sua própria tela, independentemente da página visível nas tabelas.

Não inclui pagamentos, emissão fiscal, descontos, custos, entregas ou sincronização em tempo real entre abas. Use “Atualizar” para recarregar. O total de cada pedido está limitado a R$ 1 bilhão nesta demonstração.

A suíte automatizada inclui testes de domínio, HTTP, autenticação e DOM mínimo; **não equivale a um teste visual completo em navegadores**. O arquivo `TESTE-MANUAL.md` contém o roteiro para essa verificação.

## Próximos exercícios

- Paginação e busca diretamente na API.
- Registro do usuário responsável por cada operação.
- Testes completos de navegador e capturas das telas para o README.
- Reposição sugerida e relatórios de giro de estoque.
- Migrações numeradas para futuras alterações de schema.

Este projeto é uma base de estudo. Personalize-o e saiba explicar as transações, permissões e testes ao apresentá-lo em uma entrevista.
