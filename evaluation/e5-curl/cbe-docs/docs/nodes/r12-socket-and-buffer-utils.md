# Socket, buffer, and integer utilities

**Capability.** Portable blocking/non-blocking socket switching, the dynbuf dynamic-buffer API, and safe narrowing/widening integer conversion helpers that suppress compiler warnings.

Use curlx_nonblock for socket modes, dyn_* for growable buffers, and the warnless conversions at every size-reducing assignment.

**Depended on by.**

- [Chunked transfer codec](r12-http-chunked-transfer.md) · graph-confirmed · 1 edge(s)
- [MD5 digest service](r12-md5-digest.md) · graph-confirmed · 24 edge(s)
- [Write-out output](r12-writeout-output.md) · model-inferred · 0 edge(s)

Parent: [Portable utilities](r12-portable-utils.md)

## Units (3)

<a id="u-3b381dd4a464"></a>
### `curlx_nonblock`

`int curlx_nonblock(curl_socket_t sockfd, /* operate on this */ int nonblock /* TRUE o…` · [lib/curlx/nonblock.c:L45-L92][f1]

Sets a socket to blocking or non-blocking mode, portable across platforms via compile-time selection.

On Unix (HAVE_FCNTL_O_NONBLOCK) it reads the file status flags with sfcntl(F_GETFL), returning -1 on failure; if the O_NONBLOCK bit already matches the request it returns 0 without a syscall, otherwise it sets or clears the bit and returns the result of sfcntl(F_SETFL). Amiga uses IoctlSocket(FIONBIO), older Unix uses ioctl(FIONBIO), Windows uses ioctlsocket(FIONBIO), Orbis uses setsockopt(SO_NONBLOCK), each passing 1 or 0 per the nonblock flag and returning the underlying call's status. If no method is configured the file fails to compile via #error.

**Uncertainties.**

- Which platform branch applies depends on build configuration macros not visible here

<a id="u-a7ccbf94cd93"></a>
### `dynbuf`

`struct dynbuf` · [lib/curlx/dynbuf.h:L27-L35][f2]

Declares the dynbuf struct backing the curlx_dyn_* dynamic-buffer API.

bufr points to a null-terminated allocated buffer, leng counts bytes excluding the terminator, allc is the current allocation size, and toobig is the buffer's maximum size; under DEBUGBUILD an init field detects API misuse. The header only declares state and the API contract; behavior lives in the implementations not shown here.

**Uncertainties.**

- Semantics of the init debug field depend on the implementation in other files.

<a id="u-97fe403e2706"></a>
### `warnless.c-narrowing-conversions`

`unsigned char curlx_ultouc(unsigned long ulnum)` · [lib/curlx/warnless.c:L59-L63][f3]

Safe narrowing/widening integer conversion helpers that suppress compiler warnings and document range assumptions.

Most one-value converters mask the input to the target's range and cast: curlx_ultouc, curlx_uztosi, curlx_uztoul, curlx_uztoui, curlx_sltosi, curlx_sltoui, curlx_sltous, curlx_uztosz, curlx_sotouz, curlx_sztosi, curlx_uitous all AND with the target mask (some masks checked under DEBUGASSERT only when the source type is actually wider, e.g. ULONG_MAX < SIZE_MAX guards in curlx_uztoul). curlx_sitouz and curlx_uitouz are plain casts asserting/asserting-nothing non-negativity. Range-checking variants behave differently: curlx_sotouz_range clamps a signed curl_off_t to [uzmin, uzmax], returning uzmin for negatives and uzmax when the value exceeds SIZE_MAX (checked only when curl_off_t is wider than size_t); curlx_sztouz, curlx_sotouz_fits, and curlx_sltouz return FALSE and set *puznum = 0 for negatives (and, for curlx_sotouz_fits, values above SIZE_MAX when curl_off_t is wider), otherwise store the value and return TRUE. curlx_uztoso converts size_t to curl_off_t, saturating at CURL_OFF_T_MAX when size_t is at least as wide as curl_off_t. Signed-input converters assert non-negative input under DEBUGASSERT.

**Uncertainties.**

- DEBUGASSERT behavior (assert vs no-op) depends on build configuration; without asserts, out-of-range inputs are silently truncated by the mask.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curlx/nonblock.c
[f2]: ../../../../../../eval/curl-2c04412/lib/curlx/dynbuf.h
[f3]: ../../../../../../eval/curl-2c04412/lib/curlx/warnless.c
