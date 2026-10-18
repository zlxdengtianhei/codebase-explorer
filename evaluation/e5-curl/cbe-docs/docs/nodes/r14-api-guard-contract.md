# API Guard Contract

**Capability.** Owns the internal header contract that guards libcurl's api.c entry points.

Readers implementing or auditing the internal API-check mechanism should consult this header. It defines the guard macros shared by api.c callers and nothing else.

Parent: [curl Codebase](r14-curl-codebase.md)

## Units (1)

<a id="u-ac802f8909ea"></a>
### `api-h-api-contract`

`enum` · [lib/api.h:L56-L76][f1]

Header defining the internal API-guard contract shared by api.c callers.

Magic-number macros CURLEASY_MAGIC_NUMBER (0xc0dedbad) and CURLMULTI_MAGIC_NUMBER (0x000bab1e) back GOOD_EASY_HANDLE and GOOD_MULTI_HANDLE, which test a handle's magic field and, in DEBUGBUILD only, additionally DEBUGASSERT on stale non-NULL handles before returning FALSE. Three typedef enums enumerate easy-API ids (Curl_eapi_fn, 0..17), multi-API ids (Curl_mapi_fn), and callback-API ids which start at CURL_CBAPI_FN_START = 128 so they never collide with the other ranges in callstacks. Recursion limits are 7 for easy and 15 for multi callstacks; Curl_eapi_stack/Curl_eapi_guard and Curl_mapi_stack/Curl_mapi_guard carry the callstack arrays and per-call guard state (data/multi kept only when the handle survives the call; depth > 0 only for a successful enter). CURL_EAPI_ENTER/CURL_MAPI_ENTER map a bare function name to its enum value and AND with the handle so analyzers see the NULL check; CURL_CBAPI_START/CURL_CBAPI_MULTI_START wrap Curl_cbapi_enter and the END macros wrap the leaves.

**Uncertainties.**

- Which regions map to which inventory segments cannot be confirmed beyond the declared line ranges; all header content is covered by this group.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/api.h
