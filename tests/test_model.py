import json

from sqlalchemy.orm.attributes import flag_modified


def test_marshalling(db, data, author_id):
    with db.session() as s:
        author = s.query(db.Author).get(author_id)
        assert author.data == data
        assert not (author.data is data)

        field, = db.metadata.bind.execute('select data from author').fetchone()

        result = json.loads(field)

        assert isinstance(result, dict)


def test_mutable_attr(db, author_id):
    with db.session() as s:
        author = s.query(db.Author).get(author_id)
        author.data.year = 1989
        assert author in s.dirty

    with db.session() as s:
        author = s.query(db.Author).get(author_id)
        assert author.data.year != 2019


def test_mutable_attr_by_hand(db, author_id):
    with db.session() as s:
        author = s.query(db.Author).get(author_id)
        author.data.year = 1989
        flag_modified(author, 'data')
        assert author in s.dirty

    some_value = 4

    with db.session() as s:
        author = s.query(db.Author).get(author_id)
        assert author.data.year != 2019
        author.data.ids.append(some_value)
        flag_modified(author, 'data')
        assert author in s.dirty

    with db.session() as s:
        author = s.query(db.Author).get(author_id)
        assert some_value in author.data.ids


def test_mutable_nested(db, author_id):
    some_value = 4

    with db.session() as s:
        author = s.query(db.Author).get(author_id)
        author.data.ids.append(some_value)
        assert author in s.dirty

    with db.session() as s:
        author = s.query(db.Author).get(author_id)
        assert some_value in author.data.ids
