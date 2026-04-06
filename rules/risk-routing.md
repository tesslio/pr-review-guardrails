# Risk Routing

The risk lane determines which skills run, how findings are surfaced, and how much time the tile spends.

## Lane routing

- **Green:** lightest viable workflow (evidence + 1 review pass + synthesis)
- **Yellow:** standard workflow (evidence + review + optional challenger + synthesis + handoff)
- **Red:** full workflow with mandatory human review

## Challenger triggering

Use challenger review selectively based on risk lane or reviewer uncertainty. Never skip the evidence-build stage regardless of risk lane.

## Confidence rounding

When the risk classifier's confidence is low, route to the next higher lane. False red is cheap. False green is dangerous.

## Performance budgets

- Green: synchronous, under 2 minutes
- Yellow: synchronous, under 5 minutes
- Red: may run async, under 10 minutes, notifies when ready

If the tile is slower than these budgets, developers will skip it.
