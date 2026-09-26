# Atualizar da versão 1 para a versão 2

## Se já cadastrou produtos ou pedidos

1. No terminal do sistema antigo, pressione **Ctrl+C** para encerrar o servidor.
2. Faça uma cópia da pasta antiga completa e guarde como backup.
3. Extraia o novo ZIP em **outra pasta**, sem substituir a antiga.
4. Copie a pasta **`data`** da versão antiga para dentro da nova pasta `estoque-pedidos` (ao lado de `app.py`). Ela contém `estoque.sqlite3`.
5. Abra a nova pasta no VS Code e execute `python app.py`. Ou abra `iniciar.bat` com dois cliques.
6. Acesse http://localhost:8000 e crie sua conta de administrador.
7. Confira se produtos, pedidos e movimentos anteriores estão presentes.

A versão 2 cria as tabelas de acesso automaticamente, sem apagar os registros da operação. **Não rode `seed.py` para migrar dados**: esse arquivo serve apenas para popular um banco novo com exemplos fictícios.

Se estiver em dúvida sobre qual pasta contém os seus dados, pare antes de copiar ou substituir arquivos e confira o local de onde o servidor anterior foi iniciado.

## Se não precisa dos dados anteriores

Extraia em uma nova pasta, execute `python seed.py` se quiser exemplos, depois `python app.py`. No primeiro acesso, crie o administrador.

## Diagnóstico rápido

- **Tela antiga:** confira se o servidor antigo foi encerrado e use Ctrl+F5 no navegador.
- **Porta ocupada:** encerre o outro servidor ou use `python app.py --port 8001` e acesse http://localhost:8001.
- **Python não reconhecido:** feche e abra o VS Code após a instalação do Python.
- **Site sem estilo:** abra pela URL exibida pelo servidor, não por Live Server ou pelo arquivo HTML.
- **Muitas tentativas de login:** espere um minuto e tente novamente.
- **Senha esquecida:** `python manage.py reset-password --username seu_usuario`.

Mantenha a pasta antiga de backup até conferir a atualização. Bancos e backups não devem ser enviados ao repositório público.
