# Form/Multipart Argument Parsing

**Capability.** Parses 'name=contents' form arguments into a tool_mime tree (data, file/stdin sources, nested parts) with type=/filename=/encoder=/headers= attribute clauses, then translates the tree into libcurl curl_mime parts preserving order, with stdin-backed read/seek callbacks and recursive cleanup.

Use this subtree to follow -F parsing from raw command-line text to a ready curl_mime. formparse drives clause parsing via get_param_part and word extraction; tool2curlmime/tool2curlparts perform the final translation; residuals are constants and documentation.

**Depends on.**

- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) · graph-confirmed · 10 edge(s)

Parent: [curl Command-Line Tool Support](r3-cli-tool.md)

## Units (28)

<a id="u-d8ed0bd087d0"></a>
### `tool_formparse.c module code (L1–L32)`

`module_region` · [src/tool_formparse.c:L1-L32][f1]

License text and includes of tool_cfgable.h, tool_msgs.h, tool_paramhlp.h, tool_formparse.h, and tool_parsecfg.h; non-behavioral preamble.

<a id="u-e8f01c86913a"></a>
### `tool_formparse.c module code (L69–L76)`

`module_region` · [src/tool_formparse.c:L69-L76][f1]

Macros CURL_MASK_UCOFFT/CURL_MASK_SCOFFT and the uztoso comment; constants only.

<a id="u-6d2ad649c1da"></a>
### `uztoso`

`static curl_off_t uztoso(size_t uznum)` · [src/tool_formparse.c:L77-L93][f1]

Converts an unsigned size_t to signed curl_off_t, masking the value to the positive range of curl_off_t via CURL_MASK_SCOFFT.

DEBUGASSERT fires (debug builds) if the value exceeds the signed maximum; in release builds the value is silently masked, so oversized sizes wrap rather than error.

**Uncertainties.**

- Actual behavior on out-of-range input in release builds is truncation by masking; no error is returned.

<a id="u-76e73ef9aa0f"></a>
### `tool_mime_new`

`static struct tool_mime *tool_mime_new(struct tool_mime *parent, toolmimekind kind)` · [src/tool_formparse.c:L33-L47][f1]

Allocates a zeroed tool_mime node of the given kind and links it as the newest subpart of an optional parent.

On allocation failure it returns NULL without side effects; with a parent, the node is prepended to parent->subparts and its prev pointer records the previous head, so sibling order in the tree is reverse of insertion.

<a id="u-751315da1138"></a>
### `tool_mime_new_data`

`static struct tool_mime *tool_mime_new_data(struct tool_mime *parent, char *mime_data)` · [src/tool_formparse.c:L54-L69][f1]

Creates a TOOLMIME_DATA node holding a copy of the given string.

The data is duplicated first; only if that succeeds is the node allocated, and if node allocation then fails the copy is freed so no memory leaks. Returns NULL when either allocation fails; otherwise the node owns the copied data.

