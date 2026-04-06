# Comment Quality

Comments must be worth the cognitive effort to read. Every finding competes for a human reviewer's limited attention.

## Requirements

- Prefer hunk-level comments tied to specific lines
- Suppress generic style advice (especially if a linter already covers it)
- Avoid repetitive phrasing across findings — each finding gets its own language
- Explain impact, not just code difference ("this can cause X" not "this was changed from Y to Z")
- Never generate comments that require the reviewer to read more than the finding itself to understand the issue

## Anti-patterns to actively suppress

- "Consider using..." without explaining what breaks if you don't
- "This could be improved by..." without a concrete defect or risk
- "Nitpick:" anything — if it's not worth fixing, it's not worth saying
- Restating the diff in English ("this function was renamed from X to Y")
- Boilerplate praise ("good use of...", "nice refactoring...")

## Volume control

All findings that clear the evidence threshold are surfaced. There is no arbitrary cap. The evidence threshold IS the volume control.
