"""Regras de negócio e persistência. Valores monetários sempre em centavos."""
import sqlite3
from contextlib import contextmanager, closing
from pathlib import Path


class BusinessError(ValueError):
    pass


def integer(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= 100_000_000:
        raise BusinessError(f'{label}: informe um inteiro entre {minimum} e 100.000.000.')
    return value


def text(value, label, required=True, limit=160):
    if not isinstance(value, str):
        raise BusinessError(f'{label}: texto inválido.')
    value = value.strip()
    if (required and not value) or len(value) > limit:
        raise BusinessError(f'{label}: preencha até {limit} caracteres.')
    return value


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS suppliers (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL,
                    contact TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)));
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY, sku TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    name TEXT NOT NULL, supplier_id INTEGER REFERENCES suppliers(id),
                    price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
                    minimum INTEGER NOT NULL CHECK(minimum >= 0),
                    stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
                    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)));
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY, customer TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','completed','cancelled')),
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(id),
                    product_id INTEGER NOT NULL REFERENCES products(id),
                    name TEXT NOT NULL, sku TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK(quantity > 0),
                    price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
                    UNIQUE(order_id, product_id));
                CREATE TABLE IF NOT EXISTS movements (
                    id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(id),
                    order_id INTEGER REFERENCES orders(id), quantity INTEGER NOT NULL CHECK(quantity != 0),
                    balance INTEGER NOT NULL CHECK(balance >= 0), reason TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
                CREATE INDEX IF NOT EXISTS movement_product ON movements(product_id);
                CREATE INDEX IF NOT EXISTS item_order ON order_items(order_id);
            ''')

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        return db

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            # Serializa os escritores antes de consultar saldos/status.
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except sqlite3.IntegrityError as exc:
            db.rollback()
            raise BusinessError('Dados em conflito. Verifique se o SKU já está cadastrado.') from exc
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def require(db, table, item_id):
        # table é sempre uma constante interna, nunca entrada da API.
        row = db.execute(f'SELECT * FROM {table} WHERE id=?', (integer(item_id, 'Identificador', 1),)).fetchone()
        if row is None:
            raise BusinessError('Registro não encontrado.')
        return row

    def supplier(self, data, item_id=None):
        name = text(data.get('name'), 'Nome')
        contact = text(data.get('contact', ''), 'Contato', False)
        with self.transaction() as db:
            if item_id is None:
                return db.execute('INSERT INTO suppliers(name,contact) VALUES (?,?)', (name, contact)).lastrowid
            self.require(db, 'suppliers', item_id)
            db.execute('UPDATE suppliers SET name=?,contact=? WHERE id=?', (name, contact, item_id))
            return item_id

    def product(self, data, item_id=None):
        sku = text(data.get('sku'), 'SKU', limit=40).upper()
        name = text(data.get('name'), 'Nome')
        price = integer(data.get('price_cents'), 'Preço em centavos')
        minimum = integer(data.get('minimum'), 'Estoque mínimo')
        supplier = data.get('supplier_id')
        with self.transaction() as db:
            if supplier is not None:
                row = self.require(db, 'suppliers', supplier)
                old = self.require(db, 'products', item_id) if item_id else None
                if not row['active'] and (old is None or old['supplier_id'] != supplier):
                    raise BusinessError('Escolha um fornecedor ativo.')
            values = (sku, name, supplier, price, minimum)
            if item_id is None:
                return db.execute('INSERT INTO products(sku,name,supplier_id,price_cents,minimum) VALUES (?,?,?,?,?)', values).lastrowid
            self.require(db, 'products', item_id)
            db.execute('UPDATE products SET sku=?,name=?,supplier_id=?,price_cents=?,minimum=? WHERE id=?', (*values, item_id))
            return item_id

    def active(self, kind, item_id, active):
        if kind not in ('products', 'suppliers') or not isinstance(active, bool):
            raise BusinessError('Alteração de status inválida.')
        with self.transaction() as db:
            self.require(db, kind, item_id)
            db.execute(f'UPDATE {kind} SET active=? WHERE id=?', (int(active), item_id))

    @staticmethod
    def change_stock(db, product_id, quantity, reason, order_id=None):
        row = Store.require(db, 'products', product_id)
        balance = row['stock'] + quantity
        if balance < 0:
            raise BusinessError(f'Estoque insuficiente para {row["name"]}. Disponível: {row["stock"]}.')
        if balance > 100_000_000:
            raise BusinessError('Saldo acima do limite permitido.')
        db.execute('UPDATE products SET stock=? WHERE id=?', (balance, product_id))
        db.execute('INSERT INTO movements(product_id,order_id,quantity,balance,reason) VALUES (?,?,?,?,?)',
                   (product_id, order_id, quantity, balance, reason))

    def movement(self, data):
        quantity = integer(data.get('quantity'), 'Quantidade', 1)
        kind = data.get('kind')
        if kind not in ('in', 'out'):
            raise BusinessError('Tipo de movimentação inválido.')
        reason = text(data.get('reason'), 'Motivo', limit=240)
        with self.transaction() as db:
            product = self.require(db, 'products', data.get('product_id'))
            if not product['active']:
                raise BusinessError('Reative o produto para movimentá-lo manualmente.')
            self.change_stock(db, product['id'], quantity if kind == 'in' else -quantity, reason)

    def order(self, data, item_id=None):
        customer = text(data.get('customer'), 'Cliente')
        items = data.get('items')
        if not isinstance(items, list) or not 1 <= len(items) <= 100:
            raise BusinessError('Inclua entre 1 e 100 itens no pedido.')
        with self.transaction() as db:
            if item_id is None:
                item_id = db.execute('INSERT INTO orders(customer) VALUES (?)', (customer,)).lastrowid
            else:
                order = self.require(db, 'orders', item_id)
                if order['status'] != 'draft':
                    raise BusinessError('Somente rascunhos podem ser editados.')
                db.execute('UPDATE orders SET customer=? WHERE id=?', (customer, item_id))
            # Preserva preços previamente negociados para produtos já presentes no rascunho.
            old_prices = {r['product_id']: r['price_cents'] for r in db.execute('SELECT * FROM order_items WHERE order_id=?', (item_id,))}
            normalized = {}
            for item in items:
                if not isinstance(item, dict):
                    raise BusinessError('Item inválido.')
                product = self.require(db, 'products', item.get('product_id'))
                if not product['active']:
                    raise BusinessError(f'Produto inativo: {product["name"]}.')
                qty = integer(item.get('quantity'), 'Quantidade', 1)
                total = normalized.get(product['id'], (product, 0))[1] + qty
                integer(total, 'Quantidade total', 1)
                normalized[product['id']] = (product, total)
            db.execute('DELETE FROM order_items WHERE order_id=?', (item_id,))
            if sum(qty * old_prices.get(p['id'], p['price_cents']) for p, qty in normalized.values()) > 100_000_000_000:
                raise BusinessError('Total do pedido acima do limite de demonstração (R$ 1 bilhão).')
            for product, qty in normalized.values():
                db.execute('INSERT INTO order_items(order_id,product_id,name,sku,quantity,price_cents) VALUES (?,?,?,?,?,?)',
                           (item_id, product['id'], product['name'], product['sku'], qty, old_prices.get(product['id'], product['price_cents'])))
            return item_id

    def transition(self, item_id, action):
        if action not in ('complete', 'cancel'):
            raise BusinessError('Ação inválida.')
        with self.transaction() as db:
            order = self.require(db, 'orders', item_id)
            items = db.execute('SELECT * FROM order_items WHERE order_id=?', (item_id,)).fetchall()
            if action == 'complete':
                if order['status'] != 'draft':
                    raise BusinessError('Somente um rascunho pode ser finalizado.')
                for item in items:
                    product = self.require(db, 'products', item['product_id'])
                    if not product['active']:
                        raise BusinessError(f'Produto inativo: {product["name"]}.')
                    self.change_stock(db, item['product_id'], -item['quantity'], 'Finalização do pedido', item_id)
                status = 'completed'
            else:
                if order['status'] == 'cancelled':
                    raise BusinessError('Pedido já cancelado.')
                if order['status'] == 'completed':
                    for item in items:
                        self.change_stock(db, item['product_id'], item['quantity'], 'Estorno por cancelamento', item_id)
                status = 'cancelled'
            db.execute('UPDATE orders SET status=? WHERE id=?', (status, item_id))

    def snapshot(self):
        db = self.connect()
        try:
            db.execute('BEGIN')
            result = {table: [dict(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY id DESC')]
                      for table in ('products', 'suppliers', 'orders', 'movements')}
            all_items = [dict(r) for r in db.execute('SELECT * FROM order_items ORDER BY id')]
            by_order = {}
            for item in all_items:
                by_order.setdefault(item['order_id'], []).append(item)
            for order in result['orders']:
                order['items'] = by_order.get(order['id'], [])
                order['total_cents'] = sum(i['quantity'] * i['price_cents'] for i in order['items'])
            return result
        finally:
            db.close()
