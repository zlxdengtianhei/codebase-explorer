# Small Shared Utilities

**Capability.** Owns generic leaf helpers with no protocol policy: random data generation (crypto or weak fallback), a growable pointer array, memrchr replacement, hostname lookup, line reading declaration, and the generic HMAC abstraction header.

Use this child when a cross-cutting primitive is needed; it intentionally knows nothing about transfers. randit delegates to TLS or weak randomness with a debug entropy override.

Parent: [curl Codebase](r10-curl-source.md)

## Units (11)

<a id="u-fc97999f6848"></a>
### `Curl_rand_alnum`

`CURLcode Curl_rand_alnum(struct Curl_easy *data, unsigned char *rnd, size_t num)` · [lib/rand.c:L207-L230][f1]

Fills a buffer with random alphanumeric characters from a 62-character alphabet plus a terminating null.

num must exceed 1 (DEBUGASSERT); it decrements num to reserve the null. For each output character it repeatedly calls randit(data, &r, TRUE) until r falls below UINT_MAX minus UINT_MAX % 62, avoiding modulo bias; on randit error it returns immediately, discarding partial output. Each accepted draw yields alnum[r % 62]. It finally writes *rnd = 0 and returns CURLE_OK (unless an error occurred). The env_override argument TRUE has no effect outside DEBUGBUILD.

