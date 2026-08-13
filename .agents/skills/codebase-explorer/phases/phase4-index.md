# Phase 4: Independent Review and Revision

## Create and Consume a Blind Review Batch

```text
review = get_semantic_review_batch(output_dir=output_dir)
verdict = submit_semantic_review(
  review_batch_id=review["review_batch_id"],
  output_dir=output_dir
)
```

The review batch hides producer metadata and symbol IDs. The submit tool owns
dispatch to an isolated Codex reviewer and binds the returned verdict to the
current ledger fingerprint. Producers must not fabricate a review result.

## Outcomes

- `accepted`: query progress and require
  `review_verdict_present: true`.
- `revision_required`: the listed symbol explanations have been invalidated.
  Return to Phase 2, rebuild them from a fresh claim, render again, and request a
  new review batch.

A review batch is single-use and revision changes the ledger fingerprint. Never
reuse an old `review_batch_id`.
