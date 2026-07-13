#!/usr/bin/env python3
"""Resequence s/d/o list IDs in plain text or JavaScript list files."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path


PREFIXES = ("s", "d", "o")
ID_PATTERN = re.compile(
    r"(?P<bracket>\[(?P<bracket_prefix>[sdoSDO])(?P<bracket_body>\d[0-9A-Za-z]*)\])"
    r"|(?P<id_head>\bid\s*:\s*(?P<id_quote>[\"']))"
    r"(?P<id_prefix>[sdoSDO])(?P<id_body>\d[0-9A-Za-z]*)(?P=id_quote)"
)


@dataclass
class ResequenceResult:
    text: str
    processed: dict[str, int] = field(default_factory=lambda: dict.fromkeys(PREFIXES, 0))
    changed: dict[str, int] = field(default_factory=lambda: dict.fromkeys(PREFIXES, 0))


@dataclass
class VerificationIssue:
    line_number: int
    expected: str
    found: str


def make_id(prefix: str, number: int) -> str:
    return f"{prefix}{number:04d}"


def read_text(path: Path, encoding: str | None) -> tuple[str, str]:
    data = path.read_bytes()
    if encoding:
        return data.decode(encoding), encoding

    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"

    return data.decode("utf-8"), "utf-8"


def write_text(path: Path, text: str, encoding: str) -> None:
    path.write_bytes(text.encode(encoding))


def output_path_for(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}.resequenced{input_path.suffix or '.txt'}")


def line_number_at(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def matched_id(match: re.Match[str]) -> tuple[str, str]:
    if match.group("bracket") is not None:
        prefix = match.group("bracket_prefix").lower()
        return prefix, prefix + match.group("bracket_body")

    prefix = match.group("id_prefix").lower()
    return prefix, prefix + match.group("id_body")


def resequence(text: str) -> ResequenceResult:
    counters = dict.fromkeys(PREFIXES, 0)
    result = ResequenceResult(text="")

    def replace(match: re.Match[str]) -> str:
        prefix, old_id = matched_id(match)
        counters[prefix] += 1
        new_id = make_id(prefix, counters[prefix])
        result.processed[prefix] += 1

        if old_id != new_id:
            result.changed[prefix] += 1

        if match.group("bracket") is not None:
            return f"[{new_id}]"

        return f"{match.group('id_head')}{new_id}{match.group('id_quote')}"

    result.text = ID_PATTERN.sub(replace, text)
    return result


def verify(text: str) -> VerificationIssue | None:
    counters = dict.fromkeys(PREFIXES, 0)

    for match in ID_PATTERN.finditer(text):
        prefix, found = matched_id(match)
        counters[prefix] += 1
        expected = make_id(prefix, counters[prefix])
        if found != expected:
            return VerificationIssue(
                line_number=line_number_at(text, match.start()),
                expected=expected,
                found=found,
            )

    return None


def print_counts(title: str, counts: dict[str, int]) -> None:
    print(f"{title}:")
    for prefix in PREFIXES:
        print(f"  {prefix}: {counts[prefix]}")


def print_summary(result: ResequenceResult, output_path: Path | None, dry_run: bool) -> None:
    print_counts("IDs processed", result.processed)
    print()
    print_counts("IDs changed", result.changed)
    print()
    print("Verification:")
    print("  passed")
    print()
    print("Output:")
    if dry_run:
        print("  not written (--dry-run)")
    else:
        print(f"  {output_path}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resequence s/d/o IDs like [s0001] and id: \"s0001\"."
    )
    parser.add_argument("file", nargs="?", help="Input .txt/.js file to resequence.")
    parser.add_argument(
        "-o",
        "--output",
        help="Output file. Defaults to <input>.resequenced.txt unless --in-place is used.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the input file after verification passes.",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create <input>.bak before overwriting. Only valid with --in-place.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resequence and verify in memory, but do not write a file.",
    )
    parser.add_argument(
        "--encoding",
        help="Text encoding to use. Defaults to UTF-8, preserving a UTF-8 BOM if present.",
    )

    args = parser.parse_args(argv)

    if args.output and args.in_place:
        parser.error("--output cannot be used with --in-place")
    if args.backup and not args.in_place:
        parser.error("--backup can only be used with --in-place")

    return args


def prompt_for_file() -> str:
    raw = input("File to resequence: ").strip()
    return raw.strip('"')


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    file_arg = args.file or prompt_for_file()
    input_path = Path(file_arg).expanduser().resolve()

    if not input_path.is_file():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        original_text, encoding = read_text(input_path, args.encoding)
    except UnicodeDecodeError as error:
        print(f"Error: could not decode file as {args.encoding or 'utf-8'}: {error}", file=sys.stderr)
        print("Try again with --encoding, for example: --encoding cp1252", file=sys.stderr)
        return 1

    result = resequence(original_text)
    issue = verify(result.text)
    if issue:
        print("Verification:")
        print("  failed")
        print()
        print(f"Expected {issue.expected} but found {issue.found} on line {issue.line_number}")
        print("No file was written.")
        return 1

    output_path: Path | None = None
    if not args.dry_run:
        output_path = input_path if args.in_place else Path(args.output).resolve() if args.output else output_path_for(input_path)

        if args.in_place and args.backup:
            shutil.copy2(input_path, input_path.with_name(f"{input_path.name}.bak"))

        write_text(output_path, result.text, encoding)

    print_summary(result, output_path, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
