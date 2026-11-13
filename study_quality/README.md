# TCT lesson coverage gate (experimental)

A deterministic **Teach-Cluster-Test** lesson-quality gate, designed to be run
locally against a topic bundle before the exam-practice phase. This is a
**standalone pilot**, not an installed component of LifeSystem.

## Why

The failure mode is a lesson that mentions topics without teaching the
conclusions needed to resolve *every* question option. A good lesson must be
answer-enabling without saying which option will be correct in an upcoming
question. The gate checks the **structure** of that contract.

## What is checked

- Each original question has its options and answer labels preserved.
- Every option references one or more *taught claims*.
- Every taught claim has an explicit stance, decision, explanation, and an
  exact anchor in learner-facing lesson text.
- Pre-test selects 1-3 original questions, with no advance answer key.
- Exam phase contains **all** original questions, once each.
- Lesson text does not name question numbers, option letters, or answer keys.
- Report includes only finding codes and record positions, not original
  question stems or teaching text.

**Limits:** This tool cannot determine whether medical claims, answer keys,
source citations, or mechanisms are scientifically correct. It cannot detect
all forms of implicit answer leakage. A clinician/verified source and an
independent review are still required. A passing report means the structural
contract passes, not that the medical lesson is safe or correct.

## Run locally

```bash
python3 study_quality/tct_audit.py study_quality/examples/fictional_weather.json
python3 -m unittest discover -s study_quality/tests -v
```

Exit codes: `0` = pass, `1` = structural quality findings, `2` = input/output error.
Use `--report /private/path/report.json` for a compact report. The tool does not
make network requests and does not upload files.

## Integration target for Tannen

1. Keep the real MCQ banks, lesson drafts and learner history **only on Tannen**.
2. A local, read-only adapter produces one topic-specific JSON bundle, with
   original question IDs and claim anchors. Do not commit this bundle to GitHub.
3. The local workflow invokes `tct_audit.py`. On red findings, return only the
   finding codes to the author, then rebuild the lesson. On green, proceed to
   independent factual verification and the existing study/exam practice flow.
4. Optionally record counts and hashes in the LifeSystem ledger, with source
   refs local to Tannen. Do not store patient data or medical-study materials
   in public CI runs.
5. GitHub Actions runs **synthetic tests only** on every PR. Its job is to
   ensure changes to the validator do not weaken previously checked rules.

No migrations, daemon, cron, server access, or LifeSystem authority changes are
part of this pilot.

## Synthetic fixture

`examples/fictional_weather.json` tests a weather-instrument MCQ. This is
intentionally not a medical exam, and it contains no personal records.