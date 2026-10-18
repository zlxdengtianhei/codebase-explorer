# Apple SecTrust verification

**Capability.** TLS peer certificate verification via Apple's Security/SecTrust framework, enabled only under USE_APPLE_SECTRUST.

Consult when changing macOS/iOS certificate trust behavior; the header declares the API gated by the same build condition.

Parent: [TLS infrastructure](r12-tls-infrastructure.md)

## Units (2)

<a id="u-443724e5a00b"></a>
### `apple.c module code (L1–L316)`

`module_region` · [lib/vtls/apple.c:L1-L316][f1]

Implements TLS peer certificate verification using Apple's Security/SecTrust framework, gated behind USE_APPLE_SECTRUST.

The single function Curl_vtls_apple_verify builds a SecTrust object from caller-supplied DER certificates plus SSL/revocation policies, evaluates it, and maps the outcome to a CURLcode; on every exit it releases all Core Foundation objects allocated on the path. Compilation behavior changes with SDK availability macros: SUPPORTS_SecTrustEvaluateWithError enables the modern evaluation path, REQUIRES_... suppresses the legacy SecTrustEvaluate fallback, SUPPORTS_SecOCSP and HAVE_BUILTIN_AVAILABLE gate OCSP/revocation-policy support, each selected per-platform via __*_OS_X_VERSION_*_ALLOWED macros.

**Notes.**

- condition: If conn_config->verifyhost is set, an SSL policy is created with the SNI hostname (falling back to peer->origin->hostname); otherwise host_str stays NULL and the SSL policy has no hostname.
- failure: All CF allocations (host string, policy arrays, cert data, SecCertificate) map allocation failure to CURLE_OUT_OF_MEMORY via goto out; der_cb errors propagate unchanged.
- condition: When HAVE_BUILTIN_AVAILABLE and SUPPORTS_SecOCSP hold and no_revoke is unset, a revocation policy using kSecRevocationUseAnyAvailableMethod is appended at runtime only if the OS version check passes; revoke_best_effort handling requiring positive response is compiled out via #if 0.
- failure: SecTrustCreateWithCertificates failure or a non-empty OCSP buffer on a platform without OCSP support yields CURLE_PEER_FAILED_VERIFICATION or CURLE_NOT_BUILT_IN respectively; SecTrustSetOCSPResponse failure maps to CURLE_PEER_FAILED_VERIFICATION.
- condition: Evaluation: with SecTrustEvaluateWithError available, success is CURLE_OK and failure CURLE_PEER_FAILED_VERIFICATION, logging the CFError code and description when verbose; the legacy path accepts only kSecTrustResultUnspecified or kSecTrustResultProceed as success, any OSStatus error or other trust result is CURLE_PEER_FAILED_VERIFICATION.

uses: [module_residual::::104-244][f2]

**Uncertainties.**

- The parser reported a syntax error near line 1, so exact macro-evaluation coverage across the conditional blocks cannot be fully confirmed from this excerpt.
- VERBOSE/infof output behavior depends on macros defined outside this file.

<a id="u-fb619193f4b9"></a>
### `apple.h module code (L1–L54)`

`module_region` · [lib/vtls/apple.h:L1-L54][f3]

Declares the Apple Security-framework TLS verification API used only when USE_APPLE_SECTRUST is defined.

It defines the function-pointer type Curl_vtls_get_cert_der, which retrieves the DER encoding of the i-th certificate from the peer handshake, and declares Curl_vtls_apple_verify, which asks Apple's framework to verify the peer chain built via that callback plus optional OCSP data; CURLE_OK indicates a verified chain. The header contains only declarations, no implementation.

uses: [apple.h module code (L1–L54)](r12-apple-sectrust.md#u-fb619193f4b9)

**Uncertainties.**

- Implementation behavior of Curl_vtls_apple_verify is not in this file and cannot be established here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/apple.c
[f2]: ../../../../../../eval/curl-2c04412/lib/vtls/vtls.h
[f3]: ../../../../../../eval/curl-2c04412/lib/vtls/apple.h
