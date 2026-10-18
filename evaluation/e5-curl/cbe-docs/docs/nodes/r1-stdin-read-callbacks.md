# Upload Read Callbacks

**Capability.** Owns the CURLOPT_READFUNCTION implementation for uploads: reading from infd with size-limit and timeout enforcement, a progress callback that resumes paused busy reads, and the non-Windows waitfd helper for input readiness.

Use this to trace how upload data flows from a file descriptor into the transfer. tool_read_cb and tool_readbusy_cb are the registered callbacks; waitfd implements the blocking wait they rely on.

**Depends on.**

- [Tool Operation Configuration](r1-tool-operation-config.md) · model-inferred · 0 edge(s)

Parent: [curl Command-Line Tool](r1-curl-tool.md)

## Units (4)

<a id="u-9e81b5491269"></a>
### `tool_cb_rea-c-module-regions`

`module_region` · [src/tool_cb_rea.c:L1-L43][f1]

Non-behavioral regions of tool_cb_rea.c: license header, platform-conditional includes for select/poll, and includes of tool_cfgable.h, tool_cb_rea.h, tool_operate.h, tool_msgs.h, plus the whole file is guarded by #ifndef _WIN32 for waitfd.

<a id="u-f117240dbaea"></a>
### `tool_read_cb`

`size_t tool_read_cb(char *buffer, size_t sz, size_t nmemb, void *userdata)` · [src/tool_cb_rea.c:L73-L152][f1]

CURLOPT_READFUNCTION callback that reads upload data from per->infd, enforcing the upload size limit and optional total transfer timeout.

**Notes.**

- condition: Returns 0 (EOF) immediately when uploadfilesize is set and uploadedsofar already equals it.
- condition: If config->timeout_ms is set and elapsed ms since per->start exceeds it, returns 0; otherwise on non-Windows it blocks in waitfd for the remaining time, clamped to INT_MAX.
- condition: On Windows with -T. (uploadfile == "." and infd > 0), reads via sread(); on SOCK_EAGAIN it sets config->readbusy and returns CURL_READFUNC_PAUSE; other errors are treated as EOF (rc = 0).
- condition: On other paths, read() EAGAIN likewise pauses via CURL_READFUNC_PAUSE with readbusy set and errno cleared; other read errors yield rc = 0 since size_t cannot be negative.
- failure: If the read would push uploadedsofar past uploadfilesize, warns and truncates rc to the remaining bytes.
- side_effect: Clears config->readbusy to FALSE before returning.

calls: [waitfd](r1-stdin-read-callbacks.md#u-34c26e80d8a4), [warnf](r5-tool-messaging.md#u-b1c19a3e5da7)

**Uncertainties.**

- Under CURL_WINDOWS_UWP the -T. branch is replaced by a warnf call; actual read behavior there is not present in this source

<a id="u-f82f38e00c15"></a>
### `tool_readbusy_cb`

`int tool_readbusy_cb(void *clientp, curl_off_t dltotal, curl_off_t dlnow, curl_off_t …` · [src/tool_cb_rea.c:L157-L186][f1]

XFERINFOFUNCTION progress callback that resumes a paused busy read once upload progress stalls, then reports normal progress continuation.

**Notes.**

- side_effect: Uses a static ulprev across calls to detect no upload progress since the previous callback.
- condition: When config->readbusy is set: waits 1 ms if upload did not advance, clears readbusy, and unpauses the easy handle; returns 0 if per->noprogress, else CURL_PROGRESSFUNC_CONTINUE.

calls: [waitfd](r1-stdin-read-callbacks.md#u-34c26e80d8a4), [curl_easy_pause](r14-core-easy-lifecycle.md#u-1e5032112aa7)

**Uncertainties.**

- The static ulprev is shared across all transfers, so concurrent transfers with different per handles share progress state

<a id="u-34c26e80d8a4"></a>
### `waitfd`

`static void waitfd(int waitms, int fd)` · [src/tool_cb_rea.c:L44-L67][f1]

Blocks up to a given number of milliseconds waiting for read activity on a non-socket file descriptor, on non-Windows builds only.

uses: [tool_read_cb](r1-stdin-read-callbacks.md#u-f117240dbaea)

**Uncertainties.**

- With HAVE_POLL undefined, fd values at or above FD_SETSIZE are silently not waited on

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_cb_rea.c
