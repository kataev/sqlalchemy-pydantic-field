import typing

import pydantic
from pydantic.class_validators import ROOT_KEY
from pydantic.fields import SHAPE_LIST, SHAPE_MAPPING, SHAPE_SET
from sqlalchemy import JSON, UnicodeText, event
from sqlalchemy.ext.mutable import Mutable, MutableDict, MutableList
from sqlalchemy.sql.sqltypes import Indexable
from sqlalchemy.types import TypeDecorator, TypeEngine

if typing.TYPE_CHECKING:
    from sqlalchemy.engine.default import (
        DefaultDialect,
    )  # noqa: F401  # pylint: disable=unused-import
    from sqlalchemy.sql.type_api import (
        TypeEngine,
    )  # noqa: F401  # pylint: disable=unused-import

__all__ = ['MutationTrackingPydanticField']


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

            if isinstance(val, pydantic.BaseModel):
                if not cls.model.__custom_root_type__:
                    val.__dict__._parents[state.obj()] = key
                else:
                    val.__root__._parents[state.obj()] = key
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
            if isinstance(value, pydantic.BaseModel):
                if not cls.model.__custom_root_type__:
                    value.__dict__._parents[target.obj()] = key
                else:
                    value.__root__._parents[target.obj()] = key
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


@classmethod
def coerce(cls, key, value):
    if value is None:
        return None
    if not isinstance(value, cls.model):
        msg = "Attribute '%s' does not accept objects of type %s"
        raise ValueError(msg % (key, type(value)))

    if not cls.model.__custom_root_type__:
        object.__setattr__(value, '__dict__', MutableDict(value.__dict__))
        return value

    root = cls.model.__fields__[ROOT_KEY]
    if root.shape == SHAPE_MAPPING:
        value.__dict__[ROOT_KEY] = MutableDict(value.__dict__[ROOT_KEY])
    elif root.shape == SHAPE_LIST:
        value.__dict__[ROOT_KEY] = MutableList(value.__dict__[ROOT_KEY])
    return value


class PydanticJsonPath:
    def __init__(self, model: typing.Type[pydantic.BaseModel]):
        self._model = model


class MutationTrackingPydanticField(
    TypeDecorator
):  # pylint: disable=abstract-method
    impl = TypeEngine  # Special placeholder

    @property
    def comparator_factory(self):
        return self._json_type.comparator_factory

    def __init__(  # pylint: disable=keyword-arg-before-vararg
        self,
        model: typing.Type[pydantic.BaseModel],
        json_type: typing.Type['TypeEngine'] = JSON,
        *args,
        **kwargs,
    ) -> None:
        self.path = PydanticJsonPath(model)
        self._model = model

        self._json_type = json_type

        super().__init__(*args, **kwargs)

        self.mutable = type(
            f'{model.__name__}MutationTrackingModel',
            (Mutable,),
            {
                'model': model,
                'coerce': coerce,
                '_listen_on_attribute': _listen_on_attribute,
            },
        )
        self.mutable.as_mutable(self)

    def load_dialect_impl(self, dialect: 'DefaultDialect') -> 'TypeEngine':
        """Select impl by dialect."""
        return dialect.type_descriptor(self._json_type)

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
