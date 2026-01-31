from fastapi.testclient import TestClient
from financial.main import app, engine, ReceiptItem
from sqlmodel import SQLModel, Session, select
from sqlalchemy import delete

# Ensure DB tables exist for tests
SQLModel.metadata.create_all(engine)
client = TestClient(app)


def test_recalculate_categories_endpoint():
    # seed some items with blank category
    with Session(engine) as s:
        # use a delete() expression to clear the table
        s.exec(delete(ReceiptItem))
        s.commit()
        s.add(ReceiptItem(transaction_id=1, name='Starbucks Latte', price=3.5, category=None))
        s.add(ReceiptItem(transaction_id=1, name='BP Petrol', price=40.0, category=None))
        s.add(ReceiptItem(transaction_id=1, name='Spotify Subscription', price=9.99, category=None))
        s.commit()

    # set admin token for test and include header
    import os
    prev = os.environ.get('ADMIN_TOKEN')
    try:
        os.environ['ADMIN_TOKEN'] = 'testtoken'
        headers = {'X-Admin-Token': 'testtoken'}
        r = client.post('/admin/recalculate_categories', headers=headers)
        assert r.status_code == 200
    finally:
        # restore previous env value to avoid leaking into other tests
        if prev is None:
            os.environ.pop('ADMIN_TOKEN', None)
        else:
            os.environ['ADMIN_TOKEN'] = prev

    # wait a short time for the background job to complete (it runs synchronously in tests)
    import time
    for _ in range(20):
        with Session(engine) as s:
            items = s.exec(select(ReceiptItem)).all()
            cats = [getattr(it, 'category', None) for it in items]
            if all(cats):
                break
        time.sleep(0.1)

    # confirm categories persisted
    with Session(engine) as s:
        items = s.exec(select(ReceiptItem)).all()
        cats = [getattr(it, 'category', '').lower() for it in items]
        assert 'coffee' in cats
        assert 'fuel' in cats
        assert 'subscription' in cats
