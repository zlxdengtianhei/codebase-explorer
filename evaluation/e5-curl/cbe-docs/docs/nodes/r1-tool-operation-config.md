# Tool Operation Configuration

**Capability.** Owns the tool's configuration structs: the large OperationConfig mirroring command-line options (postdata, slists, MIME, limits, BIT flags, file-clobber mode), the per-URL State struct for globbed transfers, and the Windows wide-character termout buffering.

Consult this when a tool behavior depends on parsed options. OperationConfig is the central struct read throughout the tool; State carries per-URL glob iteration state used by create_transfer.

**Depended on by.**

- [--libcurl Code Generation](r1-libcurl-codegen.md) · model-inferred · 0 edge(s)
- [Upload Read Callbacks](r1-stdin-read-callbacks.md) · model-inferred · 0 edge(s)
- [Windows/DOS Tool Support](r1-windows-tool-support.md) · model-inferred · 0 edge(s)

Parent: [curl Command-Line Tool](r1-curl-tool.md)

## Units (3)

<a id="u-0ddebfc61157"></a>
### `tool-cfgable-h-global-config`

`struct termout` · [src/tool_cfgable.h:L317-L320][f1]

On Windows, termout buffers a wide-character output segment (buf plus DWORD len).

GlobalConfig holds tool-wide state: a State for transfer creation, trace dump settings, libcurl-code output file, SSL session file, tool variables, the OperationConfig linked list (first/current/last), optional Windows termout, inter-transfer millisecond delay, trace/progress/parallel/verbosity settings (including debug-only test_duphandle and test_event_based), and BIT flags for styled output, silence, tty detection, tracing, and fail-early behavior. Followed by prototypes for config allocation/free and globalconf init/free.

<a id="u-97ea51fb524a"></a>
### `tool-cfgable-h-operation-config`

`struct OperationConfig` · [src/tool_cfgable.h:L53-L204][f1]

OperationConfig is the large per-operation option struct mirroring curl command-line options: dynamic postdata, strings for URLs/proxy/TLS/auth/mail/SSH/ECH settings, curl_slist collections (headers, quotes, resolve, connect_to, telnet options), MIME structures, getout list pointers (first/last/get/out/ul plus num_urls), linked-list prev/next pointers, numeric limits (bandwidth, timeouts, retries, ports, low-speed), an enum file_clobber_mode with CLOBBER_DEFAULT/NEVER/ALWAYS semantics, and a large block of BIT flag fields covering transfer, TLS, FTP, proxy, retry, and output behaviors (e.g. show_headers, content_disposition, xattr, rm_partial).

Also defines FAIL_NONE/WITH_BODY/WO_BODY constants and MAX_CONFIG_LINE_LENGTH, the checkprefix macro (case-insensitive prefix test via curl_strnequal), and extern global. Declarations for config_alloc/config_free/globalconf_init/globalconf_free follow without bodies here.

group: [tool-cfgable-h-global-config](r1-tool-operation-config.md#u-0ddebfc61157)

<a id="u-968b5d7caeb1"></a>
### `tool-cfgable-h-state`

`struct State` · [src/tool_cfgable.h:L38-L47][f1]

State struct holds per-URL iteration state for create_transfer: the current getout urlnode, URLGlob instances for the URL and input globs, the upload filename, and counters/indices for uploads and globbed URLs (upnum, upidx, urlnum, urlidx).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_cfgable.h
