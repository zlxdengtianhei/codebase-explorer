# Legacy HTTP form (multipart) API

**Capability.** Building, serializing, and freeing curl_httppost multipart form chains via curl_formadd/curl_formget, bridged onto the mime machinery, with disabled-build stubs.

Use curl_formadd to construct a form and curl_formget to serialize it through a callback. Internally a FormInfo chain is parsed, validated, and converted to HttpPost nodes.

**Depends on.**

- [Bufref Utility](r14-bufref-buffers.md) · graph-only · 42 edge(s)

Parent: [Shared infrastructure utilities](r7-shared-infra.md)

## Units (16)

<a id="u-9ad0bce2d42b"></a>
### `Curl_getformdata`

`CURLcode Curl_getformdata(CURL *data, curl_mimepart *finalform, struct curl_httppost …` · [lib/formdata.c:L723-L847][f1]

Converts an HttpPost chain into a mime structure under *finalform.

The destination part is cleaned first; a NULL post yields an empty form. A curl_mime is created and attached as subparts of finalform (CURLE_OUT_OF_MEMORY on failure). Each top-level post with a 'more' chain becomes a nested multipart subpart named by setname; each 'more' element then becomes a part of that sub-multipart, else a part of the top form. Per part: headers are attached (not owned), contenttype set when present, the name set only for single-content parts, then contents are set by flags: FILENAME/READFILE parts read from file, with the legacy "-" pseudo-filename wired to fread on stdin via curl_mime_data_cb (backward compatibility; freopen(stdin) by the caller may misbehave), and READFILE clears the derived filename; BUFFER parts copy bufferlength bytes, or -1 meaning zero-terminated when bufferlength is 0; CALLBACK parts use fread_func with clen, -1 if clen is 0; other parts copy contents with CURL_ZERO_TERMINATED when clen is 0. A contentlen overrides contentslength when CURL_HTTPPOST_LARGE is set. showfilename is applied when set and the part is a file, buffer, callback, or multi-file. Any error cleans the whole finalform again before returning.

