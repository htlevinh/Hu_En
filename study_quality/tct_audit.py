#!/usr/bin/env python3
"""TCT lesson coverage validator. Standard library only, offline, no uploads.

This tool checks *structure*, not medical truth. It never validates scientific
claims or substitutes for independent verification of medical content.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ALLOWED_STANCES = {"true", "false", "conditional", "supportive", "non_diagnostic", "required", "optional", "obsolete"}
LEAK_MARKERS = (
    re.compile(r"(?i)\b(?:q(?:uestion)?\s*[-#:]?\s*\d{1,4})\b"),
    re.compile(r"(?i)\b(?:option|choice)\s+[A-H]\b"),
    re.compile(r"(?i)\b(?:correct\s+answer|answer\s+key|the\s+answer)\s*(?:is|:|=)?\s*[A-H](?:\b|\s*,)"),
)


@dataclass(frozen=True)
class Finding:
    code: str
    location: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "location": self.location, "message": self.message}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _items(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def audit(bundle: Any) -> dict[str, Any]:
    """Return a content-minimal quality report, omitting private source text.

    A teaching claim is counted as covered only when it has an explicit verdict,
    a reason, and an anchor appearing in the text taught to the learner. These
    are necessary but not sufficient checks of answer-directed teaching.
    """
    issues: list[Finding] = []

    def flag(code: str, where: str, msg: str) -> None:
        issues.append(Finding(code, where, msg))

    if not isinstance(bundle, dict):
        return {"ok": False, "topic_id": None, "summary": {"questions": 0, "options": 0, "claims": 0, "lesson_blocks": 0, "covered_options": 0}, "findings": [Finding("INVALID_ROOT", "$", "Expected a JSON object.").to_dict()]}
    if bundle.get("schema_version") != 1:
        flag("SCHEMA_VERSION", "schema_version", "Expected schema_version = 1.")

    topic_id = _text(bundle.get("topic_id"))
    if not topic_id:
        flag("TOPIC_ID", "topic_id", "A stable topic identifier is required.")

    lesson = bundle.get("lesson")
    if not isinstance(lesson, dict):
        flag("LESSON_MISSING", "lesson", "Lesson must be an object with blocks and claims.")
        lesson = {}
    blocks = _items(lesson.get("blocks"))
    claims = _items(lesson.get("claims"))
    questions = _items(bundle.get("questions"))
    if not blocks:
        flag("NO_BLOCKS", "lesson.blocks", "Learner-facing teaching blocks are required.")
    if not claims:
        flag("NO_CLAIMS", "lesson.claims", "Explicit taught claims are required.")
    if not questions:
        flag("NO_QUESTIONS", "questions", "At least one original question is required.")

    block_map: dict[str, str] = {}
    for i, item in enumerate(blocks):
        where = f"lesson.blocks[{i}]"
        if not isinstance(item, dict):
            flag("INVALID_BLOCK", where, "Block must be an object.")
            continue
        identifier, body = _text(item.get("id")), _text(item.get("text"))
        if not identifier or identifier in block_map:
            flag("BLOCK_ID", where, "Block id must be present and unique.")
        else:
            block_map[identifier] = body
        if len(body) < 40:
            flag("BLOCK_TOO_SHORT", where, "Teaching block is too short to be useful.")
        if any(pattern.search(body) for pattern in LEAK_MARKERS):
            flag("QUESTION_LEAK", where, "Teaching mentions a question number or option/answer label.")

    claim_map: dict[str, dict[str, Any]] = {}
    for i, item in enumerate(claims):
        where = f"lesson.claims[{i}]"
        if not isinstance(item, dict):
            flag("INVALID_CLAIM", where, "Claim must be an object.")
            continue
        identifier = _text(item.get("id"))
        if not identifier or identifier in claim_map:
            flag("CLAIM_ID", where, "Claim id must be present and unique.")
            continue
        claim_map[identifier] = item
        stance = _text(item.get("stance"))
        if stance not in ALLOWED_STANCES:
            flag("CLAIM_STANCE", where, "Explicit stance must use an allowed verdict type.")
        if len(_text(item.get("decision"))) < 14:
            flag("CLAIM_DECISION", where, "Explicit decision/conclusion is required.")
        if len(_text(item.get("why"))) < 24:
            flag("CLAIM_WHY", where, "Teach why the claim is true, false, or insufficient.")
        block_id = _text(item.get("block_id"))
        if block_id not in block_map:
            flag("CLAIM_BLOCK", where, "Claim must link to a real learner-facing block.")
        anchor = _text(item.get("anchor"))
        if len(anchor) < 18 or anchor.casefold() not in block_map.get(block_id, "").casefold():
            flag("CLAIM_ANCHOR", where, "Anchor must be a meaningful exact excerpt of the teaching text.")

    question_ids: set[str] = set()
    answer_coverage: dict[str, int] = Counter()
    total_options = 0
    covered = 0
    for qi, question in enumerate(questions):
        where = f"questions[{qi}]"
        if not isinstance(question, dict):
            flag("INVALID_QUESTION", where, "Question must be an object.")
            continue
        qid = _text(question.get("id"))
        if not qid or qid in question_ids:
            flag("QUESTION_ID", where, "Original question ID must be present and unique.")
        question_ids.add(qid)
        options = _items(question.get("options"))
        if len(options) < 2:
            flag("QUESTION_OPTIONS", where, "At least two original options are required.")
        labels: set[str] = set()
        for oi, option in enumerate(options):
            total_options += 1
            loc = f"{where}.options[{oi}]"
            if not isinstance(option, dict):
                flag("INVALID_OPTION", loc, "Option must be an object.")
                continue
            label = _text(option.get("label"))
            if not label or label in labels:
                flag("OPTION_LABEL", loc, "Option label must be present and unique within the question.")
            labels.add(label)
            if not _text(option.get("text")):
                flag("OPTION_TEXT", loc, "Preserve the original option text.")
            refs = _items(option.get("taught_by"))
            if not refs or not all(isinstance(x, str) and x.strip() for x in refs):
                flag("UNTaught_OPTION", loc, "Every option needs one or more taught claims.")
            else:
                missing = [ref for ref in refs if ref not in claim_map]
                if missing:
                    flag("UNKNOWN_CLAIM", loc, "Option refers to a nonexistent teaching claim.")
                else:
                    covered += 1
                    for ref in set(refs):
                        answer_coverage[ref] += 1
        answer_labels = _items(question.get("answer_labels"))
        if not answer_labels or not all(isinstance(a, str) and a in labels for a in answer_labels):
            flag("ANSWER_KEY", where, "Preserve a nonempty valid answer key for exam practice.")

    for ci, claim in claim_map.items():
        if not answer_coverage[ci]:
            flag("ORPHAN_CLAIM", f"lesson.claims.{ci}", "Claim is not mapped to any question option.")

    phases = bundle.get("phases", {})
    if not isinstance(phases, dict):
        phases = {}
        flag("PHASES", "phases", "Phases must be an object.")
    pretest = _items(phases.get("pretest_question_ids"))
    exam = _items(phases.get("exam_question_ids"))
    if not 1 <= len(pretest) <= 3 or any(q not in question_ids for q in pretest) or len(pretest) != len(set(pretest)):
        flag("PRETEST_SELECTION", "phases.pretest_question_ids", "Pre-test needs 1-3 unique original question IDs.")
    if len(exam) != len(set(exam)) or set(exam) != question_ids:
        flag("EXAM_INCOMPLETE", "phases.exam_question_ids", "Exam phase must include each original question exactly once.")
    if any(_text(phases.get(key)) for key in ("pretest_answer_text", "pretest_explanations")):
        flag("PRETEST_ANSWER_LEAK", "phases", "Do not reveal answers or explanations in pre-test content.")

    return {
        "ok": not issues,
        "topic_id": topic_id or None,
        "summary": {"questions": len(questions), "options": total_options, "claims": len(claims), "lesson_blocks": len(blocks), "covered_options": covered},
        "findings": [finding.to_dict() for finding in issues],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Teach-Cluster-Test answer-enabling lesson coverage (structure only).")
    parser.add_argument("path", type=Path, help="Local TCT JSON bundle; never uploaded by this tool")
    parser.add_argument("--report", type=Path, help="Optional report path; contains finding codes, no question or lesson text")
    args = parser.parse_args(argv)
    try:
        bundle = json.loads(args.path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": f"Unable to load JSON: {type(exc).__name__}"}), file=sys.stderr)
        return 2
    result = audit(bundle)
    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.report:
        try:
            args.report.write_text(output + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"Report not written: {type(exc).__name__}", file=sys.stderr)
            return 2
    print(output)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())