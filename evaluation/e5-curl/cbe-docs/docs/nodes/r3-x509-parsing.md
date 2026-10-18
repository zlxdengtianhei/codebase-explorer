# ASN.1 / X.509 Parsing

**Capability.** Parses DER-encoded X.509 certificates into a Curl_X509certificate and renders their elements as printable strings: generic ASN.1 element parsing, per-type converters (times, strings, OIDs, booleans, bit/octets, integers), distinguished-name and public-key rendering, and an OID lookup table.

Use this subtree to understand how certificate fields become the certinfo records surfaced via curl_easy_getinfo and verbose output. Element parsing is recursive; conversion dispatch lives in ASN1tostr and DNtostr.

**Depends on.**

- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) · model-inferred · 0 edge(s)

Parent: [TLS Certificate Handling](r3-tls-certificates.md)

## Units (24)

<a id="u-f371ece802ee"></a>
### `x509asn1.c module code (L1–L55)`

`module_region` · [lib/vtls/x509asn1.c:L1-L55][f1]

Compilation prologue: copyright header, includes, and feature macros.

The file compiles only under USE_GNUTLS, USE_WOLFSSL, USE_SCHANNEL, USE_MBEDTLS, or USE_RUSTLS; within that, WANT_PARSEX509 enables Curl_parseX509 and WANT_EXTRACT_CERTINFO enables the conversion and certinfo code.

<a id="u-730f0ab36195"></a>
### `getASN1Element_`

`static const uint8_t *getASN1Element_(struct Curl_asn1Element *elem, const uint8_t *b…` · [lib/vtls/x509asn1.c:L130-L198][f1]

Parses a single ASN.1 element from beg..end into elem and returns a pointer just past it, or NULL on rejection.

The guard rejects NULL pointers, empty ranges, sizes over CURL_ASN1_MAX (256K), or recursion depth at CURL_ASN1_MAX_RECURSIONS (16). It decodes the header byte into constructed flag, class, and low 5 tag bits (long-form tag 0x1F is unsupported). Short-form lengths are used directly; a 0x80 length byte requires a constructed element and its length is resolved by recursively skipping sub-elements until a zero terminator byte (missing terminator returns NULL). Long-form lengths over 4 bytes, or any length exceeding the remaining source, return NULL. On success elem->beg/end cover the content.

**Notes.**

- failure: All malformed inputs yield NULL rather than an error code.

