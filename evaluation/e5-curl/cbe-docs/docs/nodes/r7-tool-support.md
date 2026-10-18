# Tool environment and libcurl info

**Capability.** Locating config-style files in home directories and caching libcurl runtime capability info (version info, canonical protocol tokens).

findfile backs config-file lookup; get_libcurl_info/proto_token expose what the linked libcurl supports and are queried by retry logic. Call proto_token to compare protocol names against the library's own strings.

**Depended on by.**

- [Transfer execution and retry](r7-tool-execution.md) · graph-confirmed · 3 edge(s)

Parent: [Command-line tool](r7-tool-cli.md)

## Units (4)

<a id="u-6b92e249f0be"></a>
### `findfile`

`char *findfile(const char *fname, int dotscore)` · [src/tool_findfile.c:L98-L150][f1]

Locates a config-style file by searching home directories from environment variables in conf_list order, returning the first existing path (caller frees with curl_free) or NULL.

For each set, non-empty env var, the optional append string is appended (allocation failure returns NULL immediately). Entries marked withoutdot apply only when dotscore is set: they drop the leading dot of fname and disable further dotscoring for that check; other entries leave the name intact and keep dotscore. Each candidate home is tested with checkhome (passing dotscore-1 so level 2/1 becomes the underscore/dot probing). After the list, on systems with getpwuid/geteuid, the effective user's passwd home is tried as a last resort without dotscoring. Empty fname returns NULL immediately.

**Notes.**

- field: conf_list order matters: CURL_HOME, XDG_CONFIG_HOME, HOME, then Windows-only USERPROFILE/APPDATA entries, then CURL_HOME//.config and HOME//.config fallbacks for .curlrc.

calls: [checkhome](r7-tool-support.md#u-2ac903c35e42), [curl_getenv](r8-netrc-credentials.md#u-88fda3b63c5f)

**Uncertainties.**

- getpwuid data is not thread-safe per POSIX; no locking is visible here.
- On Windows, findfile itself has no executable-directory logic in this file; any such behavior lives elsewhere despite the header comment in open_config_file.

<a id="u-2ac903c35e42"></a>
### `checkhome`

`static char *checkhome(const char *home, const char *fname, bool dotscore)` · [src/tool_findfile.c:L63-L85][f1]

Tests whether a candidate file exists under a home directory.

With dotscore it first tries 'home/.<rest-of-name>' then 'home/_<rest-of-name>'; without dotscore it tries 'home/<name>' directly. Each candidate is probed with an O_RDONLY open; the first successful open yields a strdup'd path (fd closed) that the caller must free with curl_free. Allocation failures and failed opens simply move to the next candidate; returns NULL when nothing opens.

uses: [findfile](r7-tool-support.md#u-6b92e249f0be)

**Uncertainties.**

- dotscore semantics: callers pass dotscore ? dotscore - 1 : 0, so only values 1 and 2 (CURLRC_DOTSCORE) produce the dot/underscore probes; a plain nonzero other than 1/2 would behave as no-probe at the last iteration.

<a id="u-8b92be4685d6"></a>
### `get_libcurl_info`

`CURLcode get_libcurl_info(void)` · [src/tool_libinfo.c:L134-L186][f2]

Populates the module's libcurl runtime globals from curl_version_info(CURLVERSION_NOW); a NULL result returns CURLE_FAILED_INIT.

If protocols exist, built_in_protos points at the library array and each entry is matched case-insensitively against possibly_built_in, setting the corresponding proto_* token pointers; proto_count becomes the number of protocols enumerated. If the library supplies feature_names (age >= CURLVERSION_ELEVENTH), feature_names aliases it; otherwise fnames is built from maybe_feature entries whose feature_bitmask is set in curlinfo->features, NUL-terminated. Finally each feature name is matched against maybe_feature, setting matching feature_* booleans to TRUE (entries with NULL presentp only match), and feature_count counts all reported names. Always returns CURLE_OK after the initial check.

**Notes.**

- field: feature_count counts every reported feature name, including ones with no matching boolean token.

calls: [curl_version_info](r3-version-info.md#u-a10e1e8ea546), [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

**Uncertainties.**

- The feature-name loop does not stop on error, and there is no path returning an error after the initial NULL check other than the documented CURLE_OK.

<a id="u-cf1321e4e28c"></a>
### `proto_token`

`const char *proto_token(const char *proto)` · [src/tool_libinfo.c:L195-L205][f2]

Returns the library's canonical string pointer for a protocol name: a NULL input returns NULL; otherwise the built_in_protos array is scanned case-insensitively and the matching entry's pointer is returned.

If not found the scan ends at the terminating NULL, which is returned; this stable per-protocol pointer enables pointer-equality comparison and outlives the call.

calls: [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_findfile.c
[f2]: ../../../../../../eval/curl-2c04412/src/tool_libinfo.c
