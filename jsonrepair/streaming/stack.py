from enum import Enum


class StackType(Enum):
    ROOT = "root"
    OBJECT = "object"
    ARRAY = "array"
    ND_JSON = "ndJson"
    FUNCTION_CALL = "functionCall"


class Caret(Enum):
    BEFORE_VALUE = "beforeValue"
    AFTER_VALUE = "afterValue"
    BEFORE_KEY = "beforeKey"


class Stack:
    def __init__(self):
        self._stack: list[StackType] = [StackType.ROOT]
        self._caret = Caret.BEFORE_VALUE

    @property
    def type(self) -> StackType:
        return self._stack[-1]

    @property
    def caret(self) -> Caret:
        return self._caret

    def pop(self) -> bool:
        self._stack.pop()
        self._caret = Caret.AFTER_VALUE
        return True

    def push(self, stack_type: StackType, caret: Caret) -> bool:
        self._stack.append(stack_type)
        self._caret = caret
        return True

    def update(self, caret: Caret) -> bool:
        self._caret = caret
        return True
