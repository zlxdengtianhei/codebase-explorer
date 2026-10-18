# FTP Wildcard Transfer

**Capability.** Owns directory-listing wildcard matching: splitting the URL into prefix and pattern (init_wc_data) and the yielding wildcard state machine (wc_statemach) that iterates matches by re-entering the path parsing.

Read this only for CURLOPT_WILDCARDMATCH-style chunked downloads. wc_statemach loops until a state yields and calls back into ftp_parse_url_path for each matched entry.

**Depends on.**

- [FTP Transfer Lifecycle](r1-ftp-lifecycle.md) · model-inferred · 0 edge(s)
- [FTP Path and Data-Channel Helpers](r1-ftp-path-data-helpers.md) · graph-confirmed · 4 edge(s)

Parent: [FTP Protocol Implementation](r1-ftp-protocol.md)

## Units (2)

<a id="u-c9819aa7692a"></a>
### `init_wc_data`

`static CURLcode init_wc_data(struct Curl_easy *data, struct ftp_conn *ftpc, struct FT…` · [lib/ftp.c:L3958-L4041][f1]

Prepares wildcard matching by splitting the URL into directory prefix and trailing pattern.

A path ending in '/' or an empty path means listing-only: the state becomes CURLWC_CLEAN and ftp_parse_url_path runs directly. Otherwise the last slash delimits the pattern (or a slash-less path is all pattern, emptying the path); allocation failures propagate. An ftp_wc struct with a list parser is allocated, attached to wildcard with wc_data_dtor as destructor; NOCWD is silently forced to MULTICWD since wildcard cannot support it. The path is re-parsed, and wildcard->path stores the prefix; failure unwinds all wildcard allocations. wc_data_dtor (folded) frees the parser data and the ftp_wc struct.

**Notes.**

- side_effect: ftp->path is truncated in place to the directory prefix; the pattern is copied to wildcard->pattern.

<a id="u-29e92d5ceb77"></a>
### `wc_statemach`

`static CURLcode wc_statemach(struct Curl_easy *data, struct ftp_conn *ftpc, struct FT…` · [lib/ftp.c:L4043-L4175][f1]

Wildcard transfer state machine, looping per invocation until a state yields.

CURLWC_INIT initializes wildcard data (listing-only returns immediately; otherwise MATCHING or ERROR). CURLWC_MATCHING inspects parsed LIST results: a parse error goes to CLEAN; an empty filelist returns CURLE_REMOTE_FILE_NOT_FOUND; otherwise DOWNLOADING. CURLWC_DOWNLOADING takes the first filelist entry, URL-escapes its name onto wildcard->path as the new ftp->path, then: a user chunk_bgn SKIP moves to SKIP, FAIL returns CURLE_CHUNK_FAILED; non-regular files are skipped; a known size is stored as ftpc->known_filesize; ftp_parse_url_path re-parses the new path (errors propagate) and the consumed entry is removed; an exhausted list moves to CLEAN (no further transfer), otherwise returns to let DO proceed. CURLWC_SKIP runs chunk_end, removes the entry, and continues to CLEAN or DOWNLOADING. CURLWC_CLEAN surfaces any parser error and moves to DONE or ERROR. DONE/ERROR/CLEAR invoke the destructor and clear ftpwc.

**Uncertainties.**

- The behavior of chunk_bgn returning values other than the handled constants is not specified here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/ftp.c
