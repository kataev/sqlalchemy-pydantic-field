import json

import pytest


@pytest.fixture()
def data(db):
    return db.Schema(
        text='hello', year=2019, ids=[1, 2, 3], meta={'foo': 'bar'}
    )


@pytest.fixture()
def list_data(db):
    return db.ListSchema(__root__=[1, 2, 3, 4])


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


def test_marshalling_list(db, list_data):
    book = db.Book(pages=list_data)

    with db.session() as s:
        s.add(book)
        s.flush()
        book_id = book.id

    with db.session() as s:
        book = s.query(db.Book).get(book_id)
        assert book.pages == list_data
        assert not (book.pages is list_data)

        field, = db.metadata.bind.execute('select pages from book').fetchone()

        result = json.loads(field)

        assert isinstance(result, list)


def test_mutable_attr_list(db, list_data):
    book = db.Book(pages=list_data)

    with db.session() as s:
        s.add(book)
        s.flush()
        book_id = book.id

    extra_page = 10
    with db.session() as s:
        book = s.query(db.Book).get(book_id)
        book.pages.__root__.append(extra_page)
        assert book in s.dirty

    with db.session() as s:
        book = s.query(db.Book).get(book_id)
        assert extra_page in book.pages.__root__


def test_mutable_attr(db, data):
    author = db.Author('test', data)

    with db.session() as s:
        s.add(author)
        s.flush()
        author_id = author.id

    with db.session() as s:
        author = s.query(db.Author).get(author_id)
        author.data.year = 1989
        assert author in s.dirty

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
        assert author in s.dirty

    with db.session() as s:
        author = s.query(db.Author).get(author_id)
        assert some_value in author.data.ids
