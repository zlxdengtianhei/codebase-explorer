# Platform and MIME Header Contracts

**Capability.** Owns header-only contracts with no library-internal dependencies in this slice: the AmigaOS conditional init/cleanup declarations (macros on non-Amiga builds so callers need no ifdef), and the MIME type/state/strategy definitions shared between the mime implementation and formdata.c.

Consult these units when checking platform-conditional API surfaces or the shared MIME vocabulary (mimekind, mimestate, mimestrategy).

Parent: [curl Library Responsibilities](r13-curl-library-core.md)

## Units (2)

<a id="u-826851526e42"></a>
### `amigaos.h module code (L1–L41)`

`module_region` · [lib/amigaos.h:L1-L41][f1]

Header guard plus conditional declarations of Curl_amiga_init and Curl_amiga_cleanup, declared as functions only for __AMIGA__ builds with bsdsocket headers where either AmiSSL is off or the target is amigaos4; all other builds get macros mapping the calls to CURLE_OK and Curl_nop_stmt so callers need no ifdef.

<a id="u-f6019b0ebc1a"></a>
### `mime.h-mime-types-and-state`

`enum mimekind` · [lib/mime.h:L43-L50][f2]

Type definitions shared by the mime implementation and formdata.c: mimekind enumerates part source kinds (none, data, file, callback, multipart); mimestate tokens drive readback position (begin, curl/user headers, end-of-headers, body, boundary phases, content, end); mimestrategy selects MAIL or FORM header generation.

mime_encoder pairs an encoding name with encode/size function pointers; mime_encoder_state tracks output-line position and a 256-byte input buffer (ENCODING_BUFFER_SIZE); mime_state holds the state token with a pointer and offset. curl_mime is a multipart container with parent/first/last part links, a boundary string of MIME_BOUNDARY_LEN characters, and readback state; curl_mimepart is a doubly-linked-list node carrying its kind, flags, data or callback source (read/seek/free functions and arg), FILE pointer, curl- and user-supplied headers, mimetype, filename, name, expected size, readback state, encoder and its state, and the last read status.

**Uncertainties.**

- Interpretation of each mimestate token's runtime role rests on the header's comments; the state machine itself is in lib/mime.c.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/amigaos.h
[f2]: ../../../../../../eval/curl-2c04412/lib/mime.h
