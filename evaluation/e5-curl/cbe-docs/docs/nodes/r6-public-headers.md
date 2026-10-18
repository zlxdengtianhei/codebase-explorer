# Public API Headers

**Capability.** Compile-time public contracts: printf-family wrappers with format-string checking and easy-option introspection types.

Consult for the ABI surface consumers compile against. The option descriptor enum/struct are inferred to back easy-option lookup elsewhere.

Parent: [curl Codebase](r6-curl-codebase.md)

## Units (4)

<a id="u-58c06e0a3a3f"></a>
### `mprintf-h-printf-format-contract`

`group` · [include/curl/mprintf.h:L1-L85][f1]

Declares curl's printf-family wrappers with compile-time format-string checking.

When compiled by GCC, Clang, or IAR with C99 or later and format checks not disabled via CURL_NO_FMT_CHECKS, CURL_TEMP_PRINTF(fmt,arg) expands to a format attribute; on MinGW without Clang it uses __MINGW_PRINTF_FORMAT if that macro exists (mingw-w64 3.0.0+, which requires stdio.h), otherwise no attribute, and elsewhere the standard printf attribute. On other compilers it expands to nothing. The wrappers themselves follow C semantics: printf/fprintf variants print to stdout or a FILE; sprintf/msnprintf write to a caller buffer, msnprintf bounded by maxlength; the v-variants take va_list; curl_maprintf/curl_mvaprintf allocate and return a string (freeing contract not stated in this header). CURL_TEMP_PRINTF is #undef'd after use unless the caller pre-defined it.

**Notes.**

- condition: If CURL_TEMP_PRINTF is already defined by the includer, the whole attribute-selection block is skipped and it is not undefined at the end.
- condition: Defining CURL_NO_FMT_CHECKS suppresses the format attribute on all compilers.

imports: [mprintf-h-printf-format-contract](r6-public-headers.md#u-58c06e0a3a3f)

**Uncertainties.**

- Whether curl_maprintf memory must be freed with curl_free or free() is not stated in this header.

<a id="u-0cc0a4f97357"></a>
### `options-h-easyoption-lookup`

`enum` · [include/curl/options.h:L31-L41][f2]

Declares the option-introspection API for easy handles.

curl_easytype enumerates the underlying option types (CURLOT_LONG, CURLOT_VALUES, CURLOT_OFF_T, CURLOT_OBJECT, CURLOT_STRING, CURLOT_SLIST, CURLOT_CBPTR, CURLOT_BLOB, CURLOT_FUNCTION), and CURLOT_FLAG_ALIAS marks entries that exist only as compatibility aliases for another preferred name. struct curl_easyoption exposes name, CURLoption id, type, and flags. Three lookups return const pointers into libcurl's option table: curl_easy_option_by_name, curl_easy_option_by_id, and curl_easy_option_next(prev) for iteration (prev NULL presumably starts iteration, though the header does not say so). The header notes CURLOPTTYPE_* id ranges still hint at the type/size curl_easy_setopt needs.

uses: [curl_easyoption](r6-public-headers.md#u-10e135d66850), [include/curl/options.h:<enum>](r6-public-headers.md#u-593c0acaabce)

**Uncertainties.**

- Return value when no option matches, and the end-of-iteration sentinel for curl_easy_option_next, are not stated in this header.

<a id="u-593c0acaabce"></a>
### `include/curl/options.h:<enum>`

`enum` · [include/curl/options.h:L31-L41][f2]

curl_easytype enum classifying easy-option value types: long, defined value set/bitmask, curl_off_t, object pointer, string, slist, callback passthrough pointer, blob, and function pointer.

<a id="u-10e135d66850"></a>
### `curl_easyoption`

`struct curl_easyoption` · [include/curl/options.h:L51-L56][f2]

Struct exposing one easy-option descriptor: option name string, CURLoption id, curl_easytype type, and unsigned flags (CURLOT_FLAG_ALIAS marks compatibility aliases).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/include/curl/mprintf.h
[f2]: ../../../../../../eval/curl-2c04412/include/curl/options.h
