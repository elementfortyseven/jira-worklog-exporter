# Brief — JWE-7: fine-grained cancellation in worklog pagination

v1.1.0, child of JWE-42. Verified against origin/main @ d1b50a0. One commit, small.
`git fetch origin; git pull origin main` first; ASCII commit, no Co-Authored-By; mirror to
GitLab manually after green GitHub CI.

## Problem

`run_export` (`src/jwe/exporter.py`) checks `cancel_event` only at the top of the issue loop and
once at the very end:

```
for issue in iter_issues(client, jql):
    if cancel_event is not None and cancel_event.is_set():   # per-issue only
        break
    issues_seen += 1
    for worklog in iter_worklogs(client, issue.key, ...):    # <-- no check inside
        ... append_row, count, periodic progress ...
```

So an issue with many worklog pages cannot be cancelled until the whole issue is done. The
docstring even says "stops cleanly between issues". `iter_worklogs` (worklog.py, `startAt`/
`maxResults`) and `iter_issues` (search.py, `nextPageToken`) are pure generators with no cancel hook.

## Approach (exporter-side; keep the API layer pure)

Do NOT thread `cancel_event` into the paginators. They are lazy generators: the next page is only
fetched when the exporter requests the next item. So a check inside the consuming loop already gives
effectively per-page network granularity, without coupling the API layer to cancellation.

Add two checks:

```
for issue in iter_issues(client, jql):
    if cancel_event is not None and cancel_event.is_set():
        break
    issues_seen += 1
    for worklog in iter_worklogs(client, issue.key, ...):
        if cancel_event is not None and cancel_event.is_set():   # (NEW) breaks inner loop
            break
        if writer is not None:
            writer.append_row(issue, worklog)
        worklogs_written += 1
        ...periodic progress yield...
    if cancel_event is not None and cancel_event.is_set():        # (NEW) breaks outer loop too
        break
    ...existing per-issue progress yield...

if cancel_event is not None and cancel_event.is_set():
    yield ExportProgress(...)   # existing final partial yield
    return
yield ExportProgress(...)
```

The second new check avoids requesting one more issue from `iter_issues` (which could trigger a
spurious page fetch) after an inner cancel.

## Semantics decision (locked)

On mid-issue cancel, the worklog rows already streamed for the current issue via `append_row` are
KEPT (no rollback) and `worklogs_written` reflects the partial count. This is consistent with the
existing streaming writer and the "partial result" contract. Do not buffer-per-issue or roll back.

## Docstring

Update the `run_export` docstring: "stops cleanly between issues" -> "stops cleanly between issues
and between worklog pages within an issue (already-written rows for the in-progress issue are kept)".

## Tests (tests/gui/test_export_worker.py and/or the exporter test module)

- Cancel mid-worklog-pagination: mock the client / `iter_worklogs` so one issue yields several
  worklogs; set `cancel_event` after the first worklog; assert the run stops promptly, that
  `worklogs_written` reflects the partial count (not the issue's full total), and that a final
  partial `ExportProgress` is yielded. Reuse the existing W-11 / W-12 cancellation patterns.
- Regression: an uncancelled multi-page export still yields all rows (existing tests should cover
  this; add one if the per-worklog branch isn't otherwise exercised).
- Verify the periodic-progress and final-result counts stay consistent on the cancel path.

## Acceptance

- A cancel during a large single issue's worklog pagination stops within one worklog iteration.
- API paginators unchanged (no `cancel_event` parameter added to `iter_worklogs` / `iter_issues`).
- ruff / mypy / pytest green; ASCII commit; pushed to origin (GitLab mirror is manual, post-CI).
