# FTP Wildcard LIST Parsing

**Capability.** Feed-style state machine converting Unix and Windows NT LIST reply bytes into fileinfo records: OS detection, per-field Unix parsers, permission decoding, symlink handling, and record allocation/cleanup.

Trace FTP directory listing bytes through Curl_ftp_parselist, which dispatches to parse_unix or parse_winnt and finalizes entries via ftp_pl_insert_finfo. The fileinfo records this subtree allocates and frees are its data model. Lifecycle helpers cover setup, teardown and error query.

**Depends on.**

- [Extended Attribute Metadata](r6-tool-xattr-metadata.md) · graph-confirmed · 5 edge(s)
- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) · graph-only · 25 edge(s)

Parent: [curl Codebase](r6-curl-codebase.md)

## Units (18)

<a id="u-b61fe04fea7b"></a>
### `Curl_ftp_listmode`

`bool Curl_ftp_listmode(struct Curl_easy *data)` · [lib/ftplistparser.c:L1019-L1026][f1]

Reports whether the transfer is currently in FTP wildcard LIST-matching mode.

**Notes.**

- condition: Returns TRUE only when data->state.wildcardmatch is set, the wildcard exists, and its state is CURLWC_MATCHING; otherwise FALSE.

<a id="u-4648f428f9ad"></a>
### `Curl_ftp_parselist`

`size_t Curl_ftp_parselist(char *buffer, size_t size, size_t nmemb, void *connptr)` · [lib/ftplistparser.c:L1028-L1104][f1]

Feed-style state machine that OS-detects, parses LIST reply bytes, and signals failures through a return-size trick.

**Notes.**

- condition: When os_type is still UNKNOWN, a first byte that is a digit selects OS_TYPE_WIN_NT, otherwise OS_TYPE_UNIX; the detection happens only once and only when bufflen > 0.
- failure: A stored parser->error from a previous call short-circuits immediately to the fail path (returning bufflen) so the FTP state machine can retrieve the deferred error via Curl_ftp_parselist_geterror.
- failure: Allocation or dynbuf-append failure sets CURLE_OUT_OF_MEMORY; a sub-parser error is stored in parser->error; both paths free the pending fileinfo. The returned size normally equals bufflen; the UNKNOWN-OS default branch returns bufflen + 1 to signal failure to the caller.
- side_effect: Each character is appended to the current fileinfo dynbuf (capacity MAX_FTPLIST_BUFFER initialized per record) before dispatch, and item_offset/item_length are reset per new record.

