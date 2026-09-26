"""Servidor local, sem dependências externas. Execute: python app.py"""
import argparse
import webbrowser
import json
import hmac
import time
import threading
from http.cookies import SimpleCookie
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from domain import Store, BusinessError
from auth import Auth

ROOT = Path(__file__).resolve().parent


def handler_for(store):
    auth = Auth(store)
    attempts = {}
    attempts_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def respond(self, data, status=200, cookie=None):
            body = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            if cookie:
                self.send_header('Set-Cookie', cookie)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def token(self):
            cookie = SimpleCookie()
            try:
                cookie.load(self.headers.get('Cookie',''))
                return cookie['estoca_session'].value if 'estoca_session' in cookie else ''
            except Exception:
                return ''

        def valid_host(self):
            return self.headers.get('Host','') in (
                f'localhost:{self.server.server_port}',f'127.0.0.1:{self.server.server_port}')

        def do_GET(self):
            if not self.valid_host():
                return self.respond({'error':'Host não permitido.'},403)
            route = urlsplit(self.path).path
            try:
                if route == '/api/auth/me':
                    return self.respond({'user':auth.session(self.token()),'setup_required':auth.needs_setup()})
                if route.startswith('/api/'):
                    user = auth.session(self.token())
                    if not user:
                        return self.respond({'error':'Entre na sua conta para continuar.'},401)
                    if route == '/api/state':
                        return self.respond(store.snapshot())
                    if route == '/api/users':
                        if user['role'] != 'admin':
                            return self.respond({'error':'Acesso exclusivo do administrador.'},403)
                        return self.respond({'users':auth.users()})
                    return self.respond({'error':'Recurso não encontrado.'},404)
            except sqlite3.Error:
                return self.respond({'error':'Banco indisponível. Tente novamente.'},503)
            files = {'/': 'index.html', '/styles.css': 'styles.css', '/app.js': 'app.js'}
            if route not in files:
                return self.respond({'error': 'Recurso não encontrado.'}, 404)
            path = ROOT / 'static' / files[route]
            body = path.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', {'index.html':'text/html','styles.css':'text/css','app.js':'text/javascript'}[path.name] + '; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if not self.valid_host():
                return self.respond({'error':'Host não permitido.'},403)
            # App local: rejeita escrita cross-origin e exige JSON.
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + self.headers.get('Host', ''):
                return self.respond({'error': 'Origem não permitida.'}, 403)
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.respond({'error': 'Envie application/json.'}, 415)
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 100_000:
                    return self.respond({'error': 'Tamanho de requisição inválido.'}, 413)
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise BusinessError('Envie um objeto JSON.')
                route = urlsplit(self.path).path
                if route in ('/api/auth/setup','/api/auth/login'):
                    with attempts_lock:
                        recent = [t for t in attempts.get(self.client_address[0],[]) if t > time.time()-60]
                        if len(recent) >= 8:
                            return self.respond({'error':'Muitas tentativas. Aguarde um minuto.'},429)
                        attempts[self.client_address[0]] = recent+[time.time()]
                    if route.endswith('/setup'):
                        auth.create(data,setup=True)
                    token = auth.login(data)
                    return self.respond({'ok':True},cookie=f'estoca_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800')
                user = auth.session(self.token())
                if not user:
                    return self.respond({'error':'Sessão expirada. Entre novamente.'},401)
                if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),user['csrf']):
                    return self.respond({'error':'Sessão inválida. Atualize a página.'},403)
                if route == '/api/auth/logout':
                    auth.logout(self.token())
                    return self.respond({'ok':True},cookie='estoca_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
                if route == '/api/auth/password':
                    auth.change_password(user,data)
                    return self.respond({'ok':True},cookie='estoca_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
                if route.startswith('/api/users'):
                    if user['role']!='admin':
                        return self.respond({'error':'Acesso exclusivo do administrador.'},403)
                    match = re.fullmatch(r'/api/users/(\d+)/active',route)
                    if route == '/api/users':
                        return self.respond({'ok':True,'id':auth.create(data)})
                    if match:
                        auth.toggle(user,int(match[1]),data.get('active'))
                        return self.respond({'ok':True})
                    return self.respond({'error':'Rota não encontrada.'},404)
                if user['role']=='viewer':
                    return self.respond({'error':'Seu perfil permite apenas consultas.'},403)
                match = re.fullmatch(r'/api/(products|suppliers|orders)(?:/(\d+))?(?:/(active|complete|cancel))?', route)
                item_id = None
                if route == '/api/movements':
                    store.movement(data)
                elif match:
                    kind, identifier, action = match.groups()
                    item_id = int(identifier) if identifier else None
                    if action and item_id is None:
                        raise BusinessError('Identificador obrigatório.')
                    if action == 'active' and kind in ('products', 'suppliers'):
                        store.active(kind, item_id, data.get('active'))
                    elif action in ('complete', 'cancel') and kind == 'orders':
                        store.transition(item_id, action)
                    elif action is None:
                        method = {'products': store.product, 'suppliers': store.supplier, 'orders': store.order}[kind]
                        item_id = method(data, item_id)
                    else:
                        raise BusinessError('Operação inválida.')
                else:
                    return self.respond({'error': 'Rota não encontrada.'}, 404)
                return self.respond({'ok': True, 'id': item_id})
            except (BusinessError, ValueError, UnicodeError) as exc:
                return self.respond({'error': str(exc) if isinstance(exc, BusinessError) else 'JSON inválido.'}, 400)
            except sqlite3.Error:
                return self.respond({'error': 'Banco indisponível. Tente novamente.'}, 503)

    return Handler


def main():
    parser = argparse.ArgumentParser(description='Estoque e pedidos: servidor de desenvolvimento local')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--db', default=str(ROOT / 'data' / 'estoque.sqlite3'))
    parser.add_argument('--open-browser',action='store_true',help='Abre o navegador ao iniciar')
    args = parser.parse_args()
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(Store(args.db)))
    except OSError as exc:
        parser.exit(1,f'Não foi possível iniciar na porta {args.port}. Tente --port 8001. Detalhe: {exc}\n')
    print(f'Abra http://localhost:{args.port} no navegador. Para encerrar, pressione Ctrl+C.')
    if args.open_browser:
        threading.Timer(0.7,lambda:webbrowser.open(f'http://localhost:{args.port}')).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor encerrado.')
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
