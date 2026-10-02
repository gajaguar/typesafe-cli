from __future__ import annotations

import dataclasses
import functools
import inspect
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from collections.abc import Callable


def _parameter(field: dataclasses.Field[object], annotation: object) -> inspect.Parameter:
    default = inspect.Parameter.empty if field.default is dataclasses.MISSING else field.default
    return inspect.Parameter(field.name, inspect.Parameter.KEYWORD_ONLY, default=default, annotation=annotation)


# Typer builds a command from the callback's signature, so every option must be a parameter. This
# fabricates that signature from a dataclass and hands the callback one options object instead,
# which keeps commands within the argument limit without dropping any flag.
def options_from[T, R](options: type[T]) -> Callable[[Callable[[typer.Context, T], R]], Callable[..., R]]:
    # Walk the MRO so an options dataclass can extend a shared base of common flags.
    annotations: dict[str, object] = {}
    for klass in reversed(options.__mro__):
        annotations.update(inspect.get_annotations(klass, eval_str=True))
    context = inspect.Parameter("ctx", inspect.Parameter.KEYWORD_ONLY, annotation=typer.Context)
    fields = dataclasses.fields(options)  # type: ignore[arg-type]
    parameters = [context, *(_parameter(field, annotations[field.name]) for field in fields)]
    signature = inspect.Signature(parameters)

    def decorate(func: Callable[[typer.Context, T], R]) -> Callable[..., R]:
        @functools.wraps(func)
        def wrapper(*, ctx: typer.Context, **values: object) -> R:
            return func(ctx, options(**values))

        wrapper.__signature__ = signature  # type: ignore[attr-defined]
        wrapper.__annotations__ = {parameter.name: parameter.annotation for parameter in parameters}
        del wrapper.__wrapped__
        return wrapper

    return decorate
