# Histórico

## 2.0.0

- Primeiro acesso com criação de administrador, login e logout.
- Perfis administrador, operador e consulta, verificados no backend.
- Cadastro e ativação/desativação de usuários, troca e recuperação local de senha.
- Sessões revogáveis, token CSRF, validação de Host/Origin e limitador de login.
- Filtros adicionais e paginação visual das tabelas.
- Relatórios CSV de estoque, pedidos e movimentações, com proteção de campos textuais.
- Backup consistente do SQLite e instruções de atualização sem perda de dados.
- Inicialização simplificada com `iniciar.bat`.
- Tipos MIME explícitos para evitar diferenças no registro do Windows.
- Limite monetário por pedido e agrupamento mais eficiente dos itens na leitura.
- Testes de autenticação, permissões, atualização, backup e JavaScript com DOM mínimo.

## 1.0.0

- Produtos e fornecedores, movimentações, pedidos e dashboard.
- Transações contra estoque negativo e estorno por cancelamento.
- Banco SQLite, dados fictícios e testes de domínio/HTTP.
