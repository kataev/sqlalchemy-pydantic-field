import typing

import pydantic
from sqlalchemy import JSON, UnicodeText, event
from sqlalchemy.ext.mutable import Mutable, MutableDict
from sqlalchemy.types import TypeDecorator, TypeEngine

if typing.TYPE_CHECKING:
    from sqlalchemy.engine.default import (
        DefaultDialect,
    )  # noqa: F401  # pylint: disable=unused-import
    from sqlalchemy.sql.type_api import (
        TypeEngine,
    )  # noqa: F401  # pylint: disable=unused-import

__all__ = ['PydanticField']


@classmethod
def _listen_on_attribute(cls, attribute, coerce, parent_cls):
    """Establish this type as a mutation listener for the given
    mapped descriptor.

    """
    key = attribute.key
    if parent_cls is not attribute.class_:
        return

    # rely on "propagate" here
    parent_cls = attribute.class_

    listen_keys = cls._get_listen_keys(attribute)

    def load(state, *args):
        """Listen for objects loaded or refreshed.

        Wrap the target data member's value with
        ``Mutable``.

        """
        val = state.dict.get(key, None)
        if val is not None:
            if coerce:
                val = cls.coerce(key, val)
                state.dict[key] = val
            if hasattr(val, '__dict__') and hasattr(val.__dict__, '_parents'):
                val.__dict__._parents[state.obj()] = key
            else:
                val._parents[state.obj()] = key

    def load_attrs(state, ctx, attrs):
        if not attrs or listen_keys.intersection(attrs):
            load(state)

    def set_(target, value, oldvalue, initiator):
        """Listen for set/replace events on the target
        data member.

        Establish a weak reference to the parent object
        on the incoming value, remove it for the one
        outgoing.

        """
        if value is oldvalue:
            return value

        if not isinstance(value, cls):
            value = cls.coerce(key, value)
        if value is not None:
            if hasattr(value, '__dict__') and hasattr(
                value.__dict__, '_parents'
            ):
                value.__dict__._parents[target.obj()] = key
            else:
                value._parents[target.obj()] = key
        if isinstance(oldvalue, cls):
            oldvalue._parents.pop(target.obj(), None)
        return value

    def pickle(state, state_dict):
        val = state.dict.get(key, None)
        if val is not None:
            if 'ext.mutable.values' not in state_dict:
                state_dict['ext.mutable.values'] = []
            state_dict['ext.mutable.values'].append(val)

    def unpickle(state, state_dict):
        if 'ext.mutable.values' in state_dict:
            for val in state_dict['ext.mutable.values']:
                val._parents[state.obj()] = key

    event.listen(parent_cls, 'load', load, raw=True, propagate=True)
    event.listen(parent_cls, 'refresh', load_attrs, raw=True, propagate=True)
    event.listen(
        parent_cls, 'refresh_flush', load_attrs, raw=True, propagate=True
    )
    event.listen(attribute, 'set', set_, raw=True, retval=True, propagate=True)
    event.listen(parent_cls, 'pickle', pickle, raw=True, propagate=True)
    event.listen(parent_cls, 'unpickle', unpickle, raw=True, propagate=True)


class PydanticField(TypeDecorator):  # pylint: disable=abstract-method
    impl = TypeEngine  # Special placeholder

    def __init__(  # pylint: disable=keyword-arg-before-vararg
        self,
        model: typing.Type[pydantic.BaseModel],
        json_type: typing.Type['TypeEngine'] = JSON,
        *args,
        **kwargs,
    ) -> None:
        self._model = model
        self._json_type = json_type

        super().__init__(*args, **kwargs)

        @classmethod
        def coerce(cls, key, value):
            if value is None:
                return None
            if isinstance(value, model):
                # breakpoint()
                object.__setattr__(
                    value, '__dict__', MutableDict(value.__dict__)
                )
                return value
            msg = "Attribute '%s' does not accept objects of type %s"
            raise ValueError(msg % (key, type(value)))

        self.mutable = type(
            f'MutablePydanticModel{model.__name__}',
            (Mutable,),
            {'coerce': coerce, '_listen_on_attribute': _listen_on_attribute},
        )
        self.mutable.as_mutable(self)

    def load_dialect_impl(self, dialect: 'DefaultDialect') -> 'TypeEngine':
        """Select impl by dialect."""
        return dialect.type_descriptor(UnicodeText)

    def process_bind_param(
        self, value: pydantic.BaseModel, dialect: 'DefaultDialect'
    ) -> typing.Union[str, typing.Any]:
        """Encode data, if required."""
        if value is None:
            return value

        return value.json()

    def process_result_value(
        self, value: typing.Union[str, typing.Any], dialect: 'DefaultDialect'
    ) -> typing.Any:
        """Decode data, if required."""
        if value is None:
            return value

        data = self._model.parse_raw(value, allow_pickle=False)
        return data

    def process_literal_param(
        self, value: typing.Any, dialect: 'DefaultDialect'
    ) -> typing.Any:
        """Re-use of process_bind_param."""
        return self.process_bind_param(value, dialect)