calls: [tool_mime_new](r3-form-parsing.md#u-76e73ef9aa0f)

<a id="u-76eb9709b6fd"></a>
### `tool_mime_new_parts`

`static struct tool_mime *tool_mime_new_parts(struct tool_mime *parent)` · [src/tool_formparse.c:L49-L52][f1]

Convenience wrapper creating a TOOLMIME_PARTS node via tool_mime_new with the given parent; inherits that function's NULL-on-allocation-failure behavior and reverse-order sibling linking.

calls: [tool_mime_new](r3-form-parsing.md#u-76e73ef9aa0f)

<a id="u-d125a2a9a1e4"></a>
### `tool_mime_new_filedata`

`static struct tool_mime *tool_mime_new_filedata(struct tool_mime *parent, const char …` · [src/tool_formparse.c:L95-L174][f1]

Creates a tool_mime node representing a file upload source, distinguishing a named file from standard input.

Sets *errcode to CURLE_OUT_OF_MEMORY on entry. If filename is not "-": duplicates the name, allocates a TOOLMIME_FILE node (TOOLMIME_FILEDATA instead when isremotefile is false), frees the duplicate on allocation failure, and sets *errcode to CURLE_OK. If filename is "-": puts stdin in binary mode, records the ftell origin, and either references a regular-file region (size = st_size - origin, clamped at 0, with VMS record-format exclusions) or buffers all of stdin via file2memory; PARAM_NO_MEM returns NULL immediately with *errcode CURLE_OUT_OF_MEMORY, PARAM_READ_ERROR records CURLE_READ_ERROR for later, and a zero-length buffer is replaced by an empty string (failure returns NULL). A TOOLMIME_STDIN node (TOOLMIME_STDINDATA when not remote) is then created carrying data, origin, size, curpos=0; allocation failure frees buffered data and returns NULL. *errcode is CURLE_OK or the remembered CURLE_READ_ERROR only on success; on NULL return the caller can only infer an allocation failure except in the PARAM_NO_MEM case.

calls: [tool_mime_new](r3-form-parsing.md#u-76e73ef9aa0f), [uztoso](r3-form-parsing.md#u-6d2ad649c1da); contract: [tool_mime_free](r3-form-parsing.md#u-f5abc1c0adbb)

**Uncertainties.**

- Whether curlx_fstat/VMS branches behave as assumed depends on headers not supplied.
- *errcode stays CURLE_OUT_OF_MEMORY whenever the node allocation fails, conflating allocation and read errors.

<a id="u-d94254b70c4b"></a>
### `tool_formparse.c module code (L191–L193)`

`module_region` · [src/tool_formparse.c:L191-L193][f1]

Comment marking the stdin mime callbacks section; no code.

<a id="u-d3c9df3176de"></a>
### `tool_mime_stdin_read`

`static size_t tool_mime_stdin_read(char *buffer, size_t size, size_t nitems, void *arg)` · [src/tool_formparse.c:L194-L227][f1]

Read callback serving stdin-backed mime parts.

If the part has a known non-negative size it returns 0 at end of data and clamps the request to the remaining byte count. When the part buffers data in memory it memcpy's from sip->data at curpos; otherwise it fread()s from stdin, and on a stream error warns once with the errno text and returns CURL_READFUNC_ABORT, which signals the transfer to fail. On success curpos advances by the number of bytes delivered.

calls: [uztoso](r3-form-parsing.md#u-6d2ad649c1da)

**Uncertainties.**

- Whether this warning can actually occur more than once per transfer is not provable from this file despite the comment.

<a id="u-06fbd78db9d6"></a>
### `tool_mime_stdin_seek`

`static int tool_mime_stdin_seek(void *instream, curl_off_t offset, int whence)` · [src/tool_formparse.c:L229-L247][f1]

Seek callback for stdin-backed parts.

SEEK_CUR offsets from curpos and SEEK_END from sip->size; other whence values use the offset directly. A resulting negative offset returns CURL_SEEKFUNC_CANTSEEK. For memory-backed parts only curpos is updated; for real stdin it performs curlx_fseek(stdin, offset + origin, SEEK_SET), returning CANTSEEK if that fails, otherwise sets curpos and reports OK.

uses: [tool_mime_stdin_seek](r3-form-parsing.md#u-06fbd78db9d6)

<a id="u-f5abc1c0adbb"></a>
### `tool_mime_free`

`void tool_mime_free(struct tool_mime *mime)` · [src/tool_formparse.c:L176-L191][f1]

Recursively releases a tool_mime tree: frees subparts then prev siblings, then each owned string (name, filename, type, encoder, data), the headers list via curl_slist_free_all, and finally the node itself.

NULL input is a no-op; cyclic structures would recurse indefinitely, but none are produced by the constructors here.

calls: [tool_mime_free](r3-form-parsing.md#u-f5abc1c0adbb)

<a id="u-945b52cde12e"></a>
### `tool_formparse.c module code (L247–L252)`

`module_region` · [src/tool_formparse.c:L247-L252][f1]

Comment and the MAX_FORMPARTS macro (100000), bounding formpart chains in tool2curlparts; constant only.

<a id="u-87c76dd51f4c"></a>
### `tool2curlparts`

`static CURLcode tool2curlparts(CURL *curl, struct tool_mime *m, curl_mime *mime)` · [src/tool_formparse.c:L253-L349][f1]

Translates a chain of tool_mime siblings (linked through prev) into libcurl mime parts on the given curl_mime, preserving order by first counting nodes and filling an array back-to-front.

A chain longer than MAX_FORMPARTS (100000) returns CURLE_BAD_FUNCTION_ARGUMENT; node-array allocation failure returns CURLE_OUT_OF_MEMORY; a NULL input chain returns CURLE_OK. Each node becomes a part configured by kind: TOOLMIME_PARTS recurses via tool2curlmime (freeing the sub-mime if attachment fails), TOOLMIME_DATA sets literal data, TOOLMIME_FILE/FILEDATA set file data (FILEDATA with no filename additionally clears the part filename), TOOLMIME_STDIN defaults the filename to "-" and falls through to STDINDATA which installs the stdin read/seek callbacks with node as the argument; other kinds add an empty part. Common attributes are applied in order — filename, type, headers (not owned by libcurl), encoder, name — stopping at the first failure, whose CURLcode is returned after freeing the node array.

calls: [tool2curlmime](r3-form-parsing.md#u-b90bfb405303); uses: [tool_mime_stdin_read](r3-form-parsing.md#u-d3c9df3176de), [function::tool_mime_stdin_seek::6329][f1]

**Uncertainties.**

- Whether curl_mime_headers copies or aliases node->headers depends on lib/mime.c, not supplied.

<a id="u-b90bfb405303"></a>
### `tool2curlmime`

`CURLcode tool2curlmime(CURL *curl, struct tool_mime *m, curl_mime **mime)` · [src/tool_formparse.c:L351-L365][f1]

Creates a libcurl mime handle for the given curl and fills it from the subparts of a tool_mime root.

On curl_mime_init failure returns CURLE_OUT_OF_MEMORY with *mime possibly left as the NULL result of init; on any translation error the mime is freed, *mime set to NULL, and the error code returned. Success leaves *mime owned by the caller.

calls: [tool2curlparts](r3-form-parsing.md#u-87c76dd51f4c)

**Uncertainties.**

- Behavior when m itself is NULL: m->subparts would dereference NULL; callers are expected to pass a valid root.

<a id="u-3427c9402125"></a>
### `tool_formparse.c module code (L365–L371)`

`module_region` · [src/tool_formparse.c:L365-L371][f1]

Comment introducing the form-parameter word helper; no code.

<a id="u-de882f1980b9"></a>
### `get_param_word`

`static char *get_param_word(char **str, char **end_pos, char endchar)` · [src/tool_formparse.c:L372-L425][f1]

Extracts the next word from a form-parameter string, advancing *str past it.

If the word starts with a double quote, escapes (\\ or \") are skipped while scanning for the closing quote; on finding it the escaped segment is rewritten in place without backslashes and *end_pos marks the unescaped end, and any non-space, non-';'/endchar trailing data after the quote triggers a warning. The return value points inside the quotes (past the opening one). If the closing quote is missing the text is re-parsed as unquoted. Unquoted words run until ';', the caller's endchar, or NUL; *str and *end_pos both land on that terminator, trailing spaces remain in the returned span (callers strip them).

**Notes.**

- side_effect: Escape removal rewrites the caller's buffer in place, shortening the word.

<a id="u-55a75cb76b85"></a>
### `tool_formparse.c module code (L425–L427)`

`module_region` · [src/tool_formparse.c:L425-L427][f1]

Comment describing get_param_word's postcondition; no code.

<a id="u-8e0bceb86c4a"></a>
### `slist_append`

`static int slist_append(struct curl_slist **plist, const char *data)` · [src/tool_formparse.c:L428-L437][f1]

Appends a string to a curl_slist, updating *plist to the new list head.

Returns 0 on success and -1 without modifying *plist when curl_slist_append fails (allocation failure), letting callers detect and clean up.

<a id="u-20e65d83d58b"></a>
### `tool_formparse.c module code (L437–L442)`

`module_region` · [src/tool_formparse.c:L437-L442][f1]

HEADER_LINE_BUFFER_SIZE macro (8192) limiting dynbuf size for header lines; constant only.

<a id="u-2c374e4c51ac"></a>
### `read_field_headers`

`static int read_field_headers(FILE *fp, struct curl_slist **pheaders)` · [src/tool_formparse.c:L443-L502][f1]

Reads header lines from a file into a curl_slist, returning 0 on success and -1 on error.

Lines starting with '#' are comments and skipped; a line starting with a space continues (folds onto) the previous header, if one exists — the previous node's text plus the new line replace the last node's data, built with dynbufs and allocated via curl_maprintf to stay compatible with curl_slist_append ownership; fold with no previous header falls through to normal append. Trailing CRLF/whitespace is trimmed and empty lines skipped. dynbuf or allocation failures set err=-1 and stop; my_get_line reporting an error after the loop yields 'Failed to read field headers'. Both error paths emit an errorf message.

calls: [slist_append](r3-form-parsing.md#u-8e0bceb86c4a); uses: [read_field_headers](r3-form-parsing.md#u-2c374e4c51ac)

**Uncertainties.**

- Behavior when a folded line appears with *pheaders NULL: it is appended as a new header; intent inferred from code order.

<a id="u-6d8439a94e85"></a>
### `param_type`

`static void param_type(char **ptr, char **ptype, char **endct, char *sep)` · [src/tool_formparse.c:L504-L519][f1]

Parses a 'type=' clause already matched at *ptr.

Skips blanks after the prefix, records the content-type start in *ptype, finds its end via a delimiter set including spaces, punctuation, and CR/LF, and stores that position in *endct with the terminating character in *sep, updating *ptr to the end. The type text is not NUL-terminated here; the caller terminates it later via endct.

<a id="u-9c3b3a078345"></a>
### `param_filename`

`static void param_filename(char **ptr, char **endct, char **pfilename, char endchar, …` · [src/tool_formparse.c:L521-L543][f1]

Parses a 'filename=' clause.

First terminates any pending content type via *endct. Skips blanks, extracts the word with get_param_word, and for unquoted words strips trailing spaces from endpos. *sep receives the terminator character, the word is NUL-terminated at endpos, and *ptr advances past the word.

calls: [get_param_word](r3-form-parsing.md#u-de882f1980b9)

<a id="u-b323319298bb"></a>
### `param_headers`

`static int param_headers(char **ptr, char **endct, struct curl_slist **pheaders, char…` · [src/tool_formparse.c:L545-L609][f1]

Parses a 'headers=' clause, terminating any pending content type first.

After '@' or '<' it treats the word as a header file name: opens it read-only, warning with the strerror text if fopen fails, otherwise reads the file with read_field_headers; a read failure frees all headers accumulated so far and returns -1. Otherwise the word is a literal header appended with slist_append; append failure reports 'Out of memory for field header', frees the header list, and returns -1. On success *ptr advances and 0 is returned; headers accumulate in *pheaders across multiple clauses.

calls: [get_param_word](r3-form-parsing.md#u-de882f1980b9), [read_field_headers](r3-form-parsing.md#u-2c374e4c51ac), [slist_append](r3-form-parsing.md#u-8e0bceb86c4a)

**Uncertainties.**

- Distinction between '@' and '<' prefixes is not visible; both take the same file path in this code.

<a id="u-f823537b8571"></a>
### `param_encoder`

`static void param_encoder(char **ptr, char **endct, char **pencoder, char endchar, ch…` · [src/tool_formparse.c:L611-L633][f1]

Parses an 'encoder=' clause like param_filename: terminates a pending content type, skips blanks, extracts the word via get_param_word, strips trailing spaces if unquoted, records the separator, NUL-terminates the encoder text, and advances *ptr.

calls: [get_param_word](r3-form-parsing.md#u-de882f1980b9)

<a id="u-3621b4f8b2f2"></a>
### `tool_formparse.c module code (L633–L660)`

`module_region` · [src/tool_formparse.c:L633-L660][f1]

Doc comment block describing get_param_part's contract and parameters; documentation only.

<a id="u-0f3c43a2031d"></a>
### `get_param_part`

`static int get_param_part(char endchar, char **str, char **pdata, char **ptype, char …` · [src/tool_formparse.c:L661-L754][f1]

Parses one form-parameter block: a primary data word followed by semicolon-separated attributes.

All optional out-pointers are initialized to NULL. After extracting the data word (trailing spaces stripped when unquoted) it loops while the separator is ';', dispatching on prefix: type= via param_type (which may be extended by a later unmatched token treated as continuation of the content type), filename=, headers= (a -1 return propagates immediately), encoder=, content-type continuation when endct is set, or an unknown word that is skipped with a warning if non-empty. After the loop any open content type is terminated. Each parsed attribute is stored only if the caller requested it; otherwise a warning names the disallowed value (headers additionally freed). Returns the terminating character as an unsigned char value, or -1 only from the headers error path; *str is left at the terminator.

calls: [get_param_word](r3-form-parsing.md#u-de882f1980b9), [param_type](r3-form-parsing.md#u-6d8439a94e85), [param_filename](r3-form-parsing.md#u-9c3b3a078345), [param_headers](r3-form-parsing.md#u-b323319298bb), [param_encoder](r3-form-parsing.md#u-f823537b8571)

**Uncertainties.**

- checkprefix is external to this batch; its case behavior is not provable here.
- The 'while(p++ && ISBLANK(*p))' blank-skip has unusual pointer arithmetic; exact skip semantics on NUL depend on it.

<a id="u-58df9eaa0c59"></a>
### `tool_formparse.c module code (L754–L811)`

`module_region` · [src/tool_formparse.c:L754-L811][f1]

Long usage comment block for formparse syntax (multiple files, quoting, type/filename/headers attributes) and the SET_TOOL_MIME_PTR macro, which strdups a field into a tool_mime and jumps to fail on allocation failure; the macro's behavior is exercised within formparse.

<a id="u-af89b610125e"></a>
### `formparse`

`int formparse(const char *input, struct tool_mime **mimeroot, struct tool_mime **mime…` · [src/tool_formparse.c:L812-L991][f1]

Parses one 'name=contents' command-line form argument and appends a part to a growing tool_mime tree, returning 0 on success and 1 on any failure after warning.

If *mimecurrent is NULL it creates the root TOOLMIME_PARTS node. The input is duplicated (allocation failure fails); a missing '=' warns 'Illegally formatted input field' and fails. Value dispatch, all suppressed under literal_value: '(' starts a multipart by creating a PARTS part and descending into it, parsing its inner content with endchar '\0'; a lone ")" (only when no name was given) pops back to the parent, warning and failing if already at root; '@' uploads one or more comma-separated files, creating a nested PARTS container for multiple files, each added with tool_mime_new_filedata as a remote file — a CURLE_READ_ERROR from stdin fails only if some data was already read (size > 0), otherwise the buffered data is dropped and size set to -1 so libcurl reads stdin later; '<' reads content from a local file via tool_mime_new_filedata with the same stdin-error handling; anything else becomes a TOOLMIME_DATA part (literal_value uses the raw remaining string, skipping attribute parsing). Each part receives headers, type, filename, encoder, and name via SET_TOOL_MIME_PTR, which fails out on strdup failure. In the non-multipart branches a leftover non-NUL separator warns 'garbage at end of field specification'. Cleanup on all exits frees the input copy and any unclaimed headers list.

**Notes.**

- failure: On any fail path, parts already attached to *mimecurrent remain in the tree; the caller owns the partially built tree via *mimeroot.
- side_effect: *mimecurrent tracks the insertion point across calls, enabling multi-line multipart definitions.

calls: [tool_mime_new_parts](r3-form-parsing.md#u-76eb9709b6fd), [tool_mime_new_data](r3-form-parsing.md#u-751315da1138), [tool_mime_new_filedata](r3-form-parsing.md#u-d125a2a9a1e4), [get_param_part](r3-form-parsing.md#u-0f3c43a2031d); uses: [tool_mime](r14-tool-data-helpers.md#u-1ac3df52f22c)

**Uncertainties.**

- In the '(' branch headers parsed before the part is created would leak only if tool_mime_new_parts fails; exact leak behavior on that path depends on the fail cleanup, which frees `headers` only when it is still set — part->headers assigned before SET_TOOL_MIME_PTR failure stays owned by the tree.
- The '(' branch parses data but never stores it as the part's data field; what libcurl does with a PARTS node having unused `data` is decided elsewhere.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_formparse.c
