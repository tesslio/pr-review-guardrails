# Reviewer Independence

Independent review is more valuable than same-context self-review. The tile must enforce separation between authoring and reviewing.

## Requirements

- Prefer independent reviewer contexts over same-context self-review
- Mark whether review was same-model or challenger-mode
- Avoid reading the authoring chain
- Report context isolation status honestly in provenance metadata

## Preferred implementation: structural isolation

Run reviewer skills in a separate agent session that receives only the evidence pack and raw diff. The reviewing agent does not receive the authoring prompt, the authoring agent's reasoning, or the authoring session's tool call history. Report `context_isolation: true`.

## Fallback implementation: soft isolation

Because Tessl skills within a tile share the same context window, structural isolation requires a separate agent session. If a separate session is not available or not supported by the runtime, fall back to soft isolation:

- The reviewer skill's instructions scope it to the evidence pack only
- The reviewer is instructed to base findings solely on the pack and raw diff
- Provenance reports `context_isolation: false`
- The reviewer packet includes a note that isolation was instructional, not structural

The tile should attempt structural isolation first and degrade to soft isolation automatically.

## Provenance metadata on every review output

- `reviewer_mode: fresh_eyes | challenger`
- `reviewer_model_family: string`
- `context_isolation: true | false`
- `authoring_model_family: string | unknown`
