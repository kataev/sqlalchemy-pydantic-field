import typing

import pydantic
from sqlalchemy import JSON, UnicodeText
from sqlalchemy.types import TypeDecorator, TypeEngine

if typing.TYPE_CHECKING:
    from sqlalchemy.engine.default import DefaultDialect  # noqa: F401  # pylint: disable=unused-import
    from sqlalchemy.sql.type_api import TypeEngine  # noqa: F401  # pylint: disable=unused-import

__all__ = ['PydanticField']


class PydanticField(TypeDecorator):  # pylint: disable=abstract-method
    def process_literal_param(self, value: typing.Any, dialect: 'DefaultDialect') -> typing.Any:
        """Re-use of process_bind_param."""
        return self.process_bind_param(value, dialect)

    impl = TypeEngine  # Special placeholder

    def __init__(  # pylint: disable=keyword-arg-before-vararg
        self,
        model: typing.Type[pydantic.BaseModel],
        json_type: 'TypeEngine' = JSON,
        *args, **kwargs
    ) -> None:
        self._model = model
        self._json_type = json_type
        super().__init__(*args, **kwargs)

    def _use_json(self, dialect: 'DefaultDialect') -> bool:
        """Helper to determine, which encoder to use."""
        return hasattr(dialect, "_json_serializer")

    def load_dialect_impl(self, dialect: 'DefaultDialect') -> 'TypeEngine':
        """Select impl by dialect."""
        if self._use_json(dialect):
            return dialect.type_descriptor(self._json_type)
        return dialect.type_descriptor(UnicodeText)

    def process_bind_param(self, value: pydantic.BaseModel, dialect: 'DefaultDialect') -> typing.Union[str, typing.Any]:
        """Encode data, if required."""
        if value is None:
            return value

        return value.json()

    def process_result_value(
        self,
        value: typing.Union[str, typing.Any],
        dialect: 'DefaultDialect'
    ) -> typing.Any:
        """Decode data, if required."""
        if value is None:
            return value

        return self._model.parse_raw(value, allow_pickle=False)
