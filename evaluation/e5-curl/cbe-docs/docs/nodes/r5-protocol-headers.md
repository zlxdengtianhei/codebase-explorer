# Internal Protocol Declarations

**Capability.** Declarations and small value types for protocols and features not otherwise detailed here: FTP strategy enum and declarations, RTSP, FTP wildcard fileinfo, form parsing storage, netrc cache types, and the Windows SSPI header.

Use as a reference index when a symbol from these headers appears elsewhere; these units carry types and prototypes, not runtime behavior. The netrc struct caches one parsed file; the ftp enum selects CWD strategy.

Parent: [Protocol and Filter Implementations](r5-protocol-implementations.md)

## Units (11)

<a id="u-bcc5b29c4f8f"></a>
### `formdata.h-FormInfo-struct`

`struct FormInfo` · [lib/formdata.h:L33-L47][f1]

Temporary per-form storage used while parsing curl_formadd options.

Holds four bufrefs (name, value, contenttype, showfilename), a raw buffer pointer and user callback pointer, a 'more' link for multi-file subparts, a contentheader slist, length fields, and flag bits. Declared and the Curl_getformdata prototype exposed only when CURL_DISABLE_FORM_API is not defined.

<a id="u-7aef39199911"></a>
### `lib-ftp-h-declarations`

`group` · [lib/ftp.h:L1-L34][f2]

Header guarding the FTP support declarations: an include guard wraps a curl_setup.h include; when FTP is enabled it declares the Curl_protocol_ftp protocol-structure constant and the Curl_ftp_conns_match function, and defines the curl_ftpfile strategy enum; outside the guard it defines DEFAULT_ACCEPT_TIMEOUT as 60000 ms unconditionally.

No definitions or runtime logic live here; the declared symbols' behavior is in the corresponding implementation files.

group: [lib/ftp.h:<enum>](r5-protocol-headers.md#u-bbcf962ff7cc), [lib-ftp-h-declarations](r5-protocol-headers.md#u-7aef39199911)

**Uncertainties.**

- The implementations of Curl_protocol_ftp and Curl_ftp_conns_match are outside this file; their behavior cannot be read from the supplied source.

<a id="u-bbcf962ff7cc"></a>
### `lib/ftp.h:<enum>`

`enum` · [lib/ftp.h:L34-L39][f2]

Defines the curl_ftpfile enum selecting the FTP file-access strategy: MULTICWD issues a CWD per path component per RFC1738, NOCWD operates on full paths directly, SINGLECWD performs one CWD then file operations.

These enumerators are compile-time constants with no runtime behavior.

<a id="u-858c1a5dfaef"></a>
### `curl_sspi.h module code (L46–L103)`

`struct` · [lib/curl_sspi.h:L43-L46][f3]

Header for the Windows SSPI support layer.

It includes <sspi.h>, defines CURL_SEC_WINNT_AUTH_IDENTITY as the UNICODE or ANSI identity type depending on UNICODE, provides compatibility typedefs/macros for missing platform definitions (SecPkgContext_Bindings, SECPKG_ATTR_ENDPOINT_BINDINGS, ISC_REQ_USE_HTTP_STYLE, several SEC_E/SEC_I status codes), declares the SSPI functions and the extern Curl_pSecFn dispatch-table pointer, and defines SP_NAME_* package name macros plus KERB_WRAP_NO_ENCRYPT. All content is compiled only under USE_WINDOWS_SSPI.

group: [curl_sspi.h module code (L46–L103)](r5-protocol-headers.md#u-858c1a5dfaef)

<a id="u-7726b7af2a15"></a>
### `fileinfo`

`struct fileinfo` · [lib/fileinfo.h:L31-L35][f4]

Defines the per-directory-entry record used by FTP wildcard listing.

**Notes.**

- field: Combines the public curl_fileinfo payload, an intrusive Curl_llist_node for the wildcard file list, and a dynbuf holding the raw line text; offset-based pointers into that buffer are computed in ftp_pl_insert_finfo.

<a id="u-87eb02334ed5"></a>
### `rtsp.h module code (L1–L47)`

`module_region` · [lib/rtsp.h:L1-L47][f5]

RTSP declarations.

When RTSP is built, declares Curl_rtsp_parseheader for parsing RTSP response headers and exposes Curl_protocol_rtsp; otherwise Curl_rtsp_parseheader becomes a macro returning CURLE_NOT_BUILT_IN. Also defines RTSPREQ_* enum aliases mapping onto CURL_RTSPREQ_* values from NONE through LAST.

<a id="u-cdbf9a7a3c10"></a>
### `lib/netrc.h:<enum>`

`enum` · [lib/netrc.h:L41-L48][f6]

NETRCcode result enum: OK, NO_MATCH, SYNTAX_ERROR, FILE_MISSING, OUT_OF_MEMORY, and the never-used NETRC_LAST sentinel.

<a id="u-aa432683d6a5"></a>
### `netrc.h module code (L1–L34)`

`module_region` · [lib/netrc.h:L1-L34][f6]

Header guard, includes, and forward declarations for Curl_easy and Curl_creds under the CURL_DISABLE_NETRC guard.

<a id="u-520c018024be"></a>
### `netrc.h module code (L39–L41)`

`module_region` · [lib/netrc.h:L39-L41][f6]

Blank separator lines after the struct.

<a id="u-928cf92f5100"></a>
### `netrc.h module code (L48–L68)`

`module_region` · [lib/netrc.h:L48-L68][f6]

Prototypes for Curl_netrc_strerror/init/cleanup/scan; when netrc is disabled, init and cleanup compile to empty macros.

Declarations only.

<a id="u-20e15b85bdd7"></a>
### `store_netrc`

`struct store_netrc` · [lib/netrc.h:L35-L39][f6]

store_netrc caches one parsed netrc file: filebuf holds the content, filename the loaded path, loaded whether the cache is valid.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/formdata.h
[f2]: ../../../../../../eval/curl-2c04412/lib/ftp.h
[f3]: ../../../../../../eval/curl-2c04412/lib/curl_sspi.h
[f4]: ../../../../../../eval/curl-2c04412/lib/fileinfo.h
[f5]: ../../../../../../eval/curl-2c04412/lib/rtsp.h
[f6]: ../../../../../../eval/curl-2c04412/lib/netrc.h
