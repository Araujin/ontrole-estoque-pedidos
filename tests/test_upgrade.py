import sqlite3
import tempfile
import unittest
from pathlib import Path
from domain import Store
from auth import Auth
from manage import backup


class UpgradeTests(unittest.TestCase):
    def test_upgrade_preserves_data_and_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'old.sqlite3'
            old=Store(path)
            old.product({'sku':'ANTIGO','name':'Produto anterior','price_cents':100,'minimum':2})
            auth=Auth(old)
            self.assertTrue(auth.needs_setup())
            self.assertEqual(old.snapshot()['products'][0]['sku'],'ANTIGO')
            with old.connect() as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],2)
            copy=Path(tmp)/'backup.sqlite3'
            backup(path,copy)
            self.assertEqual(Store(copy).snapshot(),old.snapshot())
