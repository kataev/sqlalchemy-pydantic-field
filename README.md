# sqlalchemy-pydantic-field

[![pypi](https://badge.fury.io/py/sqlalchemy-pydantic-field.svg)](https://pypi.org/project/sqlalchemy-pydantic-field)
[![Python: 3.6+](https://img.shields.io/badge/Python-3.6+-blue.svg)](https://pypi.org/project/sqlalchemy-pydantic-field)
[![Downloads](https://img.shields.io/pypi/dm/sqlalchemy-pydantic-field.svg)](https://pypistats.org/packages/sqlalchemy-pydantic-field)
[![Build Status](https://travis-ci.org/kataev/sqlalchemy-pydantic-field.svg?branch=master)](https://travis-ci.org/kataev/sqlalchemy-pydantic-field)
[![Code coverage](https://codecov.io/gh/kataev/sqlalchemy-pydantic-field/branch/master/graph/badge.svg)](https://codecov.io/gh/kataev/sqlalchemy-pydantic-field)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://en.wikipedia.org/wiki/MIT_License)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

## Description

Wrap sqlalchemy json field with pydantic models
NOTE: Not for production use (have a bug: wraps json in json on postgresql)

## Installation

    pip install sqlalchemy-pydantic-field

## Usage

```python
@as_declarative()
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

data = Schema(text='hello',
              year=2019,
              ids=[1, 2, 3],
              meta={'foo': 'bar'})
author = db.Author('test', data)

with db.session() as s:
    s.add(author)
```

## License

MIT

## Change Log

Unreleased
-----

* initial