calls: [getASN1Element_](r3-x509-parsing.md#u-730f0ab36195)

**Uncertainties.**

- Whether elem fields are meaningful to callers after a NULL return is not established here.

<a id="u-c98f0d77a08a"></a>
### `getASN1Element`

`UNITTEST const uint8_t *getASN1Element(struct Curl_asn1Element *elem, const uint8_t *…` · [lib/vtls/x509asn1.c:L205-L209][f1]

Public wrapper that parses one ASN.1 element at recursion depth 0 by delegating to getASN1Element_; same NULL-on-error contract.

calls: [getASN1Element_](r3-x509-parsing.md#u-730f0ab36195)

<a id="u-45d061f00619"></a>
### `x509asn1.c-oid-table`

`struct Curl_OID` · [lib/vtls/x509asn1.c:L56-L59][f1]

OID lookup data for X.509 field naming.

struct Curl_OID pairs a dotted-numeric OID with its symbolic text name; the static OIDtable array lists signature/hash algorithms (RSA, DSA, ECDSA, SHA family), public-key algorithms, X.500 DN attribute names (CN, C, O, OU, etc.), and certificate extensions (subjectAltName, issuerAltName, basicConstraints), terminated by a NULL/NULL sentinel that searchOID relies on. Pure data, no behavior.

<a id="u-8c6e063b2791"></a>
### `searchOID`

`static const struct Curl_OID *searchOID(const char *oid)` · [lib/vtls/x509asn1.c:L217-L225][f1]

Linearly scans the static OIDtable, comparing the argument against each entry's dotted OID with strcmp (case-sensitive) or its text name with curl_strequal (case-insensitive); returns the matching entry or NULL at the sentinel.

Unknown OIDs therefore fall back to dotted form in OID2str.

<a id="u-ca524013f61f"></a>
### `bool2str`

`static CURLcode bool2str(struct dynbuf *store, const uint8_t *beg, const uint8_t *end)` · [lib/vtls/x509asn1.c:L233-L243][f1]

Converts an ASN.1 BOOLEAN to "TRUE"/"FALSE" appended to store.

Requires exactly one content byte; returns CURLE_BAD_FUNCTION_ARGUMENT if the length differs or the byte is neither 0x00 nor 0xff, otherwise appends the text via curlx_dyn_add and propagates its result.

<a id="u-40a4922774ea"></a>
### `octet2str`

`static CURLcode octet2str(struct dynbuf *store, const uint8_t *beg, const uint8_t *end)` · [lib/vtls/x509asn1.c:L250-L259][f1]

Appends each octet as two hex digits followed by a colon via curlx_dyn_addf; stops on the first dynbuf error and returns it, otherwise CURLE_OK.

Empty ranges append nothing.

<a id="u-029f83242e2c"></a>
### `bit2str`

`static CURLcode bit2str(struct dynbuf *store, const uint8_t *beg, const uint8_t *end)` · [lib/vtls/x509asn1.c:L261-L274][f1]

Converts an ASN.1 BIT STRING.

The first byte counts unused bits and is mandatory: an empty range or a count above 7 returns CURLE_BAD_FUNCTION_ARGUMENT. The remaining bytes are rendered via octet2str, whose result propagates; the unused-bit count is not reflected in the output.

calls: [octet2str](r3-x509-parsing.md#u-40a4922774ea)

<a id="u-2b1ea67ede0a"></a>
### `utf8asn1str`

`static CURLcode utf8asn1str(struct dynbuf *to, int type, const uint8_t *from, const u…` · [lib/vtls/x509asn1.c:L320-L395][f1]

Converts an ASN.1 string of a supported type into UTF-8 appended to dynbuf `to`.

BMP strings use 2-byte code units, UNIVERSAL strings 4 bytes, and NUMERIC/PRINTABLE/TELETEX/IA5/VISIBLE/UTF8 1 byte; other types return CURLE_BAD_FUNCTION_ARGUMENT. A total length not divisible by the character size returns CURLE_BAD_FUNCTION_ARGUMENT. UTF8_STRING content is copied verbatim; other types decode each code unit big-endian and re-encode as 1-4 UTF-8 bytes, with code units at or above 0x00200000 returning CURLE_WEIRD_SERVER_REPLY. Dynbuf errors abort the loop and propagate.

**Uncertainties.**

- No surrogate-pair handling is visible for BMP strings; values in 0xD800-0xDFFF are encoded as-is, so exact output for such input is unproven.

<a id="u-923fdc2a61d2"></a>
### `encodeOID`

`UNITTEST CURLcode encodeOID(struct dynbuf *store, const uint8_t *beg, const uint8_t *…` · [lib/vtls/x509asn1.c:L410-L465][f1]

Renders a raw DER OBJECT IDENTIFIER as its dotted decimal string in store.

Empty or reversed ranges return CURLE_BAD_FUNCTION_ARGUMENT. The first byte yields the leading arc (capped at 2) and the second arc with base-128 continuation bytes; a leading 0x80 padding byte for the second arc, 32-bit accumulator overflow, or truncation at range end returns CURLE_BAD_FUNCTION_ARGUMENT. Trailing arcs are decoded the same way, rejecting 0x80 padding as the first byte, 32-bit overflow, or truncated continuations. Each component is appended via curlx_dyn_addf and errors propagate.

**Notes.**

- contract: Each component is limited to unsigned 32 bits; the second arc is bounded by 4294967215 (32 bits - 80).

<a id="u-258433f93640"></a>
### `OID2str`

`static CURLcode OID2str(struct dynbuf *store, const uint8_t *beg, const uint8_t *end)` · [lib/vtls/x509asn1.c:L473-L492][f1]

Converts an OID element to its symbolic name or dotted form.

An empty range yields CURLE_OK with nothing appended. Otherwise a temporary dynbuf (limit CURL_X509_STR_MAX) receives encodeOID's dotted string; searchOID then maps it to the table's text name if known, else the dotted string is appended to store. The temporary buffer is always freed; errors propagate and skip the append.

calls: [encodeOID](r3-x509-parsing.md#u-923fdc2a61d2), [searchOID](r3-x509-parsing.md#u-8c6e063b2791)

<a id="u-1a3853b7af9e"></a>
### `GTime2str`

`UNITTEST CURLcode GTime2str(struct dynbuf *store, const char *beg, const char *end)` · [lib/vtls/x509asn1.c:L499-L575][f1]

Converts an ASN.1 GeneralizedTime to a printable string appended to store.

It scans the leading year/month/day/hour/minute digits: a digit run of 12 or 13 chars yields seconds "00"; 14 or 15 chars take the last two digits; other lengths return CURLE_BAD_FUNCTION_ARGUMENT. Optional fractional seconds after '.' or ',' require at least one digit (else CURLE_BAD_FUNCTION_ARGUMENT) and have trailing zeroes stripped. The timezone tail: absent is omitted; 'Z' renders as " GMT"; '+'/'-' renders as " UTC" plus the raw offset; any other character renders the raw tail after a space. Output format is yyyy-mm-dd hh:mm:ss[.frac][zone].

**Notes.**

- condition: A timezone tail that is neither Z nor a sign is emitted verbatim after a space rather than rejected.

<a id="u-890647ed5247"></a>
### `UTime2str`

`static CURLcode UTime2str(struct dynbuf *store, const char *beg, const char *end)` · [lib/vtls/x509asn1.c:L582-L616][f1]

Converts an ASN.1 UTCTime to a printable string.

It scans the leading digit run: exactly 12 digits give seconds from positions 10-11; exactly 10 digits substitute "00" seconds; other lengths return CURLE_BAD_FUNCTION_ARGUMENT. A timezone is mandatory (missing tail returns CURLE_BAD_FUNCTION_ARGUMENT); 'Z' renders as "GMT", anything else is copied raw. The two-digit year is prefixed with 19 for digits '0'-'4' and 20 for '5'-'9', producing "yyyy-mm-dd hh:mm:ss zone".

<a id="u-70071e86e140"></a>
### `ASN1tostr`

`UNITTEST CURLcode ASN1tostr(struct dynbuf *store, struct Curl_asn1Element *elem)` · [lib/vtls/x509asn1.c:L627-L676][f1]

Dispatches an ASN.1 element to the appropriate string converter appended to store.

Constructed elements return CURLE_BAD_FUNCTION_ARGUMENT immediately. By tag: BOOLEAN to bool2str, INTEGER/ENUMERATED to int2str, BIT_STRING to bit2str, OCTET_STRING to octet2str, NULL appends an empty string, OBJECT_IDENTIFIER to OID2str, UTC_TIME/GENERALIZED_TIME to the time converters, and the string types to utf8asn1str. Tags not in the switch return the initial CURLE_BAD_FUNCTION_ARGUMENT; converter results propagate unchanged.

calls: [bool2str](r3-x509-parsing.md#u-ca524013f61f), [int2str](r3-x509-parsing.md#u-d9c9cdb10c8c), [bit2str](r3-x509-parsing.md#u-029f83242e2c), [octet2str](r3-x509-parsing.md#u-40a4922774ea), [OID2str](r3-x509-parsing.md#u-258433f93640), [UTime2str](r3-x509-parsing.md#u-890647ed5247), [GTime2str](r3-x509-parsing.md#u-1a3853b7af9e), [utf8asn1str](r3-x509-parsing.md#u-2b1ea67ede0a)

<a id="u-b0ac5e057225"></a>
### `encodeDN`

`static CURLcode encodeDN(struct dynbuf *store, struct Curl_asn1Element *dn)` · [lib/vtls/x509asn1.c:L683-L766][f1]

Renders an ASN.1 distinguished name into store as name=value pairs.

It walks RDNs, then AttributeTypeAndValue entries, parsing the OID and value with getASN1Element; any parse failure or ASN1tostr error sets CURLE_BAD_FUNCTION_ARGUMENT or the converter's error and jumps to the cleanup that frees the temporary dynbuf and returns. If the OID string is missing or the name scan fails, it errors out. The delimiter before each pair after the first is ", " when the name is at most 2 uppercase characters, otherwise "/". Each pair appends the name, '=', then the value converted by ASN1tostr; dynbuf errors abort and propagate.

calls: [function::getASN1Element][f1], [function::ASN1tostr][f1]

**Uncertainties.**

- Whether a NULL pointer from curlx_dyn_uptr after a successful conversion can occur is guarded here but not provable from this file.

<a id="u-ab77587aa6e6"></a>
### `Curl_parseX509`

`int Curl_parseX509(struct Curl_X509certificate *cert, const uint8_t *beg, const uint8…` · [lib/vtls/x509asn1.c:L776-L892][f1]

ASN.1-parses an X.509 certificate into the fields of a Curl_X509certificate, assuming syntax was pre-checked by the SSL backend (RFC 5280 layout).

It zeroes the struct, parses the outer sequence, then tbsCertificate, outer signatureAlgorithm, and signatureValue; any getASN1Element failure returns -1. Inside TBSCertificate it reads the optional version element (tag 0; otherwise version defaults to a static 0 byte), then serialNumber, signature algorithm, issuer, validity (notBefore/notAfter must exactly fill the validity element or it returns -1), subject, subjectPublicKeyInfo split into algorithm and key, and finally optional tags 1 (issuerUniqueID), 2 (subjectUniqueID), and 3 (extensions), defaulting them to empty elements. Returns 0 on success.

calls: [function::getASN1Element][f1]

**Uncertainties.**

- The signatureAlgorithm field of the certificate is overwritten by the TBSCertificate signature algorithm; both parses target cert->signatureAlgorithm.

<a id="u-fb7ff8b12c88"></a>
### `dumpAlgo`

`static CURLcode dumpAlgo(struct dynbuf *store, struct Curl_asn1Element *param, const …` · [lib/vtls/x509asn1.c:L898-L918][f1]

Extracts an algorithm identifier's OID and parameters.

It parses the leading OID element (failure is CURLE_BAD_FUNCTION_ARGUMENT), then, if content remains, parses the following element into *param as the algorithm parameters; otherwise param is set to an empty tag-0 element covering the tail. Returns OID2str's rendering of the OID appended to store, propagating its errors.

calls: [function::getASN1Element][f1], [function::OID2str][f1]

<a id="u-e6c54b5fa05e"></a>
### `ssl_push_certinfo`

`static CURLcode ssl_push_certinfo(struct Curl_easy *data, int certnum, const char *la…` · [lib/vtls/x509asn1.c:L924-L932][f1]

Convenience wrapper that pushes a zero-terminated certificate info value by measuring it with strlen and calling Curl_ssl_push_certinfo_len; that function's result propagates.

calls: [Curl_ssl_push_certinfo_len](../../catalog.json)

<a id="u-b8232c9f453a"></a>
### `ssl_push_certinfo_dyn`

`static CURLcode ssl_push_certinfo_dyn(struct Curl_easy *data, int certnum, const char…` · [lib/vtls/x509asn1.c:L940-L955][f1]

Pushes a dynbuf-held certificate info value via Curl_ssl_push_certinfo_len using the dynbuf's length and pointer.

Additionally, when certnum is 0 and the push succeeded, it logs the label and value with infof. Returns the push result; a failed push skips the logging.

calls: [Curl_ssl_push_certinfo_len](../../catalog.json)

**Uncertainties.**

- Whether curlx_dyn_ptr may be NULL for an empty dynbuf, and how the callee handles it, is not visible here.

<a id="u-bbe0371acf5d"></a>
### `do_pubkey_field`

`static CURLcode do_pubkey_field(struct Curl_easy *data, int certnum, const char *labe…` · [lib/vtls/x509asn1.c:L957-L975][f1]

Converts one public-key element to a string with ASN1tostr into a dynbuf limited to CURL_X509_STR_MAX, then, only when data->set.ssl.certinfo is set, pushes it via ssl_push_certinfo_dyn.

The dynbuf is freed only after a successful conversion (a conversion error leaves it allocated); both conversion and push errors propagate.

calls: [function::ASN1tostr][f1], [function::ssl_push_certinfo_dyn][f1]

**Uncertainties.**

- The dynbuf is not freed on the ASN1tostr error path, a potential leak visible in the source.

<a id="u-db8998e78ea8"></a>
### `do_pubkey`

`static int do_pubkey(struct Curl_easy *data, int certnum, const char *algo, struct Cu…` · [lib/vtls/x509asn1.c:L978-L1082][f1]

Generates all certificate info records for one public key; returns 0 on success, 1 on error.

For "ecPublicKey", the whole key bit string is not ASN.1-parsed: fewer than 2 bytes is an error; the bit length (dlen-2)*4 is logged for certnum 0, pushed as "ECC Public Key" when certinfo is enabled, and the raw key is pushed via do_pubkey_field as "ecPublicKey". Otherwise the key element is parsed from pubkey->beg + 1 (failure is an error). For "rsaEncryption", the modulus is parsed, its bit length computed from leading zero bytes and the first set bit, values over 32 bits have leading zero bytes stripped, length and coefficients rsa(n)/rsa(e) are pushed. For "dsa", p/q/g/pub_key are pushed when the parameters parse; for "dhpublicnumber", dh(p)/dh(g)/dh(pub_key). Unhandled algorithms return 0 without pushing fields.

calls: [function::do_pubkey_field][f1], [function::getASN1Element][f1], [function::ssl_push_certinfo][f1]

**Uncertainties.**

- A do_pubkey_field error returns 1, which Curl_extract_certinfo maps to CURLE_OUT_OF_MEMORY regardless of the actual cause.

<a id="u-1b13a2b31311"></a>
### `DNtostr`

`static CURLcode DNtostr(struct dynbuf *store, struct Curl_asn1Element *dn)` · [lib/vtls/x509asn1.c:L1088-L1091][f1]

Thin wrapper that converts an ASN.1 distinguished name to a printable string by delegating to encodeDN and propagating its result.

calls: [function::encodeDN][f1]

<a id="u-eb28588f2663"></a>
### `Curl_extract_certinfo`

`CURLcode Curl_extract_certinfo(struct Curl_easy *data, int certnum, const uint8_t *be…` · [lib/vtls/x509asn1.c:L1093-L1274][f1]

Extracts certificate information from a DER certificate and pushes named records for curl_easy_getinfo and verbose output.

If certinfo is disabled, only certnum 0 proceeds (others return CURLE_OK immediately). Curl_parseX509 failure returns CURLE_PEER_FAILED_VERIFICATION. It then converts and pushes, in order: Subject, Issuer, Version (hex of the version integer), Serial Number, Signature Algorithm (via dumpAlgo), Start Date, Expire Date, Public Key Algorithm (via dumpAlgo), then do_pubkey for the key fields (a nonzero return becomes CURLE_OUT_OF_MEMORY), Signature, and finally a PEM "Cert" built from base64-encoding the whole certificate wrapped at 64 characters between BEGIN/END CERTIFICATE lines. Each field is skipped when certinfo is off but conversion still runs; any error jumps to cleanup, which logs "Failed extracting certificate chain" via failf, frees the dynbuf, and returns the error.

calls: [function::Curl_parseX509][f1], [function::DNtostr][f1], [function::ASN1tostr][f1], [function::dumpAlgo][f1], [function::do_pubkey][f1], [function::ssl_push_certinfo_dyn][f1], [curlx_base64_encode](../../catalog.json)

**Uncertainties.**

- CURLE_OUT_OF_MEMORY is assumed by the comment to be the most likely do_pubkey error; the actual cause is not discriminated.
- base64 memory is freed with curlx_free before building the PEM body; behavior if result fails after encode is to skip PEM build and return the error.

<a id="u-d9c9cdb10c8c"></a>
### `int2str`

`static CURLcode int2str(struct dynbuf *store, const uint8_t *beg, const uint8_t *end)` · [lib/vtls/x509asn1.c:L281-L310][f1]

Formats an ASN.1 INTEGER.

Empty content is CURLE_BAD_FUNCTION_ARGUMENT. Content longer than 4 bytes is rendered as colon-separated hex via octet2str. Otherwise the value is assembled into 32 bits with sign extension when the leading bit is set; values strictly between -10000 and 10000 print as decimals ("%d"), larger magnitudes print as unsigned hex "0x%x". Negative 4-byte values therefore print as unsigned hex, and dynbuf errors propagate.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/x509asn1.c
