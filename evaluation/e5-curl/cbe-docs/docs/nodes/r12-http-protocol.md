# HTTP protocol semantics

**Capability.** HTTP-specific request/response handling: the HTTP/1 parser interface, AWS SigV4 signing entry point, HSTS cache types, cookie jar state, and chunked Transfer-Encoding codec.

Use this subtree for HTTP wire-semantics work. Cookies and chunked coding are split into their own children because each is a self-contained capability.

**Children.**

- [Chunked transfer codec](r12-http-chunked-transfer.md) `r12-http-chunked-transfer` · 10 unit(s)
- [Cookie jar](r12-cookie-jar.md) `r12-cookie-jar` · 0 unit(s)

**Depends on.**

- [Cookie jar](r12-cookie-jar.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r12-http-protocol ` → ` r12-cookie-jar `)

Parent: [Protocol engines](r12-protocol-engines.md)

## Units (3)

<a id="u-e2df557e91ef"></a>
### `http1-h-parser-declarations`

`struct h1_req_parser` · [lib/http1.h:L37-L45][f1]

Header for the HTTP/1 request parser.

Declares parse option flags (none/strict), the default max line length, the h1_req_parser struct holding a parsed httpreq, a scratch dynbuf with skip offset, the current line pointer, length limits, and a done flag, plus lifecycle and use functions: parse init/free, incremental parse from a read buffer with default scheme and custom method options, debug printing of a request into a dynbuf, and head serialization with a chosen HTTP minor version. Declarations only; no implementation in this file.

**Uncertainties.**

- The declared functions' behavior is defined elsewhere and not in this batch.

<a id="u-d9d9029a727f"></a>
### `http_aws_sigv4.h module code (L1–L34)`

`module_region` · [lib/http_aws_sigv4.h:L1-L34][f2]

Header declaring the SigV4 authentication entry point.

After the license banner it includes curl_setup.h, curlx/dynbuf.h, and urldata.h, then declares CURLcode Curl_output_aws_sigv4(struct Curl_easy *data) for creating aws_sigv4 header output. It contains no behavior of its own.

<a id="u-2ca93a4c9526"></a>
### `hsts-h-types-and-api`

`struct stsentry` · [lib/hsts.h:L41-L46][f3]

Declares HSTS cache types and API, conditionally compiled.

With HTTP and HSTS enabled, MAX_HSTS_ENTRIES caps the cache at 10000 entries and 'deltatime' is an externally provided time offset in DEBUGBUILD/UNITTESTS builds. struct stsentry is a list node with 'expires' timestamp, an includeSubDomains bit, and a flexible 'host' array supporting tailmatching; struct hsts wraps the list plus a save filename and flags. Prototyped operations: init, cleanup, copy, parse of an HSTS header for a hostname, save to file, load from file/callback/files, and Curl_hsts_applies testing whether a destination peer must be HTTPS per cache policy. Disabled builds get no-op macros: cleanup and save expand to nothing, loadcb and loadfiles return CURLE_OK.

group: [hsts-h-types-and-api](r12-http-protocol.md#u-2ca93a4c9526)

**Uncertainties.**

- Curl_hsts_parse and Curl_hsts_applies semantics (expiry handling, subdomain matching details) are implemented in hsts.c.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http1.h
[f2]: ../../../../../../eval/curl-2c04412/lib/http_aws_sigv4.h
[f3]: ../../../../../../eval/curl-2c04412/lib/hsts.h
