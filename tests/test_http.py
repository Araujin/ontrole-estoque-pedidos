import json
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.cookiejar import CookieJar
from urllib.request import build_opener, HTTPCookieProcessor
from app import handler_for
from domain import Store


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.server = ThreadingHTTPServer(('127.0.0.1',0),handler_for(Store(Path(self.tmp.name)/'http.db')))
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:'+str(self.server.server_port)
        self.addCleanup(self.stop)
        self.client = build_opener(HTTPCookieProcessor(CookieJar()))
        self.csrf = ''
        code,_ = self.post('/api/auth/setup',{'name':'Admin','username':'admin','password':'senha-segura-123'})
        self.assertEqual(code,200)
        with self.client.open(self.url+'/api/auth/me') as response:
            self.csrf = json.load(response)['user']['csrf']

    def stop(self):
        self.server.shutdown();self.server.server_close();self.thread.join()

    def post(self, path, data, origin=None):
        headers={'Content-Type':'application/json','X-CSRF-Token':self.csrf}
        if origin: headers['Origin']=origin
        req=Request(self.url+path,data=json.dumps(data).encode(),headers=headers)
        try:
            with self.client.open(req) as response: return response.status,json.load(response)
        except HTTPError as response:
            return response.code,json.load(response)

    def test_full_flow_over_http(self):
        code,created=self.post('/api/products',{'name':'Produto HTTP','sku':'HTTP','price_cents':990,'minimum':2})
        self.assertEqual(code,200)
        p=created['id']
        self.assertEqual(self.post('/api/movements',{'product_id':p,'kind':'in','quantity':6,'reason':'Compra'})[0],200)
        _,order=self.post('/api/orders',{'customer':'Teste','items':[{'product_id':p,'quantity':2}]})
        self.assertEqual(self.post(f'/api/orders/{order["id"]}/complete',{})[0],200)
        with self.client.open(self.url+'/api/state') as response: state=json.load(response)
        self.assertEqual(state['products'][0]['stock'],4)
        self.assertEqual(state['orders'][0]['total_cents'],1980)
        self.assertEqual(self.post(f'/api/orders/{order["id"]}/cancel',{})[0],200)

    def test_validation_and_cross_origin(self):
        self.assertEqual(self.post('/api/products',None)[0],400)
        self.assertEqual(self.post('/api/products',{},'https://example.com')[0],403)
        self.assertEqual(self.post('/api/unknown',{})[0],404)

    def test_static_assets(self):
        for path,content_type in [('/','text/html'),('/styles.css','text/css'),('/app.js','javascript')]:
            with urlopen(self.url+path) as response:
                self.assertEqual(response.status,200)
                self.assertIn(content_type,response.headers['Content-Type'])
                self.assertTrue(response.read())

    def test_auth_is_required(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(self.url+'/api/state')
        self.assertEqual(error.exception.code,401)

    def test_csrf_required(self):
        self.csrf='invalid'
        self.assertEqual(self.post('/api/products',{})[0],403)

    def test_viewer_cannot_write_or_manage_users(self):
        code,_=self.post('/api/users',{'name':'Consulta','username':'leitor','password':'leitor-seguro-123','role':'viewer'})
        self.assertEqual(code,200)
        self.post('/api/auth/logout',{})
        self.post('/api/auth/login',{'username':'leitor','password':'leitor-seguro-123'})
        with self.client.open(self.url+'/api/auth/me') as response:
            self.csrf=json.load(response)['user']['csrf']
        self.assertEqual(self.post('/api/products',{'name':'X','sku':'X','price_cents':100,'minimum':0})[0],403)
        self.assertEqual(self.post('/api/users',{})[0],403)
        with self.client.open(self.url+'/api/state') as response:
            self.assertEqual(response.status,200)

    def test_setup_cannot_be_repeated(self):
        self.assertEqual(self.post('/api/auth/setup',{'name':'Other','username':'other','password':'senha-segura-123'})[0],400)

    def test_password_change_revokes_session(self):
        self.assertEqual(self.post('/api/auth/password',{'current_password':'senha-segura-123','new_password':'outra-senha-123'})[0],200)
        with self.assertRaises(HTTPError) as error:
            self.client.open(self.url+'/api/state')
        self.assertEqual(error.exception.code,401)
        self.assertEqual(self.post('/api/auth/login',{'username':'admin','password':'outra-senha-123'})[0],200)

    def test_mime_types_ignore_os_registry(self):
        with urlopen(self.url+'/app.js') as response:
            self.assertTrue(response.headers['Content-Type'].startswith('text/javascript'))

    def test_cannot_disable_own_account(self):
        self.assertEqual(self.post('/api/users/1/active',{'active':False})[0],400)
