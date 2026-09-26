# Roteiro de validação no navegador

Use dados fictícios e confira no computador e em uma janela estreita (aproximadamente 390 px). Marque cada item após testar.

- [ ] Criar primeiro administrador; sair e entrar novamente.
- [ ] Conferir nome e perfil do usuário, navegação e atualização do painel.
- [ ] Cadastrar e editar fornecedor e produto; testar SKU repetido.
- [ ] Registrar entrada; tentar saída maior que o saldo; conferir mensagem e saldo preservado.
- [ ] Criar pedido com dois itens, editar quantidades e conferir total.
- [ ] Tentar finalizar um pedido com um dos itens sem saldo: nenhum item deve sofrer baixa.
- [ ] Regularizar saldo, finalizar e conferir histórico.
- [ ] Cancelar o pedido, conferir devolução; não deve existir ação para estornar novamente.
- [ ] Criar mais de dez produtos, testar busca, status e navegação entre páginas.
- [ ] Filtrar movimentos por produto e datas.
- [ ] Exportar os três CSVs e abrir no Excel; conferir acentos, valores e período.
- [ ] Criar usuário de consulta: cadastros e alterações devem estar indisponíveis; detalhes e CSV continuam acessíveis.
- [ ] Criar operador: alterações operacionais são permitidas, gerenciamento de usuários não.
- [ ] Desativar um usuário com outra sessão aberta; tentar atualizar nessa sessão.
- [ ] Trocar senha: deve exigir novo login e rejeitar a senha antiga.
- [ ] Navegar por teclado, abrir/fechar diálogos, verificar rótulos e mensagens.
- [ ] Reiniciar o servidor e conferir persistência.
- [ ] Criar backup e testar sua abertura em uma pasta de teste separada.

Resultado automatizado não marca estes itens: eles exigem interação real no navegador.
