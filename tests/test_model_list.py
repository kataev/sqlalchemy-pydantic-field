import json


def test_marshalling_list(db, list_data, book_id):
    with db.session() as s:
        book = s.query(db.Book).get(book_id)
        assert book.pages == list_data
        assert not (book.pages is list_data)

        field, = db.metadata.bind.execute('select pages from book').fetchone()

        result = json.loads(field)

        assert isinstance(result, list)


def test_mutable_attr_list(db, book_id):
    extra_page = 10

    with db.session() as s:
        book = s.query(db.Book).get(book_id)
        book.pages.__root__.append(extra_page)
        assert book in s.dirty

    with db.session() as s:
        book = s.query(db.Book).get(book_id)
        assert extra_page in book.pages.__root__
