"""Non-executing static pickle audit via pickletools."""

from __future__ import annotations

import io
import pickletools
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


# Modules/callables associated with elevated risk if present as GLOBAL/STACK_GLOBAL.
SUSPICIOUS_MODULE_PREFIXES = (
    "os",
    "subprocess",
    "socket",
    "requests",
    "urllib",
    "http",
    "pathlib",
    "shutil",
    "importlib",
    "ctypes",
    "marshal",
    "code",
    "pty",
    "commands",
    "popen2",
    "multiprocessing",
    "asyncio",
    "tempfile",
)

SUSPICIOUS_CALLABLES = {
    ("builtins", "eval"),
    ("builtins", "exec"),
    ("builtins", "compile"),
    ("builtins", "__import__"),
    ("builtins", "open"),
    ("__builtin__", "eval"),
    ("__builtin__", "exec"),
    ("__builtin__", "compile"),
    ("__builtin__", "__import__"),
    ("os", "system"),
    ("os", "popen"),
    ("os", "execv"),
    ("os", "execve"),
    ("os", "spawn"),
    ("subprocess", "Popen"),
    ("subprocess", "call"),
    ("subprocess", "run"),
    ("subprocess", "check_output"),
}

# Common reconstruction globals that are expected in scientific pickles.
EXPECTED_MODULES = {
    "builtins",
    "__builtin__",
    "collections",
    "copyreg",
    "copy_reg",
    "numpy",
    "numpy.core.multiarray",
    "numpy._core.multiarray",
    "pandas",
    "pandas.core.frame",
    "pandas.core.series",
    "pandas.core.indexes.base",
    "pandas.core.indexes.range",
    "pandas._libs.internals",
    "pandas.core.internals.managers",
    "pandas.core.internals.blocks",
}


@dataclass
class PickleStaticAudit:
    file: str
    size: int
    pickle_protocol: int | None
    opcode_count: int
    opcode_counts: dict[str, int]
    global_refs: list[dict[str, str]]
    modules_referenced: list[str]
    callables_referenced: list[str]
    has_stack_global: bool
    has_reduce: bool
    has_build: bool
    has_newobj: bool
    has_newobj_ex: bool
    has_ext: bool
    has_persid: bool
    suspicious_refs: list[str]
    unclear_refs: list[str]
    static_pickle_risk: str  # PASS / FAIL / REQUIRES_REVIEW
    notes: list[str]


def _iter_opcodes(data: bytes):
    bio = io.BytesIO(data)
    return list(pickletools.genops(bio))


