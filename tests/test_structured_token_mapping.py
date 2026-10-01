"""Tests for structured render, stable IDs, truncation, RQ1 mask (synthetic)."""

from __future__ import annotations

from src.data.structured_diff import (
    MARKERS,
    FileSpec,
    HunkSpec,
    LineSpec,
    render_structured_commit,
    stable_line_id_v1,
    wrap_chat_plaintext,
)
from src.data.token_line_map import whole_segment_prefix_truncation
from src.data.policy_a_canonical_bridge import RQ1CandidateMask


def test_stable_line_id_includes_ordered_position():
    a = stable_line_id_v1("c" * 40, "A.java", "added", None, 10, 0, 0)
    b = stable_line_id_v1("c" * 40, "A.java", "added", None, 10, 0, 1)
    assert a != b
    assert "|ord0" in a and "|ord1" in b


def test_renderer_grammar_and_spans():
    files = [
        FileSpec(
            canonical_path="p/A.java",
            old_path="p/A.java",
            new_path="p/A.java",
            file_status="modified",
            file_ordinal=0,
            hunks=[
                HunkSpec(
                    hunk_ordinal=0,
                    old_start=1,
                    old_length=1,
                    new_start=1,
                    new_length=1,
                    lines=[
                        LineSpec(
                            change_type="added",
                            raw_text="  int x = 1;",
                            stable_line_id="SID1",
                            old_lineno=None,
                            new_lineno=1,
                            occurrence_index=0,
                            ordered_position=0,
                            rq1_status="RQ1_POSITIVE",
                        )
                    ],
                )
            ],
        )
    ]
    ren = render_structured_commit(
        commit_message="fix bug",
        files=files,
        commit_hash="c" * 40,
    )
    assert MARKERS["MSG"] in ren.text
    assert MARKERS["FILE"] in ren.text
    assert MARKERS["ADD"] in ren.text
    assert "  int x = 1;" in ren.text
    # span registry covers full text
    assert ren.spans[0].char_start == 0
    assert ren.spans[-1].char_end == len(ren.text)
    # payload span exact
    payloads = [s for s in ren.spans if s.stable_line_id == "SID1" and s.payload]
    assert len(payloads) == 1
    s = payloads[0]
    assert ren.text[s.char_start : s.char_end] == "  int x = 1;"


def test_embedded_newline_in_message_preserved_if_present():
    files = [
        FileSpec(
            "A.java",
            None,
            "A.java",
            "added",
            0,
            [
                HunkSpec(
                    0,
                    0,
                    0,
                    1,
                    1,
                    [
                        LineSpec(
                            "added",
                            "x;",
                            "S",
                            None,
                            1,
                            0,
                            0,
                            "NOT_IN_RQ1_UNIVERSE",
                        )
                    ],
                )
            ],
        )
    ]
    ren = render_structured_commit(
        commit_message="line1\nline2", files=files, commit_hash="c" * 40
    )
    assert "line1\nline2" in ren.text


def test_duplicate_lines_different_ord():
    id0 = stable_line_id_v1("c" * 40, "A.java", "added", None, 5, 0, 0)
    id1 = stable_line_id_v1("c" * 40, "A.java", "added", None, 9, 1, 1)
    assert id0 != id1


def test_same_text_different_files():
    a = stable_line_id_v1("c" * 40, "A.java", "added", None, 1, 0, 0)
    b = stable_line_id_v1("c" * 40, "B.java", "added", None, 1, 0, 1)
    assert a != b


def test_rq1_mask_outside_not_negative():
    assert (
        RQ1CandidateMask.classify(in_policy_a=False, label=0.0)
        == RQ1CandidateMask.NOT_IN_RQ1_UNIVERSE
    )


def test_prompt_wrapper_roles():
    msgs = wrap_chat_plaintext("hello")
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert msgs[1]["content"] == "hello"


def test_whole_segment_truncation_drops_full_line():
    """Synthetic offsets: cut inside second payload drops it entirely."""

    class FakeTok:
        def __call__(self, prompt, return_offsets_mapping=True, add_special_tokens=False):
            # prompt = "AAAA" + "BBBB"  (two 4-char payloads at 0-4 and 4-8)
            # tokens of 1 char each
            ids = list(range(8))
            offs = [(i, i + 1) for i in range(8)]
            return {"input_ids": ids, "offset_mapping": offs}

    spans = [
        {
            "char_start": 0,
            "char_end": 4,
            "segment_type": "ADDED_CODE",
            "stable_line_id": "L0",
            "payload": True,
        },
        {
            "char_start": 4,
            "char_end": 8,
            "segment_type": "ADDED_CODE",
            "stable_line_id": "L1",
            "payload": True,
        },
    ]
    # structured at offset 0; max_length small so cut inside L1
    tr = whole_segment_prefix_truncation(
        FakeTok(), "AAAA" + "BBBB", 0, spans, max_length=6, reserve_completion=0
    )
    assert tr["truncated"]
    assert "L1" in tr["dropped_line_ids"]