calls: [Curl_fileinfo_alloc](r6-ftp-list-parsing.md#u-358345696e90), [Curl_fileinfo_cleanup](r6-ftp-list-parsing.md#u-5a16fa3aa02a), [parse_unix](r6-ftp-list-parsing.md#u-bb92ff05a457), [parse_winnt](r6-ftp-list-parsing.md#u-ac247f720d62)

<a id="u-f7e9b7407bd4"></a>
### `ftp_pl_get_permission`

`static unsigned int ftp_pl_get_permission(const char *str)` · [lib/ftplistparser.c:L230-L293][f1]

Converts a 9-character rwx-style permission string into a POSIX permission bitmask, flagging malformed characters.

**Notes.**

- failure: Any position character other than the expected rwx/-/s/S/t/T letters sets FTP_LP_MALFORMATED_PERM (0x01000000) in the result; the caller must test that bit to reject the line.
- field: Bits 8..0 map to user/group/other rwx; setgid/setuid/sticky contribute bits 11, 10, and 9 respectively via s/S and t/T at the x positions.

<a id="u-44d8c458ab78"></a>
### `ftp_pl_insert_finfo`

`static CURLcode ftp_pl_insert_finfo(struct Curl_easy *data, struct fileinfo *infop)` · [lib/ftplistparser.c:L295-L354][f1]

Finalizes one parsed directory entry, wires string pointers into the line buffer, pattern-filters it, and appends or discards it.

**Notes.**

- condition: Entries whose filename contains '/' are never added (a real file name cannot contain a slash).
- condition: The entry is added only when the fnmatch callback (data->set.fnmatch or the default Curl_fnmatch) returns 0 for wc->pattern vs the filename; otherwise it is freed.
- condition: Symlinks whose target contains " -> " are discarded as malformed double-link lines.
- contract: Optional string fields (group, perm, user, symlink target) become NULL when their recorded offset is 0; the target is set only for CURLFILETYPE_SYMLINK entries.
- side_effect: Sets ftpwc->parser->file_data to NULL so the next character starts a fresh fileinfo, and always returns CURLE_OK from this function.

calls: [Curl_fileinfo_cleanup](r6-ftp-list-parsing.md#u-5a16fa3aa02a), [Curl_llist_append](r9-linked-list.md#u-5e8651140cc1)

<a id="u-bb92ff05a457"></a>
### `parse_unix`

`static CURLcode parse_unix(struct Curl_easy *data, struct ftp_parselist_data *parser,…` · [lib/ftplistparser.c:L834-L884][f1]

Top-level per-character dispatcher for Unix-style LIST lines, sequencing field parsers by main state.

**Notes.**

- condition: After parse_unix_totalsize succeeds, the parser falls through into PL_UNIX_FILETYPE only when the main state advanced past TOTALSIZE; otherwise it returns for the next character.
- failure: The first sub-parser error is returned immediately and stops this character's processing; the entry remains pending until Curl_ftp_parselist sees the error.

calls: [parse_unix_totalsize](r6-ftp-list-parsing.md#u-24df1381b8ba), [unix_filetype](r6-ftp-list-parsing.md#u-491d39f26385), [parse_unix_permission](r6-ftp-list-parsing.md#u-bd224eaac1e4), [parse_unix_hlinks](r6-ftp-list-parsing.md#u-ad77765071ec), [ftplistparser-parse-user-group](r6-ftp-list-parsing.md#u-e591ba3bfb5e), [parse_unix_size](r6-ftp-list-parsing.md#u-2903b1bcf6ce), [parse_unix_time](r6-ftp-list-parsing.md#u-6d9814e4a861), [parse_unix_filename](r6-ftp-list-parsing.md#u-9475e2ec59d5), [parse_unix_symlink](r6-ftp-list-parsing.md#u-7d453aae4e81)

<a id="u-9475e2ec59d5"></a>
### `parse_unix_filename`

`static CURLcode parse_unix_filename(struct Curl_easy *data, struct ftp_parselist_data…` · [lib/ftplistparser.c:L687-L728][f1]

Parses the trailing filename of a non-symlink Unix entry and completes the record.

**Notes.**

- condition: A '\r' switches to a WINDOWSEOL substate that requires exactly '\n' next; any other character there is CURLE_FTP_BAD_FILE_LIST.
- side_effect: On '\n' the filename is NUL-terminated, offsets.filename recorded, and the main state rewinds to PL_UNIX_FILETYPE for the next line; the insert result is propagated.

calls: [ftp_pl_insert_finfo](r6-ftp-list-parsing.md#u-44d8c458ab78)

<a id="u-ad77765071ec"></a>
### `parse_unix_hlinks`

`static CURLcode parse_unix_hlinks(struct ftp_parselist_data *parser, struct fileinfo …` · [lib/ftplistparser.c:L468-L509][f1]

Parses the hard-link count field of a Unix listing entry.

**Notes.**

- condition: In PRESPACE, the first non-blank must be a digit and the buffer must be non-empty, otherwise CURLE_FTP_BAD_FILE_LIST.
- condition: If curlx_str_number fails, no failure is propagated: the count is simply left unknown and parsing continues.
- side_effect: On the terminating blank it sets CURLFINFOFLAG_KNOWN_HLINKCOUNT and info.hardlinks when conversion succeeded, then moves to PL_UNIX_USER.

calls: [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

<a id="u-bd224eaac1e4"></a>
### `parse_unix_permission`

`static CURLcode parse_unix_permission(struct ftp_parselist_data *parser, struct filei…` · [lib/ftplistparser.c:L438-L466][f1]

Accumulates the 9-character permission field of a Unix entry and decodes it on the terminating blank.

**Notes.**

- failure: During the first 9 characters any byte outside "rwx-tTsS" is rejected; the 10th character must be a blank.
- failure: If the decoded mask carries FTP_LP_MALFORMATED_PERM the line is rejected with CURLE_FTP_BAD_FILE_LIST.
- side_effect: On success sets CURLFINFOFLAG_KNOWN_PERM, stores info.perm, records offsets.perm, and advances the main state to PL_UNIX_HLINKS.

calls: [ftp_pl_get_permission](r6-ftp-list-parsing.md#u-f7e9b7407bd4)

<a id="u-2903b1bcf6ce"></a>
### `parse_unix_size`

`static CURLcode parse_unix_size(struct ftp_parselist_data *parser, struct fileinfo *i…` · [lib/ftplistparser.c:L569-L610][f1]

Parses the file size field of a Unix listing entry.

**Notes.**

- condition: In PRESPACE a non-blank that is not a digit (or an empty buffer) is rejected; in NUMBER any non-digit that is not a blank is rejected.
- condition: If curlx_str_numblanks succeeds but trailing characters remain after the number (p[0] != '\0'), or the value equals CURL_OFF_T_MAX, the size flag is not set and parsing still continues to the time field.
- side_effect: On success sets CURLFINFOFLAG_KNOWN_SIZE and info.size, then advances to PL_UNIX_TIME.

calls: [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

<a id="u-7d453aae4e81"></a>
### `parse_unix_symlink`

`static CURLcode parse_unix_symlink(struct Curl_easy *data, struct ftp_parselist_data …` · [lib/ftplistparser.c:L730-L832][f1]

Parses 'name -> target' symlink entries, splitting the line at the arrow and recording the target.

**Notes.**

- failure: Any '\r' or '\n' encountered while scanning the name or the ' -> ' sequence is rejected with CURLE_FTP_BAD_FILE_LIST; PRETARGET4 requires a non-EOL character with a non-empty buffer.
- condition: In PRETARGET1/2/3 a character that does not continue '-' '>' ' ' restarts name collection from that point.
- side_effect: When the arrow completes, the byte four positions back is NUL'd to terminate the filename and offsets.filename is set; on newline the target is terminated, offsets.symlink_target recorded, the entry inserted, and the main state rewinds to PL_UNIX_FILETYPE.

calls: [ftp_pl_insert_finfo](r6-ftp-list-parsing.md#u-44d8c458ab78)

<a id="u-6d9814e4a861"></a>
### `parse_unix_time`

`static CURLcode parse_unix_time(struct ftp_parselist_data *parser, struct fileinfo *i…` · [lib/ftplistparser.c:L612-L685][f1]

Parses the three blank-separated time/date parts of a Unix listing entry.

**Notes.**

- condition: Each part begins with an alphanumeric character after blanks; within a part, only alphanumerics, '.', and (in part 3) ':' are accepted.
- condition: After the third part terminates on a blank, the next field depends on the entry type: symlinks go to PL_UNIX_SYMLINK, everything else to PL_UNIX_FILENAME.
- side_effect: On completion the time text is NUL-terminated in place and offsets.time is recorded.

<a id="u-24df1381b8ba"></a>
### `parse_unix_totalsize`

`static CURLcode parse_unix_totalsize(struct ftp_parselist_data *parser, struct filein…` · [lib/ftplistparser.c:L391-L436][f1]

Consumes the optional 'total N' header line of a Unix LIST reply before per-entry parsing begins.

**Notes.**

- condition: In PL_UNIX_TOTALSIZE_INIT, the first character must be 't' to enter the reading state; any other character switches the main state to PL_UNIX_FILETYPE and falls through so the same character starts entry parsing.
- failure: On newline, the accumulated text must match "total " followed only by blanks and digits ending at the string terminator; anything else, or trailing junk, returns CURLE_FTP_BAD_FILE_LIST.
- side_effect: A trailing '\r' is stripped from the buffer via curlx_dyn_setlen; on success the buffer is reset with curlx_dyn_reset.

calls: [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

<a id="u-ac247f720d62"></a>
### `parse_winnt`

`static CURLcode parse_winnt(struct Curl_easy *data, struct ftp_parselist_data *parser…` · [lib/ftplistparser.c:L886-L1016][f1]

Per-character parser for Windows NT-style LIST lines: date, time, dir-or-size, then filename.

**Notes.**

- failure: DATE accepts digits and '-' for the first 8 characters and requires a blank as the 9th; the TIME content phase allows only A/P/M, digits, and ':'; any violation returns CURLE_FTP_BAD_FILE_LIST.
- condition: DIRORSIZE content equal to "<DIR>" marks the entry a directory with size 0; otherwise the text must convert as a number via curlx_str_numblanks or the line is rejected, and the entry is typed CURLFILETYPE_FILE.
- condition: In FILENAME content, an empty buffer is rejected; '\r' switches to a WINEOL substate requiring exactly '\n'.
- side_effect: On filename completion the buffer byte at len-1 is NUL'd, offsets.filename recorded, the entry inserted, and the state rewinds to PL_WINNT_DATE for the next line.

calls: [ftp_pl_insert_finfo](r6-ftp-list-parsing.md#u-44d8c458ab78)

<a id="u-491d39f26385"></a>
### `unix_filetype`

`static CURLcode unix_filetype(const char c, curlfiletype *t)` · [lib/ftplistparser.c:L358-L389][f1]

Maps the Unix listing type letter to a curlfiletype value, rejecting unknown letters.

**Notes.**

- failure: Any character other than - d l p s c b D yields CURLE_FTP_BAD_FILE_LIST and leaves *t untouched.

<a id="u-2008b8f1a40a"></a>
### `ftplistparser-lifecycle`

`static void fileinfo_dtor(void *user, void *element)` · [lib/ftplistparser.c:L176-L180][f1]

Lifecycle helpers for FTP wildcard list parsing: allocation, teardown, and error query.

**Notes.**

- side_effect: fileinfo_dtor ignores its user argument and delegates each list element to Curl_fileinfo_cleanup, so destroying the wildcard file list frees every accumulated fileinfo.
- side_effect: Curl_wildcard_dtor frees wc->path and wc->pattern with curlx_safefree, resets state to CURLWC_INIT, frees the WildcardData, and nulls the caller's pointer last; a NULL *wcp returns immediately.
- side_effect: Curl_ftp_parselist_data_free first releases any pending parser->file_data via Curl_fileinfo_cleanup, then frees the parser and nulls *parserp.
- contract: Curl_ftp_parselist_geterror simply returns the stored pl_data->error, letting the FTP state machine retrieve a deferred failure.

uses: [Curl_llist](r4-generic-containers.md#u-e947a3c088b0)

**Uncertainties.**

- Curl_wildcard_dtor asserts !wc->ftpwc after invoking wc->dtor, implying dtor must clear ftpwc; the actual dtor (wc_data_dtor) lives outside this file so that contract is unproven here.

<a id="u-e591ba3bfb5e"></a>
### `ftplistparser-parse-user-group`

`static CURLcode parse_unix_user(struct ftp_parselist_data *parser, struct fileinfo *i…` · [lib/ftplistparser.c:L511-L538][f1]

Parses the user and group name fields of a Unix listing entry.

**Notes.**

- condition: Both fields use the same two-substate pattern: skip blanks in the PRESPACE state, then capture bytes until a blank; the byte before the terminator is NUL-terminated in place.
- side_effect: User parsing records offsets.user and advances to PL_UNIX_GROUP; group parsing records offsets.group and advances to PL_UNIX_SIZE; neither field validates content, and both tolerate absent (all-blank) fields.

<a id="u-358345696e90"></a>
### `Curl_fileinfo_alloc`

`struct fileinfo *Curl_fileinfo_alloc(void)` · [lib/fileinfo.c:L30-L33][f2]

Allocates a zeroed fileinfo record for FTP wildcard LIST parsing.

**Notes.**

- failure: If curlx_calloc fails the returned pointer is expected to be NULL; no local error handling exists.

uses: [fileinfo](r5-protocol-headers.md#u-7726b7af2a15)

**Uncertainties.**

- curlx_calloc is not supplied; zero-fill and NULL-on-failure are assumed from its name

<a id="u-5a16fa3aa02a"></a>
### `Curl_fileinfo_cleanup`

`void Curl_fileinfo_cleanup(struct fileinfo *finfo)` · [lib/fileinfo.c:L35-L42][f2]

Frees a fileinfo: releases its dynbuf then the record itself, tolerating NULL input.

**Notes.**

- contract: Passing NULL is a no-op due to the early return, so callers need not pre-check.

calls: [curlx_dyn_free](r3-dynbuf.md#u-21f694d1bd8a)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/ftplistparser.c
[f2]: ../../../../../../eval/curl-2c04412/lib/fileinfo.c
