from typing import Optional


class InputBuffer:
    """Sliding window input buffer for streaming JSON repair."""

    def __init__(self):
        self._buffer = ""
        self._offset = 0
        self._current_length = 0
        self._closed = False

    def push(self, chunk: str) -> None:
        self._buffer += chunk
        self._current_length += len(chunk)

    def flush(self, position: int) -> None:
        if position > self._current_length:
            return
        self._buffer = self._buffer[position - self._offset :]
        self._offset = position

    def char_at(self, index: int) -> str:
        self._ensure(index)
        return self._buffer[index - self._offset]

    def char_code_at(self, index: int) -> int:
        self._ensure(index)
        return ord(self._buffer[index - self._offset])

    def substring(self, start: int, end: int) -> str:
        self._ensure(end - 1)
        self._ensure(start)
        return self._buffer[start - self._offset : end - self._offset]

    def length(self) -> int:
        if not self._closed:
            raise RuntimeError("Cannot get length: input is not yet closed")
        return self._current_length

    def current_length(self) -> int:
        return self._current_length

    def current_buffer_size(self) -> int:
        return len(self._buffer)

    def is_end(self, index: int) -> bool:
        if not self._closed:
            self._ensure(index)
        return index >= self._current_length

    def close(self) -> None:
        self._closed = True

    def _ensure(self, index: int) -> None:
        if index < self._offset:
            raise IndexError(
                f"Index out of range, please configure a larger buffer size "
                f"(index: {index}, offset: {self._offset})"
            )
        if index >= self._current_length:
            if not self._closed:
                raise IndexError(
                    f"Index out of range, please configure a larger buffer size "
                    f"(index: {index})"
                )
