# Public Suffix List Access

**Capability.** Owns acquiring, refreshing under share locks, and releasing the PSL context, with conditional no-op substitutes when built without libpsl.

Use this child to see how the PSL cache is kept current for a transfer and how the build degrades without libpsl.

Parent: [HTTP Domain Policy Caches](r10-url-policy.md)

## Units (4)

<a id="u-e72d21696864"></a>
### `Curl_psl_destroy`

`void Curl_psl_destroy(struct PslCache *pslcache)` · [lib/psl.c:L36-L44][f1]

Releases a PSL cache's context: if pslcache->psl is set, it frees the context with psl_free only when the dynamic flag says it was loaded via psl_latest, then clears the pointer and the dynamic flag.

A built-in (non-dynamic) context is not freed.

**Uncertainties.**

- Whether psl_free is safe on contexts obtained from psl_builtin is guarded by the dynamic flag; semantics of libpsl are external.

<a id="u-632512dd6943"></a>
### `Curl_psl_release`

`void Curl_psl_release(struct Curl_easy *easy)` · [lib/psl.c:L99-L102][f1]

Releases the shared PSL share lock taken by a successful Curl_psl_use call.

<a id="u-16e2f6d9be05"></a>
### `Curl_psl_use`

`const psl_ctx_t *Curl_psl_use(struct Curl_easy *easy)` · [lib/psl.c:L46-L97][f1]

Acquires the PSL context for a transfer under the share lock, refreshing the cache when stale.

Returns NULL immediately if the transfer has no PSL cache. It takes the shared PSL lock, and if no context is loaded or expires <= now, it releases the shared lock (so other threads are not deadlocked), takes the exclusive lock, and rechecks. While holding the exclusive lock it refreshes the now timestamp, and if the cache is still missing or expired it calls psl_latest; if that yields nothing and the current context is not dynamic it falls back to psl_builtin. On any successful context it destroys the old one via Curl_psl_destroy, stores the new context, its dynamic flag, and an expiry of now+PSL_TTL clamped to TIME_T_MAX. It then releases the exclusive lock and re-acquires the shared lock. Finally it returns the cached context, unlocking the share if no context exists so the caller never needs to release in the NULL case.

calls: [Curl_psl_destroy](r10-psl-cache.md#u-e72d21696864), [Curl_pgrs_now](r9-progress-timing-and-policy.md#u-5b4855900d77)

**Uncertainties.**

- psl_latest, psl_builtin, psl_free semantics and PSL_TTL value are external to this file.
- The inner 'if(pslcache->expires <= now_sec)' refresh of now_sec appears redundant without visible concurrency detail; its precise necessity is uncertain.

<a id="u-7cf5acb34e6a"></a>
### `psl.h module code (L1–L33)`

`struct PslCache` · [lib/psl.h:L34-L38][f2]

Conditional PSL support header: it declares the PSL cache struct and accessor prototypes when built with libpsl, otherwise defines no-op macro substitutes for each accessor.

With USE_LIBPSL defined, PSL_TTL is set to 72 hours as the cache lifetime, <libpsl.h> is included, and callers get the real declarations of Curl_psl_use, Curl_psl_release, and Curl_psl_destroy. Without it, each macro expands to nothing usable as a pointer or statement, so call sites compile without any Public Suffix List functionality; the header guard HEADER_PSL_H prevents double inclusion.

group: [psl.h module code (L1–L33)](r10-psl-cache.md#u-7cf5acb34e6a)

**Uncertainties.**

- The semantics of the no-op macro expansion of Curl_psl_use(easy) to NULL at call sites depend on how callers parenthesize and use it; those call sites are not in this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/psl.c
[f2]: ../../../../../../eval/curl-2c04412/lib/psl.h
