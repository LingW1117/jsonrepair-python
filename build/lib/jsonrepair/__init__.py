import sys
import types

from .error import JSONRepairError
from .json_repair import extract_json, jsonrepair


class _CallableModule(types.ModuleType):
    """A module that can be called directly: ``import jsonrepair`` then
    ``jsonrepair(text)``, equivalent to ``jsonrepair.jsonrepair(text)``."""

    def __call__(self, text: str) -> str:
        return jsonrepair(text)


sys.modules[__name__].__class__ = _CallableModule

__all__ = ["jsonrepair", "extract_json", "JSONRepairError"]
