# Human Escalation

Certain change categories always require mandatory human review. The tile must never imply its own review is sufficient for these.

## Mandatory human review triggers

- Architecture shifts (new subsystems, changed boundaries, new dependencies)
- Public API changes (REST routes, GraphQL schema, proto files, exported types)
- Migrations (database schema, data migrations, config migrations)
- Rollout-sensitive changes (feature flags, gradual rollout logic, kill switches)
- Auth, security, secrets, and trust-boundary logic
- Changes with unresolved intent ambiguity (PR description doesn't explain why)
- Multi-subsystem changes where the interaction between subsystems matters
- Concurrency changes (locks, async boundaries, race conditions)

## What escalation means

- The human-review-handoff packet explicitly marks these areas
- The tile does NOT reduce its finding output for escalated areas
- The tile surfaces specific questions the human reviewer should answer
- The tile never implies that its own review is sufficient for these categories
