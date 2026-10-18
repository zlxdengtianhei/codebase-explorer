# curl Command-Line Tool

**Capability.** Owns the tool-side application layer: per-operation option state, --libcurl code generation, Windows/DOS-specific support, stdin read callbacks, and shared small utilities (slist_wc, directory-hierarchy declaration, compile-time warning helpers).

Enter here for tool behavior rather than library internals. The children cover configuration state, code generation, Windows support and upload read callbacks; the node itself holds shared utilities.

**Children.**

- [Tool Operation Configuration](r1-tool-operation-config.md) `r1-tool-operation-config` · 3 unit(s)
- [--libcurl Code Generation](r1-libcurl-codegen.md) `r1-libcurl-codegen` · 15 unit(s)
- [Windows/DOS Tool Support](r1-windows-tool-support.md) `r1-windows-tool-support` · 17 unit(s)
- [Upload Read Callbacks](r1-stdin-read-callbacks.md) `r1-stdin-read-callbacks` · 4 unit(s)

**Depends on.**

- [Platform and Auth Utilities](r1-platform-utilities.md) · model-inferred · 0 edge(s)

Parent: [curl Codebase](r1-curl-codebase.md)

## Units (4)

<a id="u-a9378c7134a8"></a>
### `typecheck-gcc-h-warning-functions`

`group`

Declares all compile-time warning functions via CURLWARNING(id, message), which expands to a static, unused, noinline void function whose body is empty inline assembly and which carries __attribute__((__warning__(message))).

GCC emits the message as a warning when it can prove at compile time that a call to the function is reachable - which happens only through the type-check cascades in the wrapper macros when an argument type mismatches. Each Wcurl_easy_setopt_err*, Wcurl_multi_setopt_err*, and Wcurl_easy_getinfo_err* function carries one message naming the expected argument type (long, curl_off_t, string, specific callback types, pointer types, etc.). They are never meant to run.

uses: [typecheck-gcc-h-wrapper-macros](r8-portable-headers.md#u-35b66e97c11a)

<a id="u-afa002f0f87c"></a>
### `slist_wc_append`

`struct slist_wc *slist_wc_append(struct slist_wc *list, const char *data)` · [src/slist_wc.c:L34-L57][f1]

Appends a string to a doubly-referenced linked list, creating the wrapper when absent.

It builds a curl_slist node via curl_slist_append(NULL, data); if node allocation fails it returns NULL. When the wrapper is NULL, it allocates a struct slist_wc and on wrapper-allocation failure frees the new node and returns NULL; otherwise first and last both point at the new node. When the wrapper exists, the node is linked after list->last and last is advanced, leaving the original wrapper pointer valid.

**Notes.**

- side_effect: Mutates list->last->next and list->last of the caller's list when it is non-NULL.
- failure: Returns NULL on either node or wrapper allocation failure; the existing list is left untouched in the node-failure case.

uses: [slist_wc](r14-tool-data-helpers.md#u-df19e626b32e); calls: [curl_slist_append](r8-container-types.md#u-851bb574d7cd)

<a id="u-85a2af6b99ef"></a>
### `slist_wc_free_all`

`void slist_wc_free_all(struct slist_wc *list)` · [src/slist_wc.c:L60-L67][f1]

Frees a slist_wc wrapper: a NULL argument returns immediately; otherwise it frees the whole curl_slist chain starting at list->first and then the wrapper itself.

calls: [curl_slist_free_all](r8-container-types.md#u-098fac37e5cb)

<a id="u-42aaa34227d6"></a>
### `tool_dirhie.h module code (L1–L34)`

`module_region` · [src/tool_dirhie.h:L1-L34][f2]

Header declaring create_dir_hierarchy and, under UNITTESTS, the trace dynbuf accessor.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/slist_wc.c
[f2]: ../../../../../../eval/curl-2c04412/src/tool_dirhie.h
