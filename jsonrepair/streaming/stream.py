from typing import Callable, Generator, Iterable, Union

from .core import JsonRepairCore


def jsonrepair_stream(
    chunks: Iterable[str],
    buffer_size: int = 65536,
    chunk_size: int = 65536,
) -> Generator[str, None, None]:
    """Generator that yields repaired JSON chunks from an iterable of input chunks.

    Usage:
        for repaired_chunk in jsonrepair_stream(input_chunks):
            print(repaired_chunk, end='')
    """
    output_chunks: list[str] = []

    def on_data(chunk: str) -> None:
        output_chunks.append(chunk)

    repair = JsonRepairCore(
        on_data=on_data,
        buffer_size=buffer_size,
        chunk_size=chunk_size,
    )

    for chunk in chunks:
        repair.transform(chunk)
        while output_chunks:
            yield output_chunks.pop(0)

    repair.flush()
    while output_chunks:
        yield output_chunks.pop(0)