calls: [setname](r7-httppost-form.md#u-1bfa505458f1); uses: [grp:mime.h-mime-types-and-state][f2], [set_reader](r6-http-request-build.md#u-67f3be70fb51)

**Uncertainties.**

- fread_func is only used for CALLBACK parts; its effect when NULL is passed depends on curl_mime_data_cb in lib/mime.c.
- The lifetime rules for post->contents/buffer handed to curl_mime_data/curl_mime_filedata are defined in lib/mime.c, not shown here.

<a id="u-0527080bd0b5"></a>
### `curl_formadd`

`CURLFORMcode curl_formadd(struct curl_httppost **httppost, struct curl_httppost **las…` · [lib/formdata.c:L615-L624][f1]

Public API wrapper: captures varargs, runs formadd on them, and returns its CURLFORMcode.

calls: [formadd](r7-httppost-form.md#u-bbc79e2fccd2)

<a id="u-32e0f3a621a8"></a>
### `lib/formdata.c:curl_formadd`

`CURLFORMcode curl_formadd(struct curl_httppost **httppost, struct curl_httppost **las…` · [lib/formdata.c:L850-L856][f1]

Disabled-build stub: ignores arguments and returns CURL_FORMADD_DISABLED.

<a id="u-cd78fdca6932"></a>
### `curl_formfree`

`void curl_formfree(struct curl_httppost *form)` · [lib/formdata.c:L671-L695][f1]

Frees a whole HttpPost chain, recursing into 'more' subchains.

A NULL form returns immediately. Per node: name is freed unless HTTPPOST_PTRNAME; contents unless PTRCONTENTS, BUFFER, or CALLBACK; contenttype and showfilename always; then the node itself.

**Uncertainties.**

- Whether the FREED flags in the name/contents bufrefs should also be released is not evidenced here; only the direct pointer fields are freed.

<a id="u-3cf8b94c316b"></a>
### `lib/formdata.c:curl_formfree`

`void curl_formfree(struct curl_httppost *form)` · [lib/formdata.c:L867-L871][f1]

Disabled-build stub: does nothing.

<a id="u-1f38c0a8d0f5"></a>
### `curl_formget`

`int curl_formget(struct curl_httppost *form, void *arg, curl_formget_callback append)` · [lib/formdata.c:L633-L665][f1]

Serializes an HttpPost form through a user callback using the mime machinery.

A NULL append callback returns CURLE_BAD_FUNCTION_ARGUMENT immediately. An empty top mime part is initialized, filled by Curl_getformdata, headers prepared with strategy MIMESTRATEGY_FORM and content type multipart/form-data; then 8 KiB buffers are read with Curl_mime_read and passed to append until a zero read or error. If append returns fewer bytes than nread, the result is CURLE_READ_ERROR, or CURLE_ABORTED_BY_CALLBACK when nread equals CURL_READFUNC_ABORT. The temp part is cleaned and the CURLcode returned as int.

calls: [Curl_getformdata](r7-httppost-form.md#u-9ad0bce2d42b)

**Uncertainties.**

- Comparing nread (a size_t byte count) against CURL_READFUNC_ABORT is preserved as written; whether it is reachable depends on Curl_mime_read internals not shown.

<a id="u-b4a0f10f1d3e"></a>
### `lib/formdata.c:curl_formget`

`int curl_formget(struct curl_httppost *form, void *arg, curl_formget_callback append)` · [lib/formdata.c:L858-L865][f1]

Disabled-build stub: ignores arguments and returns CURL_FORMADD_DISABLED.

<a id="u-bbc79e2fccd2"></a>
### `formadd`

`static CURLFORMcode formadd(struct curl_httppost **httppost, struct curl_httppost **l…` · [lib/formdata.c:L296-L607][f1]

Parses curl_formadd's vararg (or curl_forms array) options into a temporary FormInfo chain, then validates and converts it.

Arguments come from the forms array when one is active (CURLFORM_ARRAY; nesting an array inside an array yields CURL_FORMADD_ILLEGAL_ARRAY, a NULL array CURL_FORMADD_NULL), otherwise from va_arg. CURLFORM_END terminates. Most options reject duplicates with CURL_FORMADD_OPTION_TWICE and NULL pointers with CURL_FORMADD_NULL; unknown options yield CURL_FORMADD_UNKNOWN_OPTION. CURLFORM_PTRNAME/PTRCONTENTS set the no-copy flags before falling through to the copy variants, which store via Curl_bufref_set without copying. Negative CONTENTSLENGTH/CONTENTLEN gives CURL_FORMADD_INCOMPLETE; CONTENTLEN also sets CURL_HTTPPOST_LARGE. CURLFORM_FILE and CURLFORM_CONTENTTYPE, when a filename part already exists, create a chained subnode via forminfo_new/forminfo_add to support multiple files. CURLFORM_BUFFERPTR and CURLFORM_STREAM set sentinel non-NULL value bufrefs so validation passes. On success formadd_check builds a new HttpPost chain that is linked into *httppost/*last_post; on any error free_formlist releases copied payloads and free_chain discards the new HttpPost chain; FormInfo nodes are always freed.

calls: [formadd_check](r7-httppost-form.md#u-dc8e80807852), [forminfo_new](r7-httppost-form.md#u-37556eca76bd), [forminfo_add](r7-httppost-form.md#u-0758fd766cc5), [free_formlist](r7-httppost-form.md#u-4ae07fca92ff), [free_chain](r7-httppost-form.md#u-d2e36a979b06)

**Uncertainties.**

- Whether the disabled-build stubs and this real definition can coexist is governed by CURL_DISABLE_FORM_API/CURL_DISABLE_HTTP outside this excerpt.

<a id="u-dc8e80807852"></a>
### `formadd_check`

`static CURLFORMcode formadd_check(struct FormInfo *first_form, struct curl_httppost *…` · [lib/formdata.c:L215-L281][f1]

Validates a completed FormInfo chain and converts each node into an HttpPost.

For each node, CURL_FORMADD_INCOMPLETE is returned when: name or value is NULL while no post exists yet; a filename part has nonzero contentslength; HTTPPOST_FILENAME is combined with HTTPPOST_PTRCONTENTS; HTTPPOST_BUFFER is combined with PTRBUFFER without a buffer; or READFILE is combined with PTRCONTENTS. Parts flagged FILENAME or BUFFER without a contenttype get a default: Curl_mime_contenttype of the filename (or showfilename for buffers), falling back to the previous part's type, then FILE_CONTENTTYPE_DEFAULT; allocation failure yields CURL_FORMADD_MEMORY. A name containing an embedded NUL within namelength returns CURL_FORMADD_NULL. Unless HTTPPOST_PTRNAME, the name is copied (forminfo_copyfield); unless the value is one of the no-copy kinds, the value is copied; failures return CURL_FORMADD_MEMORY. Then httppost_add links the node; NULL means CURL_FORMADD_MEMORY. The last seen contenttype is remembered in prevtype. Returns CURL_FORMADD_OK after the whole chain.

calls: [forminfo_copyfield](r7-httppost-form.md#u-d887f5b60438), [httppost_add](r7-httppost-form.md#u-558c8050c7a4)

**Uncertainties.**

- The exact semantics of Curl_mime_contenttype's extension matching live in lib/mime.c and are not shown.

<a id="u-0758fd766cc5"></a>
### `forminfo_add`

`static void forminfo_add(struct FormInfo *form_info, struct FormInfo *parent)` · [lib/formdata.c:L142-L153][f1]

Appends a FormInfo to a parent's 'more' chain: sets HTTPPOST_FILENAME on the new node, splices it after the parent (parent->more becomes the new node, inheriting the old parent->more).

No effect on list heads if parent is NULL.

<a id="u-d887f5b60438"></a>
### `forminfo_copyfield`

`static CURLcode forminfo_copyfield(struct bufref *field, size_t len)` · [lib/formdata.c:L121-L133][f1]

Replaces a field's bufref content with a heap copy of itself.

If the bufref pointer is NULL the field is left unchanged and CURLE_OK returned; a zero length means strlen is used, otherwise len bytes are copied via Curl_bufref_memdup0, whose error is propagated.

uses: [formadd_check](r7-httppost-form.md#u-dc8e80807852)

<a id="u-37556eca76bd"></a>
### `forminfo_new`

`static struct FormInfo *forminfo_new(void)` · [lib/formdata.c:L106-L118][f1]

Allocates a zeroed FormInfo and, on success, initializes its four bufref fields (name, value, contenttype, showfilename).

Returns NULL if allocation fails.

<a id="u-d2e36a979b06"></a>
### `free_chain`

`static void free_chain(struct curl_httppost *c)` · [lib/formdata.c:L285-L294][f1]

Shallowly frees a curl_httppost chain: iterates 'next', recursing into 'more' subchains, freeing each node with curlx_free but not the data the node points to.

<a id="u-4ae07fca92ff"></a>
### `free_formlist`

`static void free_formlist(struct FormInfo *ptr)` · [lib/formdata.c:L155-L163][f1]

Frees the four bufref payloads (name, value, contenttype, showfilename) for every node in a FormInfo 'more' chain, without freeing the node structs themselves.

uses: [formadd](r7-httppost-form.md#u-bbc79e2fccd2)

<a id="u-558c8050c7a4"></a>
### `httppost_add`

`static struct curl_httppost *httppost_add(struct FormInfo *src, struct curl_httppost …` · [lib/formdata.c:L57-L103][f1]

Builds one curl_httppost entry from a FormInfo and links it into a post chain.

If the name bufref is set but namelength is 0, the length is taken from strlen. If bufferlength or namelength exceed LONG_MAX, returns NULL to avoid overflow in the casts. Allocation failure returns NULL. Fields are copied by pointer (name, contents, buffer, contenttype, showfilename, userp, contentheader); flags gain CURL_HTTPPOST_LARGE. With parent_post the new node becomes the parent's 'more' sibling; otherwise it is appended via *last_post/*httppost.

uses: [formadd_check](r7-httppost-form.md#u-dc8e80807852)

**Uncertainties.**

- Whether callers guarantee the name bufref is NUL-terminated when namelength is 0 is not shown here.

<a id="u-1bfa505458f1"></a>
### `setname`

`static CURLcode setname(curl_mimepart *part, const char *name, size_t len)` · [lib/formdata.c:L698-L711][f1]

Sets a mime part's name, handling names that are not NUL-terminated.

If name is NULL or len is 0, curl_mime_name is called directly with the given name. Otherwise the name is duplicated to a NUL-terminated string (CURLE_OUT_OF_MEMORY on failure) before curl_mime_name, and the temporary copy is freed afterwards.

uses: [Curl_getformdata](r7-httppost-form.md#u-9ad0bce2d42b)

**Uncertainties.**

- Behavior of curl_mime_name(part, NULL) is defined in lib/mime.c, not here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/formdata.c
[f2]: ../../../../../../eval/curl-2c04412/lib/mime.h
