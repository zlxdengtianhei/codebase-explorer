# Public URL API header

**Capability.** Declares curl's public URL parsing API: the CURLUcode result-code vocabulary (including the CURLUE_NO_* absent-component codes) and the CURLUPart enum naming URL components for get/set.

Use this header as the contract for URL parsing consumers; the enums define the error and part vocabularies. No implementation lives in this excerpt.

Parent: [curl codebase](r9-curl-source.md)

## Units (3)

<a id="u-68222fde0c6a"></a>
### `urlapi-h-url-parsing-api`

`enum` · [include/curl/urlapi.h:L34-L69][f1]

Declares curl's URL parsing API.

CURLUcode enumerates success, argument/handle errors (bad handle, bad part pointer), parse failures (malformed input, bad port/scheme/hostname/IPv6/login/password/path/query/scheme/slashes/user, backslash, URL-decode, out of memory, user not allowed, lacks IDN, too large, bad file URL), and CURLUE_NO_* codes for absent components, ending in CURLUE_LAST. CURLUPart names the extractable parts: full URL, scheme, user, password, options, host, port, path, query, fragment, and zoneid. The CURLU_* flag bits (bits 0-15) modify behavior per call: default port or scheme substitution, non-supported schemes, dot-segment preservation, user disallowal, URL encode/decode, query append, scheme guessing (and its negation for get), empty authority, spaces, punycode/IDN conversion, and empty query/fragment extraction. curl_url creates a CURLU handle freed by curl_url_cleanup; curl_url_dup copies a handle; curl_url_get extracts a part into a string the caller must free with curl_free; curl_url_set copies the input string and clears the part when given NULL; curl_url_strerror maps a CURLUcode to a human-readable string. Only declarations appear here.

**Notes.**

- contract: Strings returned by curl_url_get must be freed with curl_free; curl_url_cleanup does not free previously returned strings.

uses: [include/curl/urlapi.h:<enum>](r9-public-headers.md#u-804e6fca87f6), [include/curl/urlapi.h:<enum> (2)](r9-public-headers.md#u-19980d164203), [urlapi-h-url-parsing-api](r9-public-headers.md#u-68222fde0c6a)

**Uncertainties.**

- Which flag combinations are valid for which part, and set/get restrictions per part, are defined by the implementation, not this header.

<a id="u-804e6fca87f6"></a>
### `include/curl/urlapi.h:<enum>`

`enum` · [include/curl/urlapi.h:L34-L69][f1]

CURLUcode enum of URL API result codes: success, argument/handle errors, parse failures, and CURLUE_NO_* codes indicating an absent component (scheme, user, password, options, host, port, query, fragment, zoneid), terminated by CURLUE_LAST.

<a id="u-19980d164203"></a>
### `include/curl/urlapi.h:<enum> (2)`

`enum` · [include/curl/urlapi.h:L71-L83][f1]

CURLUPart enum naming URL components for get/set: full URL, scheme, user, password, options, host, port, path, query, fragment, zoneid.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/include/curl/urlapi.h
