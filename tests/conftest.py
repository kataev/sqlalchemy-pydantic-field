import os
import typing
from contextlib import contextmanager
from types import SimpleNamespace

import pydantic
import pytest
import sqlalchemy as sa
from sqlalchemy import MetaData
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.orm import sessionmaker

from sqlalchemy_pydantic_field import MutationTrackingPydanticField


@pytest.fixture()
def db_url() -> URL:
    return make_url(os.environ.get('DB_URL', 'sqlite:///:memory:'))


class DBNamespace(SimpleNamespace):
    if typing.TYPE_CHECKING:
        Author: Author
        Book: Book

        Schema: Schema
        ListSchema: ListSchema

        session: session
        metadata: MetaData


@pytest.fixture()
def db(db_url) -> DBNamespace:
    engine = sa.create_engine(db_url)
    Base.metadata.bind = engine
    Base.metadata.drop_all()
    Base.metadata.create_all()

    yield DBNamespace(
        Author=Author,
        Schema=Schema,
        session=session,
        metadata=Base.metadata,
        ListSchema=ListSchema,
        Book=Book,
    )
    Base.metadata.drop_all()


Session = sessionmaker()


@contextmanager
def session(**kwargs) -> typing.ContextManager[Session]:
    """Provide a transactional scope around a series of operations."""
    new_session = Session(**kwargs)
    try:
        yield new_session
        new_session.commit()
    except Exception:
        new_session.rollback()
        raise
    finally:
        new_session.close()


@as_declarative(metadata=sa.MetaData())
class Base:
    pass


class Schema(pydantic.BaseModel):
    text: str
    year: int
    ids: typing.List[int]
    meta: typing.Dict[str, str]


class ListSchema(pydantic.BaseModel):
    __root__: typing.List[int]


class Author(Base):
    __tablename__ = 'author'

    id = sa.Column('author_id', sa.Integer, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    data = sa.Column(MutationTrackingPydanticField(Schema, json_type=JSON))

    def __init__(self, name: str, data: Schema):
        self.name = name
        self.data = data


class Book(Base):
    __tablename__ = 'book'

    id = sa.Column('book_id', sa.Integer, primary_key=True)
    pages = sa.Column(
        MutationTrackingPydanticField(ListSchema, json_type=JSON)
    )


@pytest.fixture()
def list_data(db) -> ListSchema:
    return db.ListSchema(__root__=[1, 2, 3, 4])


@pytest.fixture()
def book_id(db, list_data) -> int:
    book = db.Book(pages=list_data)

    with db.session() as s:
        s.add(book)
        s.flush()
        return book.id


@pytest.fixture()
def data(db) -> Schema:
    return db.Schema(
        text='hello', year=2019, ids=[1, 2, 3], meta={'foo': 'bar'}
    )


@pytest.fixture()
def author_id(db, data) -> int:
    author = db.Author('test', data)

    with db.session() as s:
        s.add(author)
        s.flush()
        return author.id
