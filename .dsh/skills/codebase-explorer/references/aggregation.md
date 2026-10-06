# Aggregation and group import

Read this when claiming or importing a group, or when writing a group body.

The graph (entries, SCCs, shared callees, unknown edges, connected-component hints) is evidence. It is not a grouping decision. Connected components and folders must not be imported as architecture. Canonical graph lists are complete and carry `*_total` fields; a display page must not silently drop the rest of the tree.

Only complete canonical Details are frontier-fresh. Fragment records and historical incomplete canonicals from a split symbol stay out of grouping until the source-0 merge commits.

Astra (existing architecture role) first calls `cbe claim --kind group` with no id file and reads the frontier (paged ids + graph totals, no child bodies). It then writes a JSON string array of fresh, ungrouped Detail ids or groups that already have a body, and claims:

```
python -m cbe claim --run-dir ABS --kind group --input-ids-file ABS.json [--replace-group-id ID]
```

The packet contains: the claim envelope, immediate child full bodies (Detail records or group bodies, never descendant Details), internal edges among the selected leaves, boundary edges with endpoint short cards, and paged graph metadata with totals. It does not dump `existing_groups`. If the selected bodies do not fit the packet window, the command returns `needed_chars` and `limit` and does not open a truncated task.

Review with source uses `delivery=packet_read`: the claim returns a packet **path** and a reserved `call_id`; the reservation settles mechanically when the external reviewer imports with a self-report (`--external`), counting the packed source once.

Import with `cbe import-result` **including the envelope**:

```
{
  "envelope": {"task_id": "...", "generation": 1, "owner": "...", "input_hash": "..."},
  "groups": [
    {
      "group_id": "...",
      "children": ["direct group ids only"],
      "member_ids": ["direct Detail ids only"],
      "question_answered": "...",
      "grouping_reason": "...",
      "entry_routes": ["..."],
      "relations": [],
      "body": "optional; else a group_body task is queued",
      "parent_id": null,
      "partial": false
    }
  ],
  "deferred_ids": ["selected ids not grouped in this slice"]
}
```

Every selected input must appear in exactly one new group or in `deferred_ids`. Mechanical checks run **before** any canonical write: unknown ids, type mix (members vs children), duplicate primary parent, empty group, single-child pass-through, children DAG cycles, stale/unfresh inputs, leftover ids. Failures stay on the task as `needs_repair`; groups are not written and body tasks are not queued. Invalid or partial old groups remain in the ungrouped denominator.

`parent_id` is derived from unique direct membership and must match if supplied. Changing a child invalidates that group's body and actual ancestors and requeues body work even if a body task id already existed. Old envelopes whose `input_hash` no longer matches current child fingerprints are rejected.

A member has one primary parent; cross-function use is a relation, not a second parent. Shared infrastructure is its own group.

Upward greedy: once required **direct** children are fresh, a parent may be produced. An incomplete tree is `partial`. Depth is not fixed. The parent describes combined behavior and links children; it does not concatenate child pages or flatten descendant Details into `member_ids`.

Grok `work` may fill `group_body` tasks after membership is imported. It may not create groups. Group-body prompts receive only direct child documents.

Minimum group-body result: write `{"body":"<combined behavior with supplied child links>"}` as a nonempty string to the unique result file this CLI attempt injects. Do not invent a second destination. Describe duty, combined flow, boundaries, failure paths, and relation evidence; link children instead of concatenating them. Do not change membership, do not introduce source, and do not search the whole repository. If a required child is missing, return that concrete gap.
