# Generic TLS verification utilities

**Capability.** Backend-independent pinned public key verification and management of per-transfer certificate info lists.

These utilities operate regardless of the TLS backend chosen. Pinned-key checking parses and matches keys; certinfo maintains data->info.certs.

**Depended on by.**

- [SSL connection filter](r15-tls-cfilter.md) · model-inferred · 0 edge(s)

Parent: [TLS layer \(vtls\)](r15-tls-layer.md)

## Units (2)

<a id="u-15793be97ff2"></a>
### `vtls.c-pinned-pubkey`

`static CURLcode pubkey_pem_to_der(const char *pem, unsigned char **der, size_t *der_len)` · [lib/vtls/vtls.c:L381-L436][f1]

Implements generic pinned public key verification.

Curl_pin_peer_pubkey returns CURLE_OK immediately when no pin is configured, and CURLE_SSL_PINNEDPUBKEYNOTMATCH when the peer key is missing/empty. For 'sha256//' pins it requires Curl_ssl->sha256sum (otherwise NOTMATCH), computes and base64-encodes the peer key digest, then compares against each ';'-separated pin entry, returning CURLE_OK on the first exact length+content match; allocation failure returns CURLE_OUT_OF_MEMORY and digest/encode errors propagate. Otherwise the pin is treated as a file path: an unopenable file yields NOTMATCH; the file must be fseek/ftell-readable, non-negative and at most MAX_PINNED_PUBKEY_SIZE, and no larger than the peer key, else NOTMATCH. The file is read in 1024-byte chunks into a dynbuf (short reads or dynbuf errors jump to cleanup with NOTMATCH). Equal file/peer sizes force a direct binary DER comparison; otherwise the file is converted via pubkey_pem_to_der, which requires the PEM at line start (or after \n), a matching END marker, strips CR/LF, base64-decodes the body, and returns CURLE_BAD_CONTENT_ENCODING for missing/malformed PEM or an empty body; a decoded size-and-content match then returns CURLE_OK. All paths free the dynbuf, decoded buffer, and file handle.

**Uncertainties.**

- base64 decode failure inside pubkey_pem_to_der propagates its CURLcode, whose identity is defined in curlx/base64.h, not shown.

<a id="u-5b2ec653236c"></a>
### `vtls.c-certinfo`

`void Curl_ssl_free_certinfo(struct Curl_easy *data)` · [lib/vtls/vtls.c:L296-L311][f1]

Manages the per-transfer certificate info lists in data->info.certs.

Free iterates num_of_certs slists, frees each, frees the array, and resets the count; it does nothing when the count is zero. Init first frees any previous info, then callocs a table of 'num' slist pointers; allocation failure returns CURLE_OUT_OF_MEMORY leaving previous data already freed, success stores the table and count. Push builds a 'label:value' string from a non-null-terminated value using a dynbuf capped at CURL_X509_STR_MAX, returning CURLE_OUT_OF_MEMORY if any dynbuf add fails; on append failure it frees the built string and the whole per-cert list and reports out-of-memory, otherwise the new node becomes the list head. A DEBUGASSERT guards certnum < num_of_certs.

**Uncertainties.**

- Push indexes ci->certinfo[certnum] without a runtime bounds check; only the DEBUGASSERT covers an out-of-range certnum in debug builds.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/vtls.c
