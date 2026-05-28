#!/usr/bin/env python3
"""CLI for jsonrepair - repair invalid JSON documents."""

import argparse
import os
import sys
import tempfile
from datetime import datetime

from .json_repair import jsonrepair
from .streaming.stream import jsonrepair_stream

HELP_TEXT = """
jsonrepair
https://github.com/josdejong/jsonrepair

Repair invalid JSON documents. When a document could not be repaired,
the output will be left unchanged.

Usage:
    jsonrepair [filename] {OPTIONS}

Options:
    --version, -v       Show application version
    --help,    -h       Show this message
    --output,  -o       Output file
    --overwrite         Overwrite the input file
    --buffer            Buffer size in bytes, for example 64K (default) or 1M

Example usage:
    jsonrepair broken.json                        # Repair a file, output to console
    jsonrepair broken.json > repaired.json        # Repair a file, output to file
    jsonrepair broken.json --output repaired.json # Repair a file, output to file
    jsonrepair broken.json --overwrite            # Repair a file, replace the file itself
    cat broken.json | jsonrepair                  # Repair data from an input stream
    cat broken.json | jsonrepair > repaired.json  # Repair data from an input stream, output to file
"""


def _parse_size(size_str: str) -> int:
    """Parse a size string like '64K', '2M', '1G' into bytes."""
    match = __import__("re").match(r"^(\d+)([KMG]?)$", size_str)
    if not match:
        raise ValueError(
            f'Buffer size "{size_str}" not recognized. Examples: 65536, 512K, 2M'
        )
    num = int(match.group(1))
    suffix = match.group(2)
    multipliers = {"K": 1024, "M": 1024**2, "G": 1024**3}
    return num * multipliers.get(suffix, 1)


def _process_file_overwrite(input_file: str, buffer_size: int) -> None:
    """Overwrite the input file with repaired JSON."""
    date_str = datetime.now().isoformat().replace(":", "-").replace(".", "-")
    temp_suffix = f".repair-{date_str}.json"
    temp_file = input_file + temp_suffix

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()

        repaired = jsonrepair(content)

        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(repaired)

        os.replace(temp_file, input_file)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        if os.path.exists(temp_file):
            os.unlink(temp_file)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="jsonrepair",
        description="Repair invalid JSON documents",
        add_help=False,
    )
    parser.add_argument("input", nargs="?", help="Input file (reads from stdin if omitted)")
    parser.add_argument("-v", "--version", action="store_true", help="Show version")
    parser.add_argument("-h", "--help", action="store_true", help="Show help")
    parser.add_argument("-o", "--output", help="Output file")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the input file")
    parser.add_argument("--buffer", help="Buffer size (e.g. 64K, 1M)", default=None)

    args = parser.parse_args()

    if args.help:
        print(HELP_TEXT)
        return

    if args.version:
        from importlib.metadata import version
        try:
            print(version("jsonrepair"))
        except Exception:
            print("0.1.0")
        return

    buffer_size = None
    if args.buffer:
        try:
            buffer_size = _parse_size(args.buffer)
        except ValueError as e:
            sys.stderr.write(str(e) + "\n")
            sys.exit(1)

    if args.overwrite:
        if not args.input:
            sys.stderr.write("Error: cannot use --overwrite: no input file provided\n")
            sys.exit(1)
        if args.output:
            sys.stderr.write("Error: cannot use --overwrite: there is also an --output provided\n")
            sys.exit(1)
        _process_file_overwrite(args.input, buffer_size or 65536)
        return

    try:
        if args.input:
            with open(args.input, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = sys.stdin.read()

        repaired = jsonrepair(content)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(repaired)
        else:
            sys.stdout.write(repaired)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
