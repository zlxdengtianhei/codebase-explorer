# Cookie line parsing and matching

**Capability.** Turns Set-Cookie headers and Netscape file lines into Cookie structs while enforcing attribute validation: domain checks, expiry caps, public-suffix and control-octet rejection, plus RFC6265 domain/path matching used at lookup time.

Read for any attribute-level policy change. These helpers are called by Curl_cookie_add and Curl_cookie_getlist; they never touch jar storage themselves.

Parent: [Cookie jar](r12-cookie-jar.md)

## Units (13)

<a id="u-db38517279ed"></a>
### `parse_cookie_header`

`static CURLcode parse_cookie_header(struct Curl_easy *data, struct Cookie *co, bool *…` · [lib/cookie.c:L565-L655][f1]

Parses a full Set-Cookie header line into a Cookie struct, attribute by attribute.

**Notes.**

- condition: Lines over MAX_COOKIE_LINE are silently discarded (returns CURLE_OK with *okay FALSE).
- failure: Invalid octets in name or value, an invalid first pair, an unsecure origin for a 'secure' attribute, or a bad Domain attribute all drop the cookie with CURLE_OK; only allocation failures propagate errors via storecookie.
- condition: Attributes only take effect when followed by '='; 'path', 'domain', 'max-age' and 'expires' are recognized case-insensitively; the name must be present for the cookie to be stored.
- side_effect: Sets *okay TRUE only after storecookie succeeds.

<a id="u-b00314911e82"></a>
### `parse_netscape`

`static CURLcode parse_netscape(struct Cookie *co, const struct CookieInfo *ci, bool *…` · [lib/cookie.c:L657-L788][f1]

Parses one Netscape-format cookie file line into a Cookie struct.

**Notes.**

- condition: A '#HttpOnly_' prefix is consumed and marks the cookie httponly; any other '#' line is ignored as a comment.
- condition: Field 0 is the domain (leading dot skipped), 1 sets tailmatch from TRUE, field 2 holds the path unless it reads TRUE/FALSE (then a default '/' and fallthrough to secure), field 3 secure (TRUE requires a secure origin or an already-running jar, otherwise the cookie is dropped), field 4 expiry (bad number drops the cookie), 5 name with prefix detection, 6 value.
- condition: Exactly 6 fields get an empty value; any count other than 7 after processing leaves *okay FALSE.
- failure: Control octets in name or value drop the cookie; allocation failures return CURLE_OUT_OF_MEMORY.

<a id="u-0904233f64b5"></a>
### `parse_domain`

`static bool parse_domain(struct Curl_easy *data, struct Cookie *co, struct Curl_str *…` · [lib/cookie.c:L452-L503][f1]

Validates a Domain attribute against the current host, storing it on the cookie or rejecting the cookie.

**Notes.**

- condition: A leading dot is nudged off the value; without PSL a bad domain (no real dot, not localhost) replaces the default domain with ':' which cannot match.
- condition: Accepts when there is no default domain, the value is the full IP host, or the value tail-matches the host; otherwise logs 'bad tailmatch' and returns FALSE.
- side_effect: On acceptance sets cookie[COOKIE_DOMAIN] and, for non-IP domains, co->tailmatch = TRUE.

<a id="u-944f35376bbb"></a>
### `parse_expires`

`static void parse_expires(struct Cookie *co, struct Curl_str *val, time_t *nowp)` · [lib/cookie.c:L537-L562][f1]

Applies an Expires date attribute, only if Max-Age has not already set an expiry and the date is under 80 bytes.

**Notes.**

- condition: Unparseable dates leave the cookie as a session cookie (expires 0); a parsed 0 date becomes 1; cap_expires applies after.

<a id="u-2f25bf27fbbe"></a>
### `parse_maxage`

`static void parse_maxage(struct Cookie *co, struct Curl_str *val, time_t *nowp)` · [lib/cookie.c:L505-L535][f1]

Applies a Max-Age attribute as an absolute expiry time on the cookie.

**Notes.**

