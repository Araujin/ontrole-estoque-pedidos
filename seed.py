"""Carrega somente dados fictícios, recusando um banco que já possui registros."""
from pathlib import Path
from domain import Store


def seed(store):
    state = store.snapshot()
    if any(state.values()):
        raise SystemExit('O banco já possui dados. Nenhum registro foi alterado.')
    supplier = store.supplier({'name': 'Fornecedor Horizonte (fictício)', 'contact': 'contato@example.com'})
    products = []
    for sku, name, price, minimum, stock in [
        ('DEMO-001', 'Teclado compacto', 12990, 5, 18),
        ('DEMO-002', 'Mouse sem fio', 7990, 8, 4),
        ('DEMO-003', 'Suporte para notebook', 8990, 4, 12),
        ('DEMO-004', 'Cabo USB-C', 2990, 10, 0),
    ]:
        product = store.product({'sku': sku, 'name': name, 'price_cents': price, 'minimum': minimum, 'supplier_id': supplier})
        products.append(product)
        if stock:
            store.movement({'product_id': product, 'quantity': stock, 'kind': 'in', 'reason': 'Carga inicial fictícia'})
    order = store.order({'customer': 'Cliente Aurora (fictício)', 'items': [{'product_id': products[0], 'quantity': 2}, {'product_id': products[2], 'quantity': 1}]})
    store.transition(order, 'complete')
    store.order({'customer': 'Cliente Jardim (fictício)', 'items': [{'product_id': products[1], 'quantity': 2}]})
    print('Exemplo carregado. Execute python app.py e abra http://localhost:8000')


if __name__ == '__main__':
    seed(Store(Path(__file__).resolve().parent / 'data' / 'estoque.sqlite3'))
