from __future__ import annotations

from pathlib import Path


def apply_file(
    source_root: Path,
    relative_path: str,
    replacements: tuple[tuple[int, str, str], ...],
    patch_name: str,
) -> None:
    path = source_root / relative_path
    source = path.read_text(encoding="utf-8")
    original = source
    line_offset = 0

    for index, (anchor_line, before, after) in enumerate(replacements, start=1):
        expected_line = anchor_line + line_offset
        positions = []
        offset = source.find(before)
        while offset != -1:
            positions.append(offset)
            offset = source.find(before, offset + 1)
        matching_lines = [
            position for position in positions
            if source.count("\n", 0, position) + 1 == expected_line
        ]
        if len(matching_lines) == 1:
            position = matching_lines[0]
        else:
            applied_positions = []
            offset = source.find(after)
            while offset != -1:
                applied_positions.append(offset)
                offset = source.find(after, offset + 1)
            applied_lines = [
                position for position in applied_positions
                if source.count("\n", 0, position) + 1 == expected_line
            ]
            if len(applied_lines) == 1:
                position = -1
            elif len(positions) == 1:
                position = positions[0]
            elif not positions and len(applied_positions) == 1:
                position = -1
            else:
                reason = "ambiguous source anchors" if positions else "source anchor not found"
                raise SystemExit(f"{patch_name}: replacement {index} {reason} near line {expected_line} in {path}")

        if position >= 0:
            source = source[:position] + after + source[position + len(before):]
        line_offset += after.count("\n") - before.count("\n")

    if source != original:
        with path.open("w", encoding="utf-8", newline="\n") as output:
            output.write(source)
