from sqlalchemy.sql.elements import BinaryExpression


def test_mutable_nested(db):
    breakpoint()
    assert isinstance(db.Author.data['asd'] == 'asd', BinaryExpression)


def test_search_path(db):
    assert db.Schema.name == ('name')
