"""Structured CHANGED_ONLY / CTX renderer with exact character-span registry.

STRUCTURED_FORMAT_VERSION = 1
No tokenization here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

STRUCTURED_FORMAT_VERSION = 1

MARKERS = {
    "MSG": "[MSG]",
    "FILE": "[FILE]",
    "HUNK": "[HUNK]",
    "ADD": "[ADD]",
    "DEL": "[DEL]",
    "CTX": "[CTX]",
}

SegmentType = Literal[
    "PROMPT_INSTRUCTION",
    "STRUCTURAL_MARKUP",
    "COMMIT_MESSAGE",
    "FILE_PATH",
    "HUNK_HEADER",
    "ADDED_CODE",
    "DELETED_CODE",
    "CONTEXT_CODE",
    "SPECIAL_TOKEN",
]


@dataclass(frozen=True)
class SpanRecord:
    char_start: int
    char_end: int
    segment_type: str
    stable_line_id: str | None = None
    file_id: str | None = None
    hunk_id: str | None = None
    change_type: str | None = None
    rq1_status: str | None = None
    payload: bool = False  # True for code/message payload (not markup)


@dataclass
class RenderedCommit:
    text: str
    spans: list[SpanRecord]
    format_version: int = STRUCTURED_FORMAT_VERSION
    context_lines: int = 0


def stable_line_id_v1(
    commit_hash: str,
    file_path: str,
    change_type: str,
    old_lineno: int | None,
    new_lineno: int | None,
    occurrence_index: int,
    ordered_position: int,
) -> str:
    """Context-invariant line ID (U0 ordered_position disambiguates rare lineno collisions)."""
    ol = "NA" if old_lineno is None else str(old_lineno)
    nl = "NA" if new_lineno is None else str(new_lineno)
    return (
        f"{commit_hash}|{file_path}|{change_type}|old{ol}|new{nl}"
        f"|occ{occurrence_index}|ord{ordered_position}"
    )


def hunk_id_v1(
    commit_hash: str,
    file_path: str,
    representation_variant: str,
    hunk_ordinal: int,
) -> str:
    return f"{commit_hash}|{file_path}|{representation_variant}|h{hunk_ordinal}"


def _append(
    buf: list[str],
    spans: list[SpanRecord],
    text: str,
    segment_type: str,
    *,
    stable_line_id: str | None = None,
    file_id: str | None = None,
    hunk_id: str | None = None,
    change_type: str | None = None,
    rq1_status: str | None = None,
    payload: bool = False,
) -> None:
    start = sum(len(x) for x in buf)
    buf.append(text)
    end = start + len(text)
    spans.append(
        SpanRecord(
            char_start=start,
            char_end=end,
            segment_type=segment_type,
            stable_line_id=stable_line_id,
            file_id=file_id,
            hunk_id=hunk_id,
            change_type=change_type,
            rq1_status=rq1_status,
            payload=payload,
        )
    )


@dataclass
class LineSpec:
    change_type: str  # added|deleted|context
    raw_text: str  # no trailing newline
    stable_line_id: str | None
    old_lineno: int | None
    new_lineno: int | None
    occurrence_index: int
    ordered_position: int | None
    rq1_status: str


@dataclass
class HunkSpec:
    hunk_ordinal: int
    old_start: int
    old_length: int
    new_start: int
    new_length: int
    lines: list[LineSpec]


@dataclass
class FileSpec:
    canonical_path: str
    old_path: str | None
    new_path: str | None
    file_status: str
    file_ordinal: int
    hunks: list[HunkSpec]


def render_structured_commit(
    *,
    commit_message: str,
    files: list[FileSpec],
    commit_hash: str,
    context_lines: int = 0,
    representation_variant: str = "CHANGED_ONLY",
) -> RenderedCommit:
    """Render structured text + span registry. Newlines only as explicit separators."""
    buf: list[str] = []
    spans: list[SpanRecord] = []

    # [MSG] marker + payload
    _append(buf, spans, MARKERS["MSG"], "STRUCTURAL_MARKUP")
    _append(buf, spans, " ", "STRUCTURAL_MARKUP")
    # Preserve message text exactly (may contain spaces); strip only a single
    # trailing newline if present from serialization — messages audited as no \n.
    msg = commit_message
    if msg.endswith("\n"):
        msg = msg[:-1]
    _append(buf, spans, msg, "COMMIT_MESSAGE", payload=True)
    _append(buf, spans, "\n", "STRUCTURAL_MARKUP")

    for fspec in files:
        _append(buf, spans, MARKERS["FILE"], "STRUCTURAL_MARKUP")
        _append(buf, spans, " ", "STRUCTURAL_MARKUP")
        _append(
            buf,
            spans,
            fspec.canonical_path,
            "FILE_PATH",
            file_id=fspec.canonical_path,
            payload=True,
        )
        _append(buf, spans, "\n", "STRUCTURAL_MARKUP")

        for hspec in fspec.hunks:
            hid = hunk_id_v1(
                commit_hash,
                fspec.canonical_path,
                representation_variant,
                hspec.hunk_ordinal,
            )
            _append(buf, spans, MARKERS["HUNK"], "STRUCTURAL_MARKUP")
            _append(buf, spans, " ", "STRUCTURAL_MARKUP")
            header = (
                f"{hspec.hunk_ordinal} -{hspec.old_start},{hspec.old_length} "
                f"+{hspec.new_start},{hspec.new_length}"
            )
            _append(
                buf,
                spans,
                header,
                "HUNK_HEADER",
                file_id=fspec.canonical_path,
                hunk_id=hid,
                payload=True,
            )
            _append(buf, spans, "\n", "STRUCTURAL_MARKUP")

            for line in hspec.lines:
                if line.change_type == "added":
                    marker = MARKERS["ADD"]
                    seg = "ADDED_CODE"
                elif line.change_type == "deleted":
                    marker = MARKERS["DEL"]
                    seg = "DELETED_CODE"
                else:
                    marker = MARKERS["CTX"]
                    seg = "CONTEXT_CODE"
                _append(buf, spans, marker, "STRUCTURAL_MARKUP")
                _append(buf, spans, " ", "STRUCTURAL_MARKUP")
                _append(
                    buf,
                    spans,
                    line.raw_text,
                    seg,
                    stable_line_id=line.stable_line_id,
                    file_id=fspec.canonical_path,
                    hunk_id=hid,
                    change_type=line.change_type,
                    rq1_status=line.rq1_status,
                    payload=True,
                )
                _append(buf, spans, "\n", "STRUCTURAL_MARKUP")

    text = "".join(buf)
    return RenderedCommit(
        text=text, spans=spans, format_version=STRUCTURED_FORMAT_VERSION, context_lines=context_lines
    )


# Chat / classification prompt
PROMPT_TEMPLATE_VERSION = 1

SYSTEM_INSTRUCTION = (
    "You are a classifier for just-in-time defect prediction. "
    "Given a structured commit diff, reply with a single character: "
    "1 if the commit is defect-inducing, or 0 otherwise. "
    "Do not explain."
)


def wrap_chat_plaintext(structured_user_content: str) -> list[dict[str, str]]:
    """Messages for tokenizer.apply_chat_template."""
    return [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": structured_user_content},
    ]