def audit_pickle_bytes(data: bytes, *, file_label: str = "<memory>") -> PickleStaticAudit:
    ops = _iter_opcodes(data)
    opcode_counts: Counter[str] = Counter()
    global_refs: list[dict[str, str]] = []
    modules: set[str] = set()
    callables: set[str] = set()
    protocol: int | None = None
    has_stack_global = False
    has_reduce = False
    has_build = False
    has_newobj = False
    has_newobj_ex = False
    has_ext = False
    has_persid = False

    # Recover STACK_GLOBAL(module, name) by tracking recent string pushes.
    str_stack: list[str] = []

    for opcode, arg, _pos in ops:
        name = opcode.name
        opcode_counts[name] += 1
        if name == "PROTO" and isinstance(arg, int):
            protocol = arg if protocol is None else max(protocol, arg)

        if name in {
            "BINUNICODE",
            "SHORT_BINUNICODE",
            "UNICODE",
            "BINUNICODE8",
            "STRING",
            "BINSTRING",
            "SHORT_BINSTRING",
        }:
            if isinstance(arg, str):
                str_stack.append(arg)
            elif isinstance(arg, bytes):
                try:
                    str_stack.append(arg.decode("utf-8"))
                except UnicodeDecodeError:
                    str_stack.append("")
            # keep stack bounded
            if len(str_stack) > 8:
                str_stack = str_stack[-8:]

        if name == "GLOBAL":
            mod = attr = None
            if isinstance(arg, str):
                if "\n" in arg:
                    mod, attr = arg.split("\n", 1)
                elif " " in arg:
                    mod, attr = arg.split(" ", 1)
            if mod is not None and attr is not None:
                global_refs.append({"module": mod, "name": attr, "opcode": name})
                modules.add(mod)
                callables.add(f"{mod}.{attr}")
        elif name == "STACK_GLOBAL":
            has_stack_global = True
            if len(str_stack) >= 2:
                mod = str_stack[-2]
                attr = str_stack[-1]
                import re as _re

                ident = _re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")
                if ident.match(mod) and ident.match(attr):
                    top = mod.split(".", 1)[0]
                    plausible = (
                        mod in EXPECTED_MODULES
                        or top in {"builtins", "__builtin__", "numpy", "pandas", "collections", "copyreg", "copy_reg"}
                        or any(mod.startswith(p + ".") for p in ("numpy", "pandas", "collections"))
                    )
                    if plausible:
                        global_refs.append({"module": mod, "name": attr, "opcode": name})
                        modules.add(mod)
                        callables.add(f"{mod}.{attr}")
                str_stack = str_stack[:-2]

        if name == "REDUCE":
            has_reduce = True
        if name == "BUILD":
            has_build = True
        if name == "NEWOBJ":
            has_newobj = True
        if name == "NEWOBJ_EX":
            has_newobj_ex = True
        if name.startswith("EXT"):
            has_ext = True
        if name in {"PERSID", "BINPERSID"}:
            has_persid = True

    suspicious: list[str] = []
    unclear: list[str] = []
    for ref in global_refs:
        mod, attr = ref["module"], ref["name"]
        key = (mod, attr)
        top = mod.split(".", 1)[0]
        if key in SUSPICIOUS_CALLABLES or top in {
            "os",
            "subprocess",
            "socket",
            "ctypes",
            "importlib",
            "marshal",
        }:
            suspicious.append(f"{mod}.{attr}")
            continue
        if any(mod == p or mod.startswith(p + ".") for p in SUSPICIOUS_MODULE_PREFIXES):
            if mod.startswith("urllib") or mod.startswith("pathlib") or mod.startswith("shutil"):
                suspicious.append(f"{mod}.{attr}")
                continue
        if mod not in EXPECTED_MODULES and not any(
            mod.startswith(m + ".") for m in ("numpy", "pandas", "collections")
        ):
            unclear.append(f"{mod}.{attr}")

    notes: list[str] = []
    if has_stack_global and not any(r["opcode"] == "STACK_GLOBAL" for r in global_refs):
        notes.append(
            "STACK_GLOBAL present; module/name may be stack-constructed and not fully recovered"
        )
    if has_persid:
        notes.append("PERSID/BINPERSID present — external persistent IDs")
        suspicious.append("PERSID")

    if suspicious:
        risk = "FAIL"
    elif unclear or (
        has_stack_global and not any(r["opcode"] == "STACK_GLOBAL" for r in global_refs)
    ):
        risk = "REQUIRES_REVIEW"
    else:
        risk = "PASS"

    return PickleStaticAudit(
        file=file_label,
        size=len(data),
        pickle_protocol=protocol,
        opcode_count=sum(opcode_counts.values()),
        opcode_counts=dict(sorted(opcode_counts.items())),
        global_refs=global_refs,
        modules_referenced=sorted(modules),
        callables_referenced=sorted(callables),
        has_stack_global=has_stack_global,
        has_reduce=has_reduce,
        has_build=has_build,
        has_newobj=has_newobj,
        has_newobj_ex=has_newobj_ex,
        has_ext=has_ext,
        has_persid=has_persid,
        suspicious_refs=sorted(set(suspicious)),
        unclear_refs=sorted(set(unclear)),
        static_pickle_risk=risk,
        notes=notes,
    )


def audit_pickle_file(path: Path) -> PickleStaticAudit:
    data = path.read_bytes()
    return audit_pickle_bytes(data, file_label=str(path))


def audit_to_dict(audit: PickleStaticAudit) -> dict[str, Any]:
    return asdict(audit)
