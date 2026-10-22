#!/usr/bin/env python3
"""Index static evidence; output is an inventory, never a register replay script."""
from pathlib import Path
import csv
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
BOARD_SECTION = "ESAuDriver_Device_Emdoor_27821A21_RegAdd"


def inf_settings(text: str, section: str) -> dict[str, int]:
    active = False
    result: dict[str, int] = {}
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        if line.startswith("[") and line.endswith("]"):
            active = line[1:-1].casefold() == section.casefold()
        elif active and line.upper().startswith("HKR,"):
            fields = next(csv.reader([line], skipinitialspace=True))
            if len(fields) == 5 and fields[1].casefold() == "esaudsetting":
                try:
                    result[fields[2].strip()] = int(fields[4].strip(), 0)
                except ValueError:
                    pass
    if not result:
        raise ValueError(f"No numeric settings found in {section}")
    return result


def call_arguments(source: str, callee: str):
    """Yield balanced arguments, retaining expressions instead of evaluating C."""
    for match in re.finditer(r"\b" + re.escape(callee) + r"\s*\(", source):
        args: list[str] = []
        start = match.end()
        depth = 1
        quote = ""
        escape = False
        for pos in range(start, len(source)):
            char = source[pos]
            if quote:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == quote:
                    quote = ""
            elif char in "\"'":
                quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    args.append(source[start:pos].strip())
                    yield source.count("\n", 0, match.start()) + 1, args
                    break
            elif char == "," and depth == 1:
                args.append(source[start:pos].strip())
                start = pos + 1
        else:
            raise ValueError(f"Unclosed {callee} call")


def literal(expression: str) -> int | None:
    if re.fullmatch(r"(?:0x[0-9a-fA-F]+|[0-9]+)", expression):
        return int(expression, 0) if expression != "0" else 0
    match = re.fullmatch(r"'\\x([0-9a-fA-F]{2})'", expression)
    if match:
        return int(match[1], 16)
    if expression == r"'\0'":
        return 0
    return None


def main() -> None:
    out = ROOT / "analysis"
    out.mkdir(exist_ok=True)
    settings = inf_settings((ROOT / "inputs/windows/esaudrivertdmmode.inf").read_text(
        encoding="utf-8-sig"), BOARD_SECTION)
    with (ROOT / "inputs/firmware/ES8326-DSM-function-returns.csv").open(
            encoding="utf-8-sig", newline="") as handle:
        dsm = {row["Function"].upper(): row["Return"] for row in csv.DictReader(handle)}
    board = {
        "hardware_id": "ACPI\\VEN_ESSX&DEV_8326&SUBSYS_27821A21",
        "inf_section": BOARD_SECTION,
        "settings": settings,
        "dsm_0x5b": dsm["0X5B"],
        "dsm_0x5b_interpretation": "Speaker GPIO polarity flag, context +0x32b; NOT codec register 0x5b",
        "windows_gpio_mode": "steady" if settings["Platform_SpkGpio_ControlMode"] == 0 else "pulsed",
        "confidence": "static binary/firmware analysis, without live Windows trace",
    }
    (out / "board-config.json").write_text(json.dumps(board, indent=2) + "\n")
    header = (ROOT / "inputs/linux-upstream/es8326.h").read_text()
    registers: dict[int, list[str]] = {}
    for name, value in re.findall(r"^#define\s+(ES8326_\w+)\s+(0x[0-9a-fA-F]+)\s*$", header, re.M):
        registers.setdefault(int(value, 16), []).append(name)
    # Header also contains bit-mask macros. Keep candidate symbols, never pretend
    # a matching numeric value identifies a register uniquely.
    count = constant_count = 0
    with (out / "register-call-inventory.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["function_va", "decompiled_line", "register_expression", "value_expression",
                         "register_literal", "value_literal", "header_numeric_matches", "status"])
        for path in sorted((out / "decompiled/functions").glob("*.c")):
            if path.stem == "14000b26c":
                continue
            for line, args in call_arguments(path.read_text(), "FUN_14000b26c"):
                if len(args) != 3:
                    raise ValueError(f"Unexpected register write arity: {path}:{line}")
                reg, value = literal(args[1]), literal(args[2])
                constant = reg is not None and value is not None
                writer.writerow(["0x" + path.stem, line, args[1], args[2],
                                 "" if reg is None else hex(reg),
                                 "" if value is None else hex(value),
                                 "|".join(registers.get(reg, [])),
                                 "constant callsite; branch applicability unproven" if constant
                                 else "dynamic expression; not evaluated"])
                count += 1
                constant_count += constant
    functions = list(csv.DictReader((out / "decompiled/functions.tsv").open(), delimiter="\t"))
    stats = {"decompiled_functions": len(functions),
             "decompiler_failures": sum(row["decompiled"] != "true" for row in functions),
             "register_write_callsites": count, "constant_register_and_value_callsites": constant_count,
             "warning": "Callsites are not runtime order, board applicability, or a safe initialization sequence."}
    (out / "inventory-summary.json").write_text(json.dumps(stats, indent=2) + "\n")
    hashes = []
    for path in sorted((ROOT / "inputs").rglob("*")):
        if path.is_file():
            hashes.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT)}")
    (out / "input-sha256.txt").write_text("\n".join(hashes) + "\n")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
