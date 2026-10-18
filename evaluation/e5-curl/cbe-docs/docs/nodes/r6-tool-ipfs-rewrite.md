# IPFS URL Rewriting

**Capability.** Rewrites ipfs:// and ipns:// URLs into HTTP(S) gateway URLs using a configurable gateway string.

Use to see how IPFS transfers are redirected to gateways. ipfs_url_rewrite drives the CURLU handle API and serializes the result; ipfs_gateway resolves the gateway setting.

**Depends on.**

- [CURLU Handle Management and Setters](r6-url-handle-api.md) · graph-confirmed · 8 edge(s)

Parent: [Command-Line Tool Support](r6-tool-side.md)

## Units (2)

<a id="u-1576b15ada23"></a>
### `ipfs_url_rewrite`

`CURLcode ipfs_url_rewrite(CURLU *uh, const char *protocol, char **url, struct Operati…` · [src/tool_ipfs.c:L103-L244][f1]

Rewrites an ipfs:// or ipns:// URL in a CURLU handle into an HTTP(S) gateway URL, updating *url with the serialized result.

It clones the input URL into a gatewayurl CURLU and takes the CID percent-encoded from the input host part. Gateway selection: config->ipfs_gateway is parsed with CURLU_GUESS_SCHEME and duplicated; if it fails to parse the function fails with CURLE_BAD_FUNCTION_ARGUMENT. Without the option, ipfs_gateway() is used; failure yields CURLE_FILE_COULDNT_READ_FILE and an unparseable detected gateway yields CURLE_URL_MALFORMAT. A gateway carrying a query part is rejected as CURLE_URL_MALFORMAT. Host, scheme, port (with default port) are read URL-decoded from the gateway and written into the input URL URL-encoded. The input path is read without decoding so percent-encoded bytes — including %2f — never become separators or dot-segments, preventing '..' from escaping the /<protocol>/<cid> namespace on the later reparse. A path of exactly '/' is cleared; the new path is '<gwpath>[/]protocol/cid<inputpath>' via curl_maprintf, set on the handle, *url is freed and replaced by the URLDECODE-encoded serialization strdup'd so curlx_free can later release it. The cleanup label frees all curl_url_get-allocated strings and the gatewayurl, then helpf()s a message matching the failure code: malformed target URL, automatic gateway detection failed, or malformed --ipfs-gateway. Any curl_url_set/get failure along the way leaves the initial CURLE_URL_MALFORMAT in place unless changed above; success returns CURLE_OK.

**Notes.**

- failure: *url is freed before the final serialization, so on failure after that point *url is left NULL/dangling-free rather than holding the original URL.
- contract: The CID is deliberately kept percent-encoded because it is placed in the URL path.

calls: [ipfs_gateway](r6-tool-ipfs-rewrite.md#u-a4cf41f5106b), [curl_url_get](r6-url-encoding-and-getters.md#u-770bb73cd6cf), [curl_url_set](r6-url-handle-api.md#u-68d6b32905a9), [helpf](r5-tool-messaging.md#u-0be25ff8537d)

**Uncertainties.**

- Whether the input CURLU handle uh is left usable when the function fails midway is not determinable here, since parts may already have been overwritten before the failure.
- The exact set of CURLUcode conditions mapping to the leading goto clean paths beyond those checked is library-defined.

<a id="u-a4cf41f5106b"></a>
### `ipfs_gateway`

`static char *ipfs_gateway(void)` · [src/tool_ipfs.c:L39-L97][f1]

Resolves an IPFS gateway URL string, returning a heap string or NULL.

First the IPFS_GATEWAY environment variable is returned as-is if set. Otherwise it reads IPFS_PATH, falling back to '<HOME>/.ipfs/' when HOME is set and non-empty; if neither yields a path it fails. It composes '<path>/gateway' (adding a separating slash only when the path lacks a trailing one, using has_trailing_slash), opens that file read-only, and reads its first line up to EOF, '\n' or '\r' into a dynbuf capped at MAX_GATEWAY_URL_LEN. If the line is non-empty the dynbuf pointer is returned; an empty file yields NULL. Any allocation, fopen, or dynbuf failure jumps to a fail path that closes the file and frees the IPFS path before returning NULL. The gateway file handle and ipfs_path_c are always released on the success path too.

calls: [ipfs_gateway](r6-tool-ipfs-rewrite.md#u-a4cf41f5106b), [curl_getenv](r8-netrc-credentials.md#u-88fda3b63c5f)

**Uncertainties.**

- The lifetime of the returned dynbuf pointer is not shown here; nothing in this function copies it out or frees the dynbuf buffer, so ownership is unclear from this source alone.
- Behavior when IPFS_PATH is set but HOME-based fallback applies is confined to string composition shown here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_ipfs.c
