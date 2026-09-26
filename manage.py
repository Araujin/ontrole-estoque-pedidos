"""Ferramentas locais de backup e recuperação de acesso."""
import argparse
import getpass
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from auth import Auth, password_hash, valid_password
from domain import Store, BusinessError

ROOT=Path(__file__).resolve().parent


def backup(source, destination):
    if not Path(source).is_file():
        raise BusinessError('Banco não encontrado. Execute o sistema primeiro.')
    if Path(destination).exists():
        raise BusinessError('O arquivo de destino já existe; escolha outro nome.')
    Path(destination).parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(source)) as origin, closing(sqlite3.connect(destination)) as target:
        origin.backup(target)


def main():
    parser=argparse.ArgumentParser(description='Backup e recuperação local do Estoca')
    parser.add_argument('action',choices=['backup','reset-password'])
    parser.add_argument('--db',default=str(ROOT/'data'/'estoque.sqlite3'))
    parser.add_argument('--username')
    args=parser.parse_args()
    try:
        if args.action=='backup':
            dest=ROOT/'backups'/('estoca-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite3')
            backup(args.db,dest)
            print('Backup salvo em:',dest)
        else:
            if not Path(args.db).is_file():
                raise BusinessError('Banco não encontrado.')
            store=Store(args.db);Auth(store)
            username=args.username or input('Usuário: ').strip()
            password=valid_password(getpass.getpass('Nova senha (mínimo 10 caracteres): '))
            if password != getpass.getpass('Repita a nova senha: '):
                raise BusinessError('As senhas não coincidem.')
            with store.transaction() as db:
                user=db.execute('SELECT id FROM users WHERE username=?',(username,)).fetchone()
                if not user:raise BusinessError('Usuário não encontrado.')
                salt=secrets.token_hex(16)
                db.execute('UPDATE users SET salt=?,password_hash=? WHERE id=?',(salt,password_hash(password,salt),user['id']))
                db.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],))
            print('Senha alterada e sessões encerradas.')
    except BusinessError as exc:
        parser.exit(1,str(exc)+'\n')


if __name__=='__main__':main()
