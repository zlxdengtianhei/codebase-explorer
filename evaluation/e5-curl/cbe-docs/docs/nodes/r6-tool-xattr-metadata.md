# Extended Attribute Metadata

**Capability.** Stores request metadata next to downloaded files via POSIX xattrs or an NTFS Zone.Identifier stream, including credential-stripped URL preparation.

Use to understand the platform-specific metadata side-channels of downloaded files. fwrite_xattr is the entry point; the helper/mapping group and win32_file_stream provide per-platform write paths.

**Depends on.**

- [CURLU Handle Management and Setters](r6-url-handle-api.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [FTP Wildcard LIST Parsing](r6-ftp-list-parsing.md) · graph-confirmed · 5 edge(s)
- [Share API](r6-share-api.md) · graph-confirmed · 1 edge(s)
- [Tool Variable Store and Expansion](r6-tool-variable-store.md) · graph-confirmed · 9 edge(s)
- [Tool configuration](r15-cli-config.md) · graph-only · 94 edge(s)
- [Digest core \(vauth/digest\)](r9-digest-core.md) · graph-only · 31 edge(s)

Parent: [Command-Line Tool Support](r6-tool-side.md)

## Units (4)

<a id="u-3b151a738586"></a>
### `fwrite_xattr`

`int fwrite_xattr(CURL *curl, const char *url, int fd, const char *filename)` · [src/tool_xattr.c:L134-L188][f1]

Stores request metadata alongside a downloaded file, using extended attributes on POSIX-like systems or an NTFS alternate data stream on Windows.

Windows branch: converts filename to an absolute path with _fullpath (returning 1 on failure) to avoid 'X:stream' being read as drive-letter syntax, builds "<abs>:Zone.Identifier" with curl_maprintf (1 on allocation failure), opens it with curlx_fopen text mode (1 on failure), optionally routes win32_file_stream output to stdout under DEBUGBUILD with CURL_FAKE_XATTR, otherwise writes the real stream and closes it. Non-Windows branch: writes user.creator=curl, then loops the mappings table while no error, fetching each CURLINFO value and writing it via xattr(); when a getinfo fails or yields NULL that attribute is skipped. If still error-free it writes user.xdg.origin.url from stripcredentials(url), returning 1 if stripping fails. Returns the accumulated error flag.

**Notes.**

- failure: All failure paths return nonzero (1); on Windows the stream FILE is closed before returning regardless of write success.

calls: [stripcredentials](r6-tool-xattr-metadata.md#u-a0a355623cb0), [tool_xattr-c-xattr-helper-and-mapping](r6-tool-xattr-metadata.md#u-91dcde99c83d), [win32_file_stream](r6-tool-xattr-metadata.md#u-eb751dcc512e), [lib-mprintf-c-dynbuf-alloc-family](r9-mprintf-formatter-families.md#u-ce09737881fa)

<a id="u-a0a355623cb0"></a>
### `stripcredentials`

`UNITTEST char *stripcredentials(const char *url)` · [src/tool_xattr.c:L32-L62][f1]

Returns a copy of the given URL with user and password parts removed, allocated by the URL API, or NULL on failure.

It parses the URL with curl_url() plus curl_url_set(CURLUPART_URL, ..., CURLU_GUESS_SCHEME), clears CURLUPART_USER and CURLUPART_PASSWORD, and fetches the result with curl_url_get(CURLUPART_URL). Any failing step jumps to an error label that cleans up the CURLU handle and returns NULL; success also cleans up the handle and returns the new string, which the caller must free.

**Uncertainties.**

- The goto error label is reached after curl_url() failure too, calling curl_url_cleanup(NULL); whether that is safe depends on the URL API's null tolerance, not shown here.

<a id="u-eb751dcc512e"></a>
### `win32_file_stream`

`static int win32_file_stream(CURL *curl, FILE *fs, const char *url)` · [src/tool_xattr.c:L107-L128][f1]

Windows variant that writes a Zone.Identifier stream body into an already-open FILE*.

It strips credentials from the URL and reads CURLINFO_REFERER. If the stripped URL was produced and the getinfo succeeded, it writes "[ZoneTransfer]\n", optionally a "ReferrerUrl=<value>\n" block when a referrer exists, then "HostUrl=<nurl>\n". Each fputs failure (EOF) is OR-ed into the error flag, which starts at 1 and is cleared to 0 only on entry to the write sequence, so a failed URL strip or getinfo yields 1; returns 0 only if every fputs succeeded. Frees the stripped URL with curl_free.

<a id="u-91dcde99c83d"></a>
### `tool_xattr-c-xattr-helper-and-mapping`

`struct xattr_mapping` · [src/tool_xattr.c:L66-L69][f1]

Platform-specific helpers for writing extended attributes.

On non-Windows, the static xattr() writes one attribute to a file descriptor: in DEBUGBUILD with CURL_FAKE_XATTR set it just prints attr => value and returns 0; otherwise it calls whichever of fsetxattr (6- or 5-argument forms) or the FreeBSD/MidnightBSD extattr_set_fd variant is compiled in, normalizing extattr's length return to 0/-1, and returns 0 without touching the fd when value is NULL. The xattr_mapping table pairs attribute names with CURLINFO getters; it currently maps user.xdg.referrer.url to CURLINFO_REFERER and user.mime_type to CURLINFO_CONTENT_TYPE, terminated by a NULL attr entry.

**Uncertainties.**

- If none of HAVE_FSETXATTR_6, HAVE_FSETXATTR_5, or the BSD macros is defined, xattr() returns 0 without writing anything; whether the build system guarantees one is configured elsewhere is not visible.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_xattr.c
