# Tool startup

**Capability.** Process entry point (main/wmain) ensuring std streams are open and enabling optional debug memory tracking from environment variables.

Read for initialization-order changes; memory tracking is a compile-time-guarded no-op otherwise.

Parent: [Command-line tool](r12-cli-tool.md)

## Units (3)

<a id="u-65abc3222a2e"></a>
### `src/tool_main.c:main`

`int main(int argc, char *argv[]) #endif` · [src/tool_main.c:L152-L216][f1]

Tool entry point (main or wmain under _UNICODE).

Initializes stderr handling, then on Windows supports a pre-init '--dump-module-paths' diagnostic that prints loaded module paths and returns 0 if the list was non-NULL else 1, and runs win32_init whose failure is reported via errorf and returned as the exit code. Calls main_checkfds, returning CURLE_FAILED_INIT with an error message on failure. Ignores SIGPIPE when HAVE_SIGNAL and SIGPIPE exist (in debug builds only when CURL_SIGPIPE_DEBUG is unset), then runs memory_tracking_init, globalconf_init, and if init succeeds runs operate(argc, argv) followed by globalconf_free; if init failed, cleanup is skipped. On Windows flushes all streams with fflush(NULL). Exits via vms_special_exit(result, vms_show) on VMS, otherwise returns (int)result.

uses: [tool_stderr.h module code (L1–L33)][f2]; calls: [main_checkfds](r12-tool-startup.md#u-08a39af42a7e), [memory_tracking_init](r12-tool-startup.md#u-25d8d0183014)

**Uncertainties.**

- operate, globalconf_init/free, win32_init, and vms_special_exit are defined in other files; their effects are not visible here.

<a id="u-08a39af42a7e"></a>
### `main_checkfds`

`static int main_checkfds(void)` · [src/tool_main.c:L86-L108][f1]

Ensures stdin, stdout, and stderr file descriptors are open by opening /dev/null for any closed one.

Only compiled with HAVE_FCNTL and HAVE_PIPE; otherwise returns 0 immediately. Loops with fcntl(F_GETFD) per descriptor (-1 means closed), opens the device read-only for stdin and write-only for the others; a failed open returns 1. main() turns 1 into 'out of file descriptors'.

calls: [src/tool_main.c:main](r12-tool-startup.md#u-65abc3222a2e)

<a id="u-25d8d0183014"></a>
### `memory_tracking_init`

`static void memory_tracking_init(void)` · [src/tool_main.c:L111-L135][f1]

Reads CURL_MEMDEBUG and CURL_MEMLIMIT environment variables to start debug-memory logging and an allocation-failure limit, only when compiled with CURL_MEMDEBUG; otherwise the name expands to a no-op statement.

CURL_MEMDEBUG's value is used as a log filename (truncated to 511 chars via curlx_strcopy); curl_free is deliberately called before curl_dbg_memdebug so the tracking log does not record an unmatched free. CURL_MEMLIMIT is parsed with curlx_str_number capped at LONG_MAX; on parse failure the limit is silently skipped.

**Notes.**

- side_effect: Installs global memory-debug logging and allocation-limit state via curl_dbg_memdebug/curl_dbg_memlimit.

calls: [src/tool_main.c:main](r12-tool-startup.md#u-65abc3222a2e)

**Uncertainties.**

- Behavior of curl_dbg_memdebug/curl_dbg_memlimit is defined outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_main.c
[f2]: ../../../../../../eval/curl-2c04412/src/tool_stderr.h
