import os
import typing
from typing import _alias, KT, VT
from contextlib import contextmanager
from types import SimpleNamespace

import pydantic
import pytest
import sqlalchemy as sa
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.ext.mutable import MutableList, MutableDict
from sqlalchemy.orm import sessionmaker

from sqlalchemy_pydantic_field import PydanticField


@pytest.fixture()
def db_url() -> URL:
    return make_url(os.environ.get('DB_URL', 'sqlite:///:memory:'))


@pytest.fixture()
def db(db_url):
    engine = sa.create_engine(db_url)
    Base.metadata.bind = engine
    Base.metadata.drop_all()
    Base.metadata.create_all()

    yield SimpleNamespace(Author=Author, Schema=Schema, session=session, metadata=Base.metadata)
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
    ids: MutableList
    meta: MutableDict

    class Config:
        validate_assignment = True


class Author(Base):
    __tablename__ = 'author'

    id = sa.Column('author_id', sa.Integer, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    data = sa.Column(PydanticField(Schema, json_type=JSON))

    def __init__(self, name: str, data: Schema):
        self.name = name
        self.data = data
