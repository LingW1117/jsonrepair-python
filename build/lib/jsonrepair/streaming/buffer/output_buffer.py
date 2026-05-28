from __future__ import annotations

from typing import Callable

from ...string_utils import is_whitespace_at


class OutputBuffer:
    """Sliding window output buffer for streaming JSON repair."""

    def __init__(
        self,
        write: Callable[[str], None],
        chunk_size: int,
        buffer_size: int,
    ):
        self._write = write
        self._chunk_size = chunk_size
        self._buffer_size = buffer_size
        self._buffer = ""
        self._offset = 0

    def _flush_chunks(self, min_size: int | None = None) -> None:
        if min_size is None:
            min_size = self._buffer_size
        while len(self._buffer) >= min_size + self._chunk_size:
            chunk = self._buffer[: self._chunk_size]
            self._write(chunk)
            self._offset += self._chunk_size
            self._buffer = self._buffer[self._chunk_size :]

    def flush(self) -> None:
        self._flush_chunks(0)
        if self._buffer:
            self._write(self._buffer)
            self._offset += len(self._buffer)
            self._buffer = ""

    def push(self, text: str) -> None:
        self._buffer += text
        self._flush_chunks()

    def unshift(self, text: str) -> None:
        if self._offset > 0:
            raise RuntimeError(
                "Cannot unshift: start of the output is already flushed from the buffer"
            )
        self._buffer = text + self._buffer
        self._flush_chunks()

    def remove(self, start: int, end: int | None = None) -> None:
        if start < self._offset:
            raise RuntimeError(
                "Cannot remove: start of the output is already flushed from the buffer"
            )
        if end is not None:
            self._buffer = (
                self._buffer[: start - self._offset]
                + self._buffer[end - self._offset :]
            )
        else:
            self._buffer = self._buffer[: start - self._offset]

    def insert_at(self, index: int, text: str) -> None:
        if index < self._offset:
            raise RuntimeError(
                "Cannot insert: start of the output is already flushed from the buffer"
            )
        rel = index - self._offset
        self._buffer = self._buffer[:rel] + text + self._buffer[rel:]

    def length(self) -> int:
        return self._offset + len(self._buffer)

    def strip_last_occurrence(
        self, text_to_strip: str, strip_remaining_text: bool = False
    ) -> None:
        buffer_index = self._buffer.rfind(text_to_strip)
        if buffer_index != -1:
            if strip_remaining_text:
                self._buffer = self._buffer[:buffer_index]
            else:
                self._buffer = (
                    self._buffer[:buffer_index]
                    + self._buffer[buffer_index + len(text_to_strip) :]
                )

    def insert_before_last_whitespace(self, text_to_insert: str) -> None:
        buffer_index = len(self._buffer)

        if not is_whitespace_at(self._buffer, buffer_index - 1):
            self.push(text_to_insert)
            return

        while buffer_index > 0 and is_whitespace_at(self._buffer, buffer_index - 1):
            buffer_index -= 1

        if buffer_index <= 0:
            raise RuntimeError(
                "Cannot insert: start of the output is already flushed from the buffer"
            )

        self._buffer = (
            self._buffer[:buffer_index]
            + text_to_insert
            + self._buffer[buffer_index:]
        )
        self._flush_chunks()

    def ends_with_ignoring_whitespace(self, char: str) -> bool:
        i = len(self._buffer) - 1
        while i > 0:
            if char == self._buffer[i]:
                return True
            if not is_whitespace_at(self._buffer, i):
                return False
            i -= 1
        return False
