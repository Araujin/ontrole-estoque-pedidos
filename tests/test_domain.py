import concurrent.futures
import sqlite3
import tempfile
import unittest
from pathlib import Path
from domain import Store, BusinessError


class BusinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'test.sqlite3')
        self.product = self.store.product({'name':'Produto A','sku':'A','price_cents':1250,'minimum':2})
        self.store.movement({'product_id':self.product,'kind':'in','quantity':10,'reason':'Compra'})

    def order(self, quantity=3, extra=None):
        return self.store.order({'customer':'Cliente fictício','items':[{'product_id':self.product,'quantity':quantity}]+(extra or [])})

    def stock(self):
        return next(p['stock'] for p in self.store.snapshot()['products'] if p['id']==self.product)

    def test_negative_stock_is_rejected(self):
        with self.assertRaises(BusinessError):
            self.store.movement({'product_id':self.product,'kind':'out','quantity':11,'reason':'Saída'})
        self.assertEqual(self.stock(),10)
        self.assertEqual(len(self.store.snapshot()['movements']),1)

    def test_draft_complete_cancel_and_no_double_return(self):
        order = self.order()
        self.assertEqual(self.stock(),10)
        self.store.transition(order,'complete')
        self.assertEqual(self.stock(),7)
        with self.assertRaises(BusinessError): self.store.transition(order,'complete')
        self.store.transition(order,'cancel')
        self.assertEqual(self.stock(),10)
        with self.assertRaises(BusinessError): self.store.transition(order,'cancel')
        self.assertEqual(self.stock(),10)
        self.assertEqual(len(self.store.snapshot()['movements']),3)

    def test_multi_item_failure_rolls_back_every_change(self):
        second = self.store.product({'name':'Sem estoque','sku':'B','price_cents':100,'minimum':0})
        order = self.order(extra=[{'product_id':second,'quantity':1}])
        with self.assertRaises(BusinessError): self.store.transition(order,'complete')
        state = self.store.snapshot()
        self.assertEqual(self.stock(),10)
        self.assertEqual(len(state['movements']),1)
        self.assertEqual(state['orders'][0]['status'],'draft')

    def test_cancel_draft_does_not_increase_stock(self):
        self.store.transition(self.order(),'cancel')
        self.assertEqual(self.stock(),10)

    def test_duplicate_lines_are_merged(self):
        order = self.order(2,[{'product_id':self.product,'quantity':3}])
        self.assertEqual(len(self.store.snapshot()['orders'][0]['items']),1)
        self.store.transition(order,'complete')
        self.assertEqual(self.stock(),5)

    def test_prices_are_frozen_in_order(self):
        order = self.order(2)
        self.store.product({'name':'Nome novo','sku':'A','price_cents':5000,'minimum':2},self.product)
        self.store.order({'customer':'Cliente','items':[{'product_id':self.product,'quantity':3}]},order)
        saved = self.store.snapshot()['orders'][0]
        self.assertEqual(saved['total_cents'],3750)

    def test_inactive_product_blocks_completion_but_allows_return(self):
        order = self.order()
        self.store.active('products',self.product,False)
        with self.assertRaises(BusinessError): self.store.transition(order,'complete')
        self.store.active('products',self.product,True)
        self.store.transition(order,'complete')
        self.store.active('products',self.product,False)
        self.store.transition(order,'cancel')
        self.assertEqual(self.stock(),10)

    def test_concurrent_orders_cannot_oversell(self):
        orders = [self.order(7),self.order(7)]
        def complete(order):
            try:
                self.store.transition(order,'complete')
                return True
            except BusinessError:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(complete,orders))
        self.assertEqual(sorted(results),[False,True])
        self.assertEqual(self.stock(),3)

    def test_supplier_and_unique_sku(self):
        supplier = self.store.supplier({'name':'Fornecedor','contact':'exemplo@example.com'})
        self.store.supplier({'name':'Atualizado','contact':''},supplier)
        self.assertEqual(self.store.snapshot()['suppliers'][0]['name'],'Atualizado')
        with self.assertRaises(BusinessError):
            self.store.product({'name':'Duplicado','sku':'a','price_cents':100,'minimum':0})
        self.store.active('suppliers',supplier,False)
        with self.assertRaises(BusinessError):
            self.store.product({'name':'Novo','sku':'Z','price_cents':100,'minimum':0,'supplier_id':supplier})

    def test_invalid_inputs_and_empty_order(self):
        for quantity in [-1,0,1.5,True,'2',None]:
            with self.subTest(quantity=quantity), self.assertRaises(BusinessError):
                self.store.movement({'product_id':self.product,'quantity':quantity,'kind':'in','reason':'Teste'})
        with self.assertRaises(BusinessError): self.store.order({'customer':'Cliente','items':[]})
        self.assertEqual(len(self.store.snapshot()['orders']),0)

    def test_invalid_edit_preserves_original_order(self):
        order = self.order(2)
        with self.assertRaises(BusinessError):
            self.store.order({'customer':'Mudou','items':[{'product_id':999,'quantity':1}]},order)
        saved = self.store.snapshot()['orders'][0]
        self.assertEqual(saved['customer'],'Cliente fictício')
        self.assertEqual(saved['items'][0]['quantity'],2)

    def test_completed_order_is_immutable(self):
        order = self.order()
        self.store.transition(order,'complete')
        with self.assertRaises(BusinessError):
            self.store.order({'customer':'Alterado','items':[{'product_id':self.product,'quantity':9}]},order)
        self.assertEqual(self.stock(),7)

    def test_ledger_matches_stock_and_persists(self):
        self.store.transition(self.order(2),'complete')
        reopened = Store(self.store.path).snapshot()
        self.assertEqual(reopened['products'][0]['stock'],8)
        self.assertEqual(sum(m['quantity'] for m in reopened['movements']),8)
        with self.store.connect() as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')


if __name__ == '__main__':
    unittest.main()