calls: [randit](r10-misc-utilities.md#u-cd484a4da017)

<a id="u-c3e86a9c4806"></a>
### `Curl_rand_bytes`

`CURLcode Curl_rand_bytes(struct Curl_easy *data, #ifdef DEBUGBUILD bool env_override,…` · [lib/rand.c:L139-L169][f1]

Fills a caller buffer of arbitrary length with random bytes by repeatedly drawing 32-bit words.

DEBUGASSERT(num) rejects zero-length requests in debug builds; result starts as CURLE_BAD_FUNCTION_ARGUMENT. Each loop iteration draws one unsigned int via randit; if randit returns an error the function returns it immediately. Otherwise it emits up to sizeof(unsigned int) bytes little-endian style (r & 0xFF, then shifts), decrementing num, until the buffer is full. In non-debug builds env_override is a fixed FALSE, so the CURL_ENTROPY override never applies. The docstring notes data may be NULL when there is no easy handle.

calls: [randit](r10-misc-utilities.md#u-cd484a4da017)

<a id="u-a2eb969bfb7d"></a>
### `Curl_rand_hex`

`CURLcode Curl_rand_hex(struct Curl_easy *data, unsigned char *rnd, size_t num)` · [lib/rand.c:L177-L197][f1]

Fills a buffer with random hexadecimal digits plus a terminating null.

It requires num > 1 (DEBUGASSERT) and rejects with CURLE_BAD_FUNCTION_ARGUMENT, after a DEBUGF infof message, when num is even (num & 1 false) or num/2 >= sizeof(buffer) (a 128-byte stack scratch). It then decrements num to reserve the null byte, draws num/2 random bytes via Curl_rand (which on failure is returned directly), and hex-encodes them with Curl_hexencode into the caller buffer sized num+1, which includes the null terminator.

calls: [Curl_hexencode](r7-string-escape-utils.md#u-9e7ae5f6fc46)

**Uncertainties.**

- Curl_rand is presumably Curl_rand_bytes; its exact signature with env_override is not shown in this file

<a id="u-cd484a4da017"></a>
### `randit`

`static CURLcode randit(struct Curl_easy *data, unsigned int *rnd, bool env_override)` · [lib/rand.c:L87-L122][f1]

Produces one random unsigned int, honoring the debug-only CURL_ENTROPY override and delegating to TLS or weak randomness.

In DEBUGBUILD, when env_override is true and CURL_ENTROPY is set, it seeds a static randseed once from the string bytes (memcpy up to sizeof(unsigned int), converted with ntohl) and returns it; on subsequent calls it simply increments randseed, so debug runs get deterministic, incrementing values. Outside DEBUGBUILD env_override is discarded. data may be NULL. When USE_SSL is defined it returns Curl_ssl_random(data, rnd, sizeof(*rnd)); otherwise it returns weak_random(data, rnd, sizeof(*rnd)).

calls: [weak_random](r10-misc-utilities.md#u-f5dec450abed)

**Uncertainties.**

- Curl_ssl_random failure semantics when USE_SSL is defined are defined in vtls, not here

<a id="u-f5dec450abed"></a>
### `weak_random`

`static CURLcode weak_random(struct Curl_easy *data, unsigned char *entropy, size_t le…` · [lib/rand.c:L40-L84][f1]

Fills a 4-byte buffer with entropy using platform randomness when available, falling back to a time-seeded LCG.

Only compiled when USE_SSL is off. DEBUGASSERT requires length == sizeof(int). Under _WIN32 it first tries curlx_win32_random and returns its result unless it is CURLE_NOT_BUILT_IN, in which case it falls through to later options. If HAVE_ARC4RANDOM, it copies arc4random() into the buffer. Otherwise it logs 'WARNING: using weak random seed' via infof, seeds a function-static randseed once using curlx_pnow (microseconds plus seconds fed through three LCG rounds), then advances randseed one LCG step and writes the word-swapped value into the buffer. The static randseed/seeded state persists across calls, making this non-thread-safe at first-call seeding. data is unused on the cryptographic paths.

calls: [lib/curl_trc.c:Curl_infof](r1-trace-logging.md#u-b6145e5eb5c9), [timeval.c-pnow](r9-time-utils.md#u-001b742a8ba1)

**Uncertainties.**

- Whether curlx_win32_random can fail with codes other than CURLE_OK or CURLE_NOT_BUILT_IN is outside this file

<a id="u-98058dbc9271"></a>
### `ptrarray.c-api`

`void Curl_ptrarray_init(struct ptrarray *pa)` · [lib/ptrarray.c:L30-L34][f2]

A growable array of up to UINT32_MAX pointers.

Curl_ptrarray_add rejects NULL with CURLE_BAD_FUNCTION_ARGUMENT; when full it grows by 8 initially, then CURLMIN(2*capacity, 16384), and near UINT32_MAX by the remaining headroom clamped to 16384; capacity==UINT32_MAX or allocation failure yields CURLE_OUT_OF_MEMORY, and the old buffer is freed only after a successful realloc-copy. Curl_ptrarray_remove out-of-range returns NULL; in-range it NULLs the slot, memmoves the tail down, decrements n, and frees the buffer entirely (Curl_ptrarray_clear) when the array becomes empty. Curl_ptrarray_init zeroes the struct, Curl_ptrarray_clear frees the buffer and resets counts, Curl_ptrarray_count returns n, and Curl_ptrarray_get returns the entry or NULL when idx >= n; the header macros CURL_PTRARRAY_COUNT and CURL_PTRARRAY_GET duplicate count and bounds-checked access inline.

<a id="u-bfc741d2cc93"></a>
### `Curl_memrchr`

`void *Curl_memrchr(const void *s, int c, size_t n)` · [lib/curl_memrchr.c:L37-L52][f3]

Backward byte search over n bytes, providing a memrchr() replacement on systems lacking one.

When n is 0 it returns NULL immediately. Otherwise it starts a pointer p at the last byte (s + n - 1) and a pointer q at the first byte, then scans toward the front: the first byte equal to (unsigned char)c is returned as a non-const pointer via CURL_UNCONST. If the loop walks past q without a match, it falls through to returning NULL. Compilation of this definition is guarded by #ifndef HAVE_MEMRCHR, so on platforms with a native memrchr this function is absent and the header callers use the system function instead.

**Notes.**

- side_effect: Pure search with no state change; returns a pointer into the caller's buffer.
- contract: Caller-supplied macro in curl_memrchr.h maps memrchr(x,y,z) to Curl_memrchr(x,y,z) when HAVE_MEMRCHR is undefined.

**Uncertainties.**

- Whether comparing pointers p >= q after p decrements below the array start is well-defined is a portability question; behavior on the intended platforms matches the return-NULL intent but standard C does not define pointer comparison below an object.

<a id="u-cd704092da51"></a>
### `Curl_gethostname`

`int Curl_gethostname(char * const name, GETHOSTNAME_TYPE_ARG2 namelen)` · [lib/curl_gethostname.c:L44-L96][f4]

Returns the local machine's un-qualified hostname into a caller-provided buffer, optionally overridden via an environment variable in debug builds.

When HAVE_GETHOSTNAME is undefined it voids both arguments and returns -1 without touching the buffer. With DEBUGBUILD defined, getenv("CURL_GETHOSTNAME") is checked: if set and its length is strictly less than namelen, it is copied into the buffer via curlx_strcopy and err is 0; if set but too long, the function returns 1 without writing; if unset, the buffer's first byte is NUL-terminated and gethostname(name, namelen) is called. Without DEBUGBUILD, the buffer is NUL-seeded and gethostname is called directly (with an unsigned char* cast on __AMIGA__). After either path, name[namelen - 1] is forced to NUL. If gethostname returned an error (err nonzero), that err value is returned before truncation; otherwise the first '.' in the result is replaced with NUL, leaving only the machine name, and 0 is returned. Callers such as smtp_parse_url_path rely on this for a hostname when none is supplied.

**Notes.**

- failure: An oversized CURL_GETHOSTNAME value in debug builds returns 1; a gethostname failure propagates the gethostname error code.
- side_effect: name[namelen-1] is unconditionally NUL-terminated even on error paths that reached the copy or gethostname call.

uses: [lib/curl_gethostname.h][f5], [lib/curlx/strcopy.h][f6]

**Uncertainties.**

- The exact numeric value and meaning of gethostname's error return are provider-dependent and not visible here; the code propagates it verbatim.
- Whether curlx_strcopy truncates or otherwise bounds its write when the source length already passed the length check is defined elsewhere and not shown.

<a id="u-048714253be5"></a>
### `curl_get_line.h module code (L1–L31)`

`module_region` · [lib/curl_get_line.h:L1-L31][f7]

Header declaring Curl_get_line() (dynbuf, FILE*, eof out-param) with include guard and dynbuf include; declarations only.

<a id="u-7a4b47968a02"></a>
### `HMAC_params`

`struct HMAC_params` · [lib/curl_hmac.h:L41-L48][f8]

Function-pointer table selecting a hash backend for generic HMAC computation.

It bundles init/update/final callbacks, the backend context structure size, the maximum HMAC key length in bytes, and the digest result length, so generic HMAC code can drive any hash algorithm uniformly.

**Notes.**

- contract: Callback signatures are aliased by HMAC_hinit, HMAC_hupdate, and HMAC_hfinal defined just above; the whole declaration block is compiled out unless one of NTLM-core, AWS, Digest, HTTPSIG, LIBSSH2, or SSL features is enabled.

uses: [HMAC_params](r10-misc-utilities.md#u-7a4b47968a02)

<a id="u-6b3799dba9ce"></a>
### `HMAC_context`

`struct HMAC_context` · [lib/curl_hmac.h:L51-L55][f8]

State holder for an in-progress HMAC computation: a pointer to the HMAC_params hash definition plus two opaque hash contexts (hashctxt1 and hashctxt2) for the inner and outer keyed hash passes.

The trailing prototype block declares the Curl_HMAC_* API that consumes this structure.

uses: [HMAC_params](r10-misc-utilities.md#u-7a4b47968a02)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/rand.c
[f2]: ../../../../../../eval/curl-2c04412/lib/ptrarray.c
[f3]: ../../../../../../eval/curl-2c04412/lib/curl_memrchr.c
[f4]: ../../../../../../eval/curl-2c04412/lib/curl_gethostname.c
[f5]: ../../../../../../eval/curl-2c04412/lib/curl_gethostname.h
[f6]: ../../../../../../eval/curl-2c04412/lib/curlx/strcopy.h
[f7]: ../../../../../../eval/curl-2c04412/lib/curl_get_line.h
[f8]: ../../../../../../eval/curl-2c04412/lib/curl_hmac.h
