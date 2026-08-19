"""Call-site shapes for the frozen inbound protocol."""

from typing import Optional

import base as base_module
from base import (
    Audit,
    Base,
    ClassReceiver,
    FinalClass,
    FinalMethod,
    Other,
    direct_target,
    imported_target as imported_alias,
    make_base,
    wrapped_target,
)


MODULE_VALUE = direct_target()


class ModuleAndClassBody:
    CLASS_VALUE = direct_target()


def use_direct() -> object:
    return direct_target()


def use_import_alias() -> str:
    return imported_alias()


def use_module_attribute() -> object:
    return base_module.direct_target()


def use_annotated(backend: Base) -> str:
    return backend.save()


def use_plain_forward(backend: "Base") -> str:
    return backend.save()


def use_imported_qualified(backend: base_module.Base) -> str:
    return backend.save()


def use_unsupported_union(backend: Base | Other) -> str:
    return backend.save()


def use_quoted_optional(backend: "Base | None") -> str:
    return backend.save()


def use_optional(backend: Optional[Base]) -> str:
    return backend.save()


def use_unrelated(audit: Audit) -> str:
    return audit.save()


def use_factory_result() -> str:
    return make_base().save()


def use_subscript(backends: list[Base]) -> str:
    return backends[0].save()


def use_attribute_chain(holder: object) -> str:
    return holder.backend.save()


def use_dynamic_attribute(holder: object, name: str) -> object:
    return getattr(holder, name)()


def use_dynamic_import() -> object:
    return __import__("base")


def use_exec() -> object:
    return exec("pass")


def use_external(values: list[object]) -> int:
    return len(values)


def use_nested() -> object:
    return direct_target(imported_alias())


def use_default(value: object = direct_target()) -> object:
    return value


def use_cls() -> str:
    return ClassReceiver.call()


def use_static() -> str:
    return ClassReceiver.static_build()


def use_final_class() -> str:
    return FinalClass().call()


def use_final_method() -> str:
    return FinalMethod().call()


def use_wrapped() -> str:
    return wrapped_target()


def use_unknown() -> object:
    return unknown_function()
