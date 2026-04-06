---
name: review-retrospective
description: |
  Evaluates which code review comments (review tiles) actually produced changes after a pull request is merged or closed, by passively collecting outcome data from the GitHub API and git history — zero developer friction. Use when analyzing post-merge pull request outcomes, assessing code review effectiveness, measuring review feedback impact, or answering questions like "how did PR #6 go?", "which review comments were accepted?", or "did any escaped defects appear after this pull request merged?" Produces a structured per-finding outcome record (accepted / rejected / ignored / superseded), merge time delta, escaped defect count, and AI authorship correlation for each PR.
---

# Review Retrospective

Evaluate code review comment (tile) effectiveness by collecting post-review outcomes passively from GitHub and git.

## When to use

- After a reviewed PR has been merged or closed
- When evaluating review tile effectiveness across a corpus of pull requests
- When analyzing code review results or post-merge feedback
- On demand: "how did PR #6 go?", "which review comments were accepted?", "were there any escaped defects?"

## Inputs

- PR number and repository (`owner/repo`)
- Tile finding IDs from the original review

## Data sources (all passive, no developer forms)

### From PR review comments
`gh api repos/{owner}/{repo}/pulls/{pr}/comments`

- Finding marked "resolved" → accepted
- Finding left unresolved at merge → ignored
- Suggested change committed → accepted with exact fix
- Reply disagreeing with finding → rejected (capture reply text for eval)

**Example — fetch and parse resolution status:**
```bash
gh api repos/{owner}/{repo}/pulls/{pr}/comments \
  --jq '[.[] | {id: .id, body: .body, resolved: (.pull_request_review_id != null), author: .user.login}]'
```
Check each comment's thread: if the thread is marked resolved via the GraphQL `isOutdated` or `resolvedAt` fields, disposition = `accepted`; if the PR merged while the thread remained open, disposition = `ignored`.

### From PR timeline
`gh api repos/{owner}/{repo}/issues/{pr}/timeline`

- Time from tile comment to merge → review overhead signal
- Number of review rounds after tile comments → iteration cost
- PR closed without merge → possible tile-induced abandonment (flag for review)

**Example — extract merge timestamp:**
```bash
gh api repos/{owner}/{repo}/issues/{pr}/timeline \
  --jq '[.[] | select(.event == "merged") | {merged_at: .created_at, actor: .actor.login}]'
```

### From post-merge issues
`gh api "search/issues?q=repo:{owner}/{repo}+linked:{pr}"`

- Issues opened referencing the merged PR → candidate escaped defects
- Bug labels on those issues → confirmed escaped defects

**Example — filter for confirmed bugs:**
```bash
gh api "search/issues?q=repo:{owner}/{repo}+linked:{pr}" \
  --jq '[.items[] | select(.labels[].name | test("bug|defect"; "i")) | {number: .number, title: .title, labels: [.labels[].name]}]'
```

### From commit metadata
```bash
git log --format='%(trailers)' origin/main..{merge_sha}
```

- `Co-Authored-By` trailers → AI authorship tagging
- Reviewer mode used → same-model vs challenger correlation with outcomes

## Steps

1. **Collect outcome data.** Query all data sources above using the commands provided. No manual input required. If an API call returns an empty array, record `null` for that signal rather than failing — partial data is valid.

2. **Validate API responses.** Before mapping, confirm:
   - PR comments response contains at least the fields `id`, `body`, `pull_request_review_id`
   - Timeline response contains a `merged` event (if the PR is merged); if absent, mark PR status as `closed_unmerged`
   - If the search API returns a 422 (query too complex), fall back to `gh api repos/{owner}/{repo}/issues --jq 'select(.body | contains("#{pr}"))'`

3. **Map findings to outcomes.** For each tile finding ID, determine disposition:
   - `accepted` — thread resolved or suggested change committed
   - `rejected` — reply explicitly disagreeing captured; record reply text
   - `ignored` — thread open at merge
   - `superseded` — PR changed scope so finding no longer applies

4. **Record structured outcome.** Write one JSON outcome record per PR. Example schema:
   ```json
   {
     "pr": 6,
     "repo": "owner/repo",
     "merged_at": "2024-11-01T14:22:00Z",
     "findings": [
       {
         "finding_id": "tile-42",
         "disposition": "accepted",
         "exact_fix": true,
         "comment_id": 198234567
       },
       {
         "finding_id": "tile-43",
         "disposition": "rejected",
         "rejection_reply": "This pattern is intentional per ADR-12."
       }
     ],
     "merge_time_delta_hours": 3.5,
     "review_rounds": 2,
     "escaped_defects": [
       {"issue": 88, "labels": ["bug"]}
     ],
     "ai_authorship": true
   }
   ```

5. **Verify outcome mapping completeness.** Confirm every finding ID from the original review appears in the `findings` array. Log any finding that could not be matched to a comment as `disposition: "unmatched"` — do not silently drop it.

## Captured outcomes

- Finding accepted / rejected / ignored / superseded / unmatched
- Whether the human fixed the exact issue or an alternative issue
- Merge time delta (hours from first tile comment to merge)
- Escaped defects (from post-merge linked issues with bug labels)
- AI authorship correlation (`Co-Authored-By` trailers)

## Success criteria

- Every tile finding has a recorded disposition
- All data captured passively — zero developer friction
- Escaped defects, if any, are linked back to specific ignored or rejected findings