- condition: An optional leading quote is skipped; number overflow sets expires to CURL_OFF_T_MAX, any other parse error sets expires to 1 (expire immediately), and a parsed 0 also expires now.
- condition: A valid value is added to the lazily-fetched current time, capped at CURL_OFF_T_MAX, then passed through cap_expires.

<a id="u-e45b51046ed0"></a>
### `parse_first_pair`

`static bool parse_first_pair(struct Curl_easy *data, struct Cookie *co, struct Curl_s…` · [lib/cookie.c:L419-L450][f1]

Validates and stores the first name=value pair of a Set-Cookie header, detecting __Secure-/__Host- prefixes.

**Notes.**

- condition: Drops the cookie when there is no separator (missing '=') or an empty name; drops when name+value exceeds MAX_NAME.
- side_effect: Sets co->prefix_secure for names starting '__Secure-' and co->prefix_host for '__Host-' (case-sensitive strncmp).

<a id="u-fc1c74f9c0a4"></a>
### `invalid_octets`

`static bool invalid_octets(const char *ptr, size_t len)` · [lib/cookie.c:L346-L357][f1]

Detects control bytes (below 0x20 and 0x7f) in a string; stops at the first NUL byte.

**Notes.**

- contract: Len is an upper bound; embedded NUL terminates the scan, so bytes after a NUL are not validated.

<a id="u-bd1f44b15e8e"></a>
### `is_public_suffix`

`static bool is_public_suffix(struct Curl_easy *data, struct Cookie *co, const char *d…` · [lib/cookie.c:L790-L867][f1]

With libpsl, rejects cookies set for public-suffix domains; without it, always returns FALSE.

**Notes.**

- condition: IP-address domains and file-loaded cookies with no domain pass. An acceptable cookie that equals the setting domain while being a public suffix loses tailmatch; a public-suffix cookie set from file is rejected and also loses tailmatch.
- failure: If the PSL context cannot be acquired, the cookie is rejected for safety.

<a id="u-1c6e0e8265f0"></a>
### `bad_domain`

`static bool bad_domain(const char *domain, size_t len)` · [lib/cookie.c:L320-L335][f1]

Without PSL, rejects domains lacking a non-trailing dot unless the domain is exactly 'localhost'.

**Notes.**

- condition: A trailing dot alone does not count as a valid dot, so 'example.com.' is rejected.

<a id="u-cfa86e66e6b3"></a>
### `cap_expires`

`static void cap_expires(time_t now, struct Cookie *co)` · [lib/cookie.c:L53-L62][f1]

Caps a cookie's expiry to at most 400 days in the future, aligned to a 60-second boundary.

uses: [cap_expires](r12-cookie-parsing.md#u-cfa86e66e6b3)

**Uncertainties.**

- Depends on TIME_T_MAX and COOKIES_MAXAGE semantics; the overflow-guard condition (TIME_T_MAX - COOKIES_MAXAGE - 30) > now is assumed to mean 'safe to add'.

<a id="u-eb1054ec1194"></a>
### `cookie_tailmatch`

`static bool cookie_tailmatch(const char *cookie_domain, const size_t cookie_domain_le…` · [lib/cookie.c:L74-L101][f1]

Returns TRUE when hostname ends with cookie_domain at a domain-label boundary.

<a id="u-086ed275cfbf"></a>
### `pathmatch`

`static bool pathmatch(const char *cookie_path, const char *uri_path)` · [lib/cookie.c:L107-L157][f1]

Implements RFC6265 5.1.4 path matching between a cookie path and a URI path.

**Notes.**

- condition: A one-character cookie path ('/') always matches; an empty or non-slash URI path is treated as '/'; the URI path must equal the cookie path or continue it with a '/'.

<a id="u-31103f8e3261"></a>
### `sanitize_cookie_path`

`static char *sanitize_cookie_path(const char *cookie_path, size_t len)` · [lib/cookie.c:L227-L249][f1]

Normalizes a cookie Path attribute: strips surrounding quotes, returns '/' for empty or non-slash paths, and removes a trailing slash from longer paths.

uses: [sanitize_cookie_path](r12-cookie-parsing.md#u-31103f8e3261)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cookie.c
