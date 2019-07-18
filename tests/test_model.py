import json

import pytest


@pytest.fixture()
def data(db):
    return db.Schema(text='hello',
                     year=2019,
                     ids=[1, 2, 3],
                     meta={'foo': 'bar'})


def test_marshalling(db, data):
    author = db.Author('test', data)

    with db.session() as s:
        s.add(author)
        s.flush()
        author_id = author.id

    with db.session() as s:
        author = s.query(db.Author).get(author_id)
        assert author.data == data
        assert not (author.data is data)

        field, = db.metadata.bind.execute('select data from author').fetchone()

        result = json.loads(field)

        assert isinstance(result, dict)


def test_mutable(db, data):
    author = db.Author('test', data)

    with db.session() as s:
        s.add(author)
        s.flush()
        author_id = author.id

    with db.session() as s:
        author = s.query(db.Author).get(author_id)
        author.data.year = 1989

    with db.session() as s:
        author = s.query(db.Author).get(author_id)
        assert author.data.year != 2019


def test_mutable_nested(db, data):
    author = db.Author('test', data)

    with db.session() as s:
        s.add(author)
        s.flush()
        author_id = author.id

    some_value = '4'

    with db.session() as s:
        author = s.query(db.Author).get(author_id)
        author.data.ids.append(some_value)

    with db.session() as s:
        author = s.query(db.Author).get(author_id)
        assert some_value in author.data.ids
