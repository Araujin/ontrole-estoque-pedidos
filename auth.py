"""Autenticação local: PBKDF2, sessões revogáveis e permissões no servidor."""
import hashlib
import hmac
import re
import secrets
import time
from contextlib import closing
from domain import BusinessError, text

ROLES = ('admin', 'operator', 'viewer')
ITERATIONS = 600_000


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), ITERATIONS).hex()


def valid_password(password):
    if not isinstance(password, str) or not 10 <= len(password) <= 128:
        raise BusinessError('A senha deve ter entre 10 e 128 caracteres.')
    return password


class Auth:
    def __init__(self, store):
        self.store = store
        with closing(store.connect()) as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    name TEXT NOT NULL, salt TEXT NOT NULL, password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin','operator','viewer')),
                    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)));
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
                    csrf TEXT NOT NULL, expires REAL NOT NULL);
                PRAGMA user_version=2;
            ''')

    def needs_setup(self):
        with closing(self.store.connect()) as db:
            return db.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0

    def create(self, data, setup=False):
        username = text(data.get('username'), 'Usuário', limit=40).lower()
        if not re.fullmatch('[a-z0-9._-]{3,40}', username):
            raise BusinessError('Usuário: use 3 a 40 letras sem acentos, números, ponto, hífen ou sublinhado.')
        name = text(data.get('name'), 'Nome', limit=80)
        password = valid_password(data.get('password'))
        role = 'admin' if setup else data.get('role')
        if role not in ROLES:
            raise BusinessError('Perfil inválido.')
        salt = secrets.token_hex(16)
        digest = password_hash(password, salt)
        with self.store.transaction() as db:
            if setup and db.execute('SELECT COUNT(*) FROM users').fetchone()[0]:
                raise BusinessError('Configuração inicial já concluída.')
            if db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone():
                raise BusinessError('Este usuário já existe.')
            return db.execute('INSERT INTO users(username,name,salt,password_hash,role) VALUES (?,?,?,?,?)',
                              (username,name,salt,digest,role)).lastrowid

    def login(self, data):
        username = text(data.get('username'), 'Usuário', limit=40).lower()
        password = data.get('password')
        if not isinstance(password,str) or len(password)>128:
            raise BusinessError('Usuário ou senha inválidos.')
        with closing(self.store.connect()) as db:
            user = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        digest = password_hash(password, user['salt'] if user else 'unregistered-user')
        if not user or not user['active'] or not hmac.compare_digest(digest,user['password_hash']):
            raise BusinessError('Usuário ou senha inválidos.')
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        with self.store.transaction() as db:
            db.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
            db.execute('INSERT INTO sessions VALUES (?,?,?,?)',
                       (hashlib.sha256(token.encode()).hexdigest(),user['id'],csrf,time.time()+8*3600))
        return token

    def session(self, token):
        if not token or len(token)>200:
            return None
        with closing(self.store.connect()) as db:
            row = db.execute('''SELECT u.id,u.username,u.name,u.role,s.csrf FROM sessions s
                JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires>? AND u.active=1''',
                (hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
            return dict(row) if row else None

    def logout(self, token):
        with self.store.transaction() as db:
            db.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))

    def users(self):
        with closing(self.store.connect()) as db:
            return [dict(r) for r in db.execute('SELECT id,name,username,role,active FROM users ORDER BY id')]

    def toggle(self, actor, user_id, active):
        if not isinstance(active,bool):
            raise BusinessError('Status inválido.')
        if user_id == actor['id']:
            raise BusinessError('Você não pode desativar a própria conta.')
        with self.store.transaction() as db:
            user = self.store.require(db,'users',user_id)
            if user['role']=='admin' and not active and db.execute("SELECT COUNT(*) FROM users WHERE active=1 AND role='admin'").fetchone()[0] <= 1:
                raise BusinessError('Mantenha pelo menos um administrador ativo.')
            db.execute('UPDATE users SET active=? WHERE id=?',(int(active),user_id))
            if not active:
                db.execute('DELETE FROM sessions WHERE user_id=?',(user_id,))

    def change_password(self, user, data):
        new_password = valid_password(data.get('new_password'))
        old = data.get('current_password')
        if not isinstance(old,str) or len(old)>128:
            raise BusinessError('Senha atual inválida.')
        with self.store.transaction() as db:
            row = self.store.require(db,'users',user['id'])
            if not hmac.compare_digest(password_hash(old,row['salt']),row['password_hash']):
                raise BusinessError('Senha atual inválida.')
            salt=secrets.token_hex(16)
            db.execute('UPDATE users SET salt=?,password_hash=? WHERE id=?',
                       (salt,password_hash(new_password,salt),user['id']))
            db.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],))
