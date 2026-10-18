# HTTP Request/Response Objects

**Capability.** Lifecycle of the generic httpreq and http_resp structures, including conversion of an httpreq into HTTP/2 pseudo-headers.

Use for allocation, destruction and H2 representation of request/response objects, separate from wire-protocol logic.

**Depended on by.**

- [Response Parsing and Reaction](r6-http-response-processing.md) · model-inferred · 0 edge(s)

Parent: [HTTP Protocol Engine](r6-http-engine.md)

## Units (3)

<a id="u-4a9c07117d37"></a>
### `http-c-httpreq-lifecycle`

`CURLcode Curl_http_req_make(struct httpreq **preq, const char *method, size_t m_len, …` · [lib/http.c:L4764-L4813][f1]

Allocation and destruction of the generic httpreq structure.

Curl_http_req_make builds a request from raw strings with explicit lengths: the method is stored in a flexible trailing array, scheme/authority/path are strdup-ed length-bounded copies when given, and empty headers and trailers dynhds are initialized; on any failure the partially built request is freed and *preq set NULL. Curl_http_req_make2 derives scheme (falling back to scheme_default when absent), authority (host plus non-default port, omitted when the URL has no host) and path (path plus '?query' when a query exists) from a CURLU handle via the two assign helpers; req_assign_url_authority leaves authority NULL for host-less URLs and uses a dynbuf only when a port is appended, req_assign_url_path takes ownership of the curl_url_get strings when no query exists. Curl_http_req_free releases scheme, authority, path, both header sets and the object itself, tolerating NULL.

**Uncertainties.**

- Ownership: req->path may point either at a dynbuf or at a curl_url_get allocation; both are freed with curlx_free at destroy time, implying compatible allocators.

<a id="u-41eff36c7c9a"></a>
### `http-c-httpresp-lifecycle`

`CURLcode Curl_http_resp_make(struct http_resp **presp, int status, const char *descri…` · [lib/http.c:L5071-L5097][f1]

Allocation and destruction of http_resp objects.

Curl_http_resp_make allocates a zeroed response with the given status, strdup-ed description when supplied, and empty headers and trailers dynhds; on failure the partial object is freed and *presp is NULL. Curl_http_resp_free releases the description, both header sets, and recursively frees the prev chain of responses before freeing the object; NULL is tolerated.

**Uncertainties.**

- Recursive prev-freeing depth is unbounded; deep chains recurse on the C stack.

<a id="u-9fcbd99a87fe"></a>
### `Curl_http_req_to_h2`

`CURLcode Curl_http_req_to_h2(struct dynhds *h2_headers, struct httpreq *req, struct C…` · [lib/http.c:L5002-L5069][f1]

Converts an httpreq into an HTTP/2 pseudo-header set.

The scheme comes from req->scheme, a custom :scheme pseudo header, or the origin scheme (none for CONNECT). The authority comes from req->authority or the Host header. After resetting the target set with lowercase options it adds :method, :scheme, :authority and :path pseudo headers as available, then copies ordinary fields, dropping connection-specific ones (Host, Upgrade, Connection, Keep-Alive, Proxy-Connection, Transfer-Encoding via h2_permissible_field); a TE header survives only when its value contains the 'trailers' token (checked by http_TE_has_token, which also rejects malformed quoted strings) and is then rewritten to exactly 'trailers'. First OOM/add failure aborts and propagates.

calls: [Curl_http_req_to_h2](r6-http-req-resp-objects.md#u-9fcbd99a87fe)

**Uncertainties.**

- HTTP_PSEUDO_* constant values are defined in headers not supplied.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http.c
