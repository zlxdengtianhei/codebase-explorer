# SSH via libssh2

**Capability.** Owns the SCP/SFTP protocol implementation over libssh2: session establishment with host-key verification, an explicit per-connection state machine spanning authentication, session setup and file transfer, DO-phase entry points for SCP and SFTP, quote-command parsing, and error-code mapping. All states return CURLE_AGAIN on libssh2 EAGAIN so the multi engine can re-enter them.

Use this subtree to trace an SSH transfer from connect through auth to SCP/SFTP transfer and teardown. ssh_statemachine dispatches the state groups; sshc_cleanup is the ordered teardown shared by all exit paths.

**Depends on.**

- [Multi Interface Engine](r13-multi-engine.md) · model-inferred · 0 edge(s)

Parent: [curl Library Responsibilities](r13-curl-library-core.md)

## Units (25)

<a id="u-4ca77ac22157"></a>
### `libssh2-api`

`static CURLcode ssh_do(struct Curl_easy *data, bool *done)` · [lib/vssh/libssh2.c:L3861-L3884][f1]

Shared SSH API functions.

ssh_do is the generic DO entry: it requires the ssh_conn metadata, resets the unknown request size and the create-dirs retry flag, resets progress, and dispatches to scp_perform or sftp_perform based on the protocol. Curl_ssh_init initializes libssh2 (CURLE_FAILED_INIT on failure); Curl_ssh_cleanup calls libssh2_exit; Curl_ssh_version formats a 'libssh2/<version>' string. ssh_attach re-points the libssh2 session's abstract user pointer to the current easy handle for SSH-family connections, but only when a session already exists.

calls: [libssh2-scp-ops](r13-ssh-libssh2.md#u-71ec22bbbf0c), [libssh2-sftp-ops](r13-ssh-libssh2.md#u-e5221a2af09a)

<a id="u-fb2673af056b"></a>
### `libssh2-auth-states`

`static void ssh_state_pkey_init(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh2.c:L1127-L1144][f1]

State handlers that drive SSH authentication in order: publickey, password, hostbased, agent, keyboard-interactive.

ssh_state_pkey_init clears authed and selects publickey when CURLSSH_AUTH_PUBLICKEY is enabled and 'publickey' is in the server's authlist, else falls to SSH_AUTH_PASS_INIT. ssh_state_authlist fetches the server's auth methods for the credentials user; a NULL list means either the user was accepted with no authentication (authed=TRUE, SSH_AUTH_DONE), EAGAIN (CURLE_AGAIN), or failure: free the session and return the mapped session error. ssh_state_auth_pkey tries publickey from files; rc 0 authenticates (SSH_AUTH_DONE), EAGAIN defers, otherwise it logs the reason (using a fixed string when rc is -1 because the stored error may be stale) and falls to SSH_AUTH_PASS_INIT. ssh_state_auth_pass_init/pass attempt password auth when enabled and offered; success goes to SSH_AUTH_DONE, failure to SSH_AUTH_HOST_INIT; EAGAIN defers. ssh_state_auth_host_init routes to SSH_AUTH_HOST when hostbased is enabled and offered, else SSH_AUTH_AGENT_INIT (SSH_AUTH_HOST itself just advances to SSH_AUTH_AGENT_INIT — hostbased is never actually attempted). ssh_state_auth_agent_init creates and connects the agent when enabled and 'publickey' offered; agent object creation or connect failure falls to SSH_AUTH_KEY_INIT; connect EAGAIN defers. ssh_state_auth_agent_list lists identities (failure falls to SSH_AUTH_KEY_INIT) and resets the previous-identity cursor. ssh_state_auth_agent iterates identities, trying libssh2_agent_userauth per identity; a failed attempt advances prev_identity and retries, rc 1 means no identity matched, rc 0 authenticates (SSH_AUTH_DONE), anything else falls to SSH_AUTH_KEY_INIT; EAGAIN defers. ssh_state_auth_key_init routes to keyboard-interactive when enabled and offered, else SSH_AUTH_DONE. ssh_state_auth_key runs keyboard-interactive with kbd_callback; success authenticates, failure returns CURLE_LOGIN_DENIED; EAGAIN defers. ssh_state_auth_done rejects unauthenticated sessions (CURLE_LOGIN_DENIED, session freed), records appconnect time, sets recv/send indices, and continues to SSH_SFTP_INIT for SFTP or SSH_STOP for SCP.

uses: [libssh2-key-callbacks](r13-ssh-libssh2.md#u-19176ee84c57); calls: [libssh2-error-mapping](r13-ssh-libssh2.md#u-6c67e4f87551)

**Uncertainties.**

- Hostbased authentication is reachable in the enum (SSH_AUTH_HOST) but the handler immediately advances, so it never performs an auth attempt.

<a id="u-6c67e4f87551"></a>
### `libssh2-error-mapping`

`static const char *sftp_libssh2_strerror(unsigned long err)` · [lib/vssh/libssh2.c:L61-L125][f1]

Translates libssh2/SFTP error codes into libcurl error codes and human-readable messages.

sftp_libssh2_strerror maps LIBSSH2_FX_* codes to fixed strings, returning 'Unknown error in libssh2' for unmapped codes. sftp_libssh2_error_to_CURLE maps SFTP codes: OK to CURLE_OK, missing file/path to CURLE_REMOTE_FILE_NOT_FOUND, permission/write-protect/lock to CURLE_REMOTE_ACCESS_DENIED, disk-full/quota to CURLE_REMOTE_DISK_FULL, exists to CURLE_REMOTE_FILE_EXISTS, dir-not-empty to CURLE_QUOTE_ERROR, anything else to CURLE_SSH. libssh2_session_error_to_CURLE maps session-level codes: NONE to CURLE_OK, SCP_PROTOCOL to CURLE_REMOTE_FILE_NOT_FOUND, SOCKET_NONE to CURLE_COULDNT_CONNECT, ALLOC to CURLE_OUT_OF_MEMORY, SOCKET_SEND to CURLE_SEND_ERROR, hostkey/publickey errors to CURLE_PEER_FAILED_VERIFICATION, PASSWORD_EXPIRED to CURLE_LOGIN_DENIED, socket/timeout to CURLE_OPERATION_TIMEDOUT, EAGAIN to CURLE_AGAIN, default CURLE_SSH.

<a id="u-19176ee84c57"></a>
### `libssh2-key-callbacks`

`static void kbd_callback(const char *name, int name_len, const char *instruction, int…` · [lib/vssh/libssh2.c:L127-L157][f1]

Callback helpers for host keys and keyboard-interactive auth.

kbd_callback is the keyboard-interactive prompt handler: with exactly one prompt it strdup()s the connection's password into responses[0].text (memory libssh2 frees via the LIBSSH2_FREE_FUNC callback), setting length 0 on allocation failure; other prompt counts leave responses untouched. sshkeycallback is the default known-hosts verdict: it accepts only a perfect match (CURLKHMATCH_OK returns CURLKHSTAT_FINE), rejecting everything else. convert_ssh2_keytype maps libssh2 host key types to curl_khtype, collapsing all ECDSA curve variants to CURLKHTYPE_ECDSA; DSS, ECDSA and ED25519 cases are compiled only when the corresponding LIBSSH2_HOSTKEY_TYPE_* macros exist; unknown types yield CURLKHTYPE_UNKNOWN.

<a id="u-47c73781997f"></a>
### `libssh2-mem-dtors`

`static void myssh_easy_dtor(const void *key, size_t klen, void *entry)` · [lib/vssh/libssh2.c:L3249-L3258][f1]

Metadata destructors registered with the connection/easy metadata stores.

myssh_easy_dtor frees the SSHPROTO path, both dynamic buffers and the struct itself. myssh_conn_dtor runs sshc_cleanup in blocking mode (data=NULL, so failures are silent) and frees the ssh_conn struct.

calls: [lib/vssh/libssh2.c:sshc_cleanup](r13-ssh-libssh2.md#u-9c02038aded2)

<a id="u-34f38efec289"></a>
### `libssh2-memory-callbacks`

`static LIBSSH2_ALLOC_FUNC(my_libssh2_malloc)` · [lib/vssh/libssh2.c:L236-L240][f1]

Custom allocator callbacks handed to libssh2 so its memory comes from the libcurl allocator rather than debugmem, so libssh2's own leaks are not attributed to curl.

my_libssh2_malloc forwards to Curl_cmalloc, my_libssh2_realloc to Curl_crealloc; my_libssh2_free skips a NULL pointer because the ssh agent can invoke free with NULL, otherwise calls Curl_cfree. All ignore the abstract argument.

<a id="u-1e8e76ac5a49"></a>
### `libssh2-quote-parsing`

`static CURLcode quote_error(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh2.c:L775-L782][f1]

Parses one SFTP quote command from the command list.

Both accept a leading '*' to mark the command as allowed to fail (sshc->acceptfail=TRUE). quote_error is a shared failure helper: logs 'Suspicious data after the command line', frees both quote paths, returns CURLE_QUOTE_ERROR. sftp_quote handles 'pwd' by formatting an FTP-style 257 response with the current path and writing it to the header callback (allocation failure returns CURLE_OUT_OF_MEMORY), then advancing to SSH_SFTP_NEXT_QUOTE. Every other supported command must have a space-separated first argument, parsed with Curl_get_pathname into quote_path1 (parse failure fails with a syntax error, except OUT_OF_MEMORY which propagates unsaid). chgrp/chmod/chown/atime/mtime also parse quote_path2 and go to SSH_SFTP_QUOTE_STAT; ln/symlink and rename parse quote_path2 and go to QUOTE_SYMLINK / QUOTE_RENAME; mkdir, rmdir, rm and statvfs take only path1 and dispatch to their states. Any trailing text after the expected arguments, or an unrecognized command, frees both paths and returns CURLE_QUOTE_ERROR.

calls: [libssh2-quote-parsing](r13-ssh-libssh2.md#u-1e8e76ac5a49)

<a id="u-71ec22bbbf0c"></a>
### `libssh2-scp-ops`

`static CURLcode scp_perform(struct Curl_easy *data, bool *connected, bool *dophase_done)` · [lib/vssh/libssh2.c:L3542-L3568][f1]

SCP DO-phase, data transfer, done and disconnect entry points.

scp_perform starts the DO phase at SSH_SCP_TRANS_INIT and runs the non-blocking state machine (missing metadata: CURLE_FAILED_INIT), reporting connected state and dophase_done. scp_doing resumes that machine. scp_send/scp_recv wrap libssh2_channel_write/read: EAGAIN sets wait directions via ssh_block2waitfor and returns CURLE_AGAIN; negative results map through libssh2_session_error_to_CURLE; otherwise the byte count is reported. ssh_done is the shared done path: with a success status it runs the blocking state machine to finish the phase (otherwise the incoming status wins), then reports progress completion (CURLE_ABORTED_BY_CALLBACK if the callback aborts) and clears request I/O. scp_done first moves to SSH_SCP_DONE when the status is clean, then calls ssh_done. scp_disconnect, when a session still exists, enters SSH_SESSION_DISCONNECT and runs the blocking machine with disconnect semantics (one-second cap), then always runs sshc_cleanup blocking and returns its result.

calls: [libssh2-statemach-drivers](r13-ssh-libssh2.md#u-174e17ed09e1), [lib/vssh/libssh2.c:sshc_cleanup](r13-ssh-libssh2.md#u-9c02038aded2)

<a id="u-aa3573289a11"></a>
### `libssh2-scp-states`

`static CURLcode ssh_state_scp_download_init(struct Curl_easy *data, struct ssh_conn *…` · [lib/vssh/libssh2.c:L2249-L2294][f1]

SCP transfer state handlers; all return CURLE_AGAIN on libssh2 EAGAIN.

ssh_state_scp_download_init opens the remote file with libssh2_scp_recv2 into a zeroed stat; failure after EAGAIN logs the session error string, frees the channel state (SSH_SCP_CHANNEL_FREE) and returns the mapped session error. Success sets maxdownload from st_size, switches the transfer to receive on FIRSTSOCKET (send_idx=0) and stops. ssh_state_scp_upload_init first resolves the working path in ssh_state_scp_trans_init: upload requires a known infilesize or fails with CURLE_UPLOAD_FAILED via SSH_SCP_CHANNEL_FREE; then libssh2_scp_send64 opens the channel (mode and size from settings); failure maps the session error and additionally converts CURLE_SSH or CURLE_REMOTE_FILE_NOT_FOUND to CURLE_UPLOAD_FAILED; success sets sizes/progress, switches to send and stops. ssh_state_scp_done branches to SEND_EOF for uploads, else CHANNEL_FREE. ssh_state_scp_send_eof, wait_eof and wait_close perform the channel EOF/close handshake, logging (but not failing on) nonzero returns, and advance in sequence to WAIT_EOF, WAIT_CLOSE, CHANNEL_FREE. ssh_state_scp_channel_free frees the channel (EAGAIN defers; negative results only logged), then stops.

calls: [libssh2-error-mapping](r13-ssh-libssh2.md#u-6c67e4f87551)

<a id="u-8300c4be93dd"></a>
### `libssh2-session-states`

`static CURLcode ssh_state_init(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh2.c:L1411-L1428][f1]

Session setup and teardown states.

ssh_state_init resets secondCreateDirs and nextstate, puts libssh2 into non-blocking mode, then runs ssh_force_knownhost_key_type; failure transitions to SSH_SESSION_FREE, success to SSH_S_STARTUP. ssh_state_startup performs the session handshake on the primary socket: EAGAIN returns CURLE_AGAIN; failure logs the libssh2 error, frees the session state and returns CURLE_FAILED_INIT; success moves to SSH_HOSTKEY (handled by ssh_state_hostkey, which runs ssh_check_fingerprint and advances to SSH_AUTHLIST on success). ssh_state_session_disconnect frees any live channel (EAGAIN defers; negative results only logged), disconnects the session with reason 'Shutdown', frees the homedir, and moves to SSH_SESSION_FREE. ssh_state_session_free runs sshc_cleanup in non-blocking mode (propagating CURLE_AGAIN), zeroes the whole ssh_conn, marks the connection for closure, re-points state at SSH_SESSION_FREE and stops.

calls: [ssh_force_knownhost_key_type](r13-ssh-libssh2.md#u-5746f8bb2955), [ssh_check_fingerprint](r13-ssh-libssh2.md#u-a6ad2056daef), [lib/vssh/libssh2.c:sshc_cleanup](r13-ssh-libssh2.md#u-9c02038aded2)

<a id="u-e5221a2af09a"></a>
### `libssh2-sftp-ops`

`static CURLcode sftp_perform(struct Curl_easy *data, bool *connected, bool *dophase_d…` · [lib/vssh/libssh2.c:L3715-L3741][f1]

SFTP DO-phase, data transfer, done and disconnect entry points.

sftp_perform starts at SSH_SFTP_QUOTE_INIT (pre-quotes run before the transfer) and runs the non-blocking machine; sftp_doing resumes it. sftp_send/sftp_recv wrap libssh2_sftp_write/read on the open sftp handle: EAGAIN records wait directions and returns CURLE_AGAIN, negative results map through libssh2_session_error_to_CURLE, and success reports the byte count. sftp_done, on a clean status and no premature abort, schedules post-quotes by setting nextstate to SSH_SFTP_POSTQUOTE_INIT (skipped on retry connections) and enters SSH_SFTP_CLOSE, then defers to ssh_done. sftp_disconnect runs SSH_SFTP_SHUTDOWN through the blocking machine when a session remains (one-second disconnect cap) and always runs sshc_cleanup blocking, returning the shutdown machine's result.

calls: [libssh2-statemach-drivers](r13-ssh-libssh2.md#u-174e17ed09e1), [libssh2-scp-ops](r13-ssh-libssh2.md#u-71ec22bbbf0c)

**Uncertainties.**

- sftp_disconnect returns the ssh_block_statemach result, so a later sshc_cleanup failure cannot change the returned code; taken as written.

<a id="u-bfe085693a69"></a>
### `libssh2-sftp-states`

`static CURLcode ssh_state_sftp_init(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh2.c:L1759-L1779][f1]

SFTP session and transfer state handlers; each returns CURLE_AGAIN on libssh2 EAGAIN so the machine can be re-entered, and most failures route through SSH_SFTP_CLOSE (or SSH_SESSION_FREE) and map SFTP errors via sftp_libssh2_error_to_CURLE.

ssh_state_sftp_init creates the SFTP session; failure frees the session and returns CURLE_FAILED_INIT. ssh_state_sftp_realpath resolves '.' into the home directory, storing it in sshc->homedir and data->state.most_recent_ftp_entrypath (either strdup failure returns CURLE_OUT_OF_MEMORY); an error returns the mapped SFTP error or CURLE_SSH when the failure was not SFTP-level. ssh_state_sftp_quote_init resolves the working path (failure goes to SSH_STOP), then starts pre-quotes if configured or jumps to SSH_SFTP_GETINFO; missing easy metadata returns CURLE_FAILED_INIT. ssh_state_sftp_postquote_init starts post-quotes if set, else SSH_STOP. ssh_state_sftp_quote and ssh_state_sftp_quote_stat wrap sftp_quote and sftp_quote_stat, routing errors to SSH_SFTP_CLOSE and resetting nextstate. ssh_state_sftp_next_quote frees both quote paths and moves to the next quote command, or to the saved nextstate when set, else SSH_SFTP_GETINFO. The per-command states (setstat, symlink, mkdir, rename, rmdir, unlink, statvfs) run one libssh2 SFTP call with the parsed paths; on failure without acceptfail they log with the SFTP error text, free the quote paths, close, reset nextstate and return CURLE_QUOTE_ERROR; statvfs on success formats all fields into a header written via Curl_client_write (allocation or write failure closes; write failure returns the client-write error). ssh_state_sftp_getinfo branches to FILETIME when get_filetime is set, else TRANS_INIT. ssh_state_sftp_filetime stats the path and stores attrs.mtime in data->info.filetime on success, always continuing to TRANS_INIT. ssh_state_sftp_trans_init dispatches: upload to SSH_SFTP_UPLOAD_INIT; a path ending in '/' to READDIR_INIT; else DOWNLOAD_INIT; missing metadata is CURLE_FAILED_INIT. ssh_state_sftp_upload_init wraps sftp_upload_init, routing errors to SSH_SFTP_CLOSE and clearing nextstate. ssh_state_sftp_create_dirs_init sets slash_pos past the leading '/' (short paths go straight to UPLOAD_INIT); ssh_state_sftp_create_dirs finds the next '/' in the path, temporarily NUL-terminates there and issues SSH_SFTP_CREATE_DIRS_MKDIR, or goes to UPLOAD_INIT when done. ssh_state_sftp_create_dirs_mkdir mkdirs the truncated prefix, restores the slash and advances; failures are tolerated only for already-exists, generic FAILURE, or permission-denied, else close and return the mapped error. ssh_state_sftp_readdir_init sets unknown download size, short-circuits to SSH_STOP for no_body requests, opens the directory (failure maps the SFTP error after SSH_SFTP_CLOSE), else goes to SSH_SFTP_READDIR. ssh_state_sftp_readdir_link resolves the pending symlink target, appending ' -> target' to the listing buffer; EAGAIN defers; negative readlink returns CURLE_OUT_OF_MEMORY (as written); success continues to READDIR_BOTTOM or closes on buffer failure. ssh_state_sftp_readdir_bottom appends a newline, writes the buffered entry as body data, resets the buffer on success and re-enters READDIR; on error it frees the buffer and stops. ssh_state_sftp_readdir_done closes the directory handle (EAGAIN defers), sets up a nop transfer and stops. ssh_state_sftp_download_init opens the file read-only (EAGAIN defers; failure logs the SFTP error, closes and returns the mapped code), else proceeds to DOWNLOAD_STAT. ssh_state_sftp_download_stat wraps sftp_download_stat, routing errors to SSH_SFTP_CLOSE and clearing nextstate. ssh_state_sftp_close closes the open handle, frees sshp->path, then either runs the saved nextstate (setting nextstate to SSH_SFTP_CLOSE so control returns) or stops. ssh_state_sftp_shutdown closes any leftover handle, shuts down the SFTP session, frees the homedir and moves to SSH_SESSION_DISCONNECT.

calls: [libssh2-quote-parsing](r13-ssh-libssh2.md#u-1e8e76ac5a49), [sftp_quote_stat](r13-ssh-libssh2.md#u-7983b8d73cd0), [sftp_upload_init](r13-ssh-libssh2.md#u-c44a198cd17d), [sftp_download_stat](r13-ssh-libssh2.md#u-c576e6b2543f), [sftp_readdir](r13-ssh-libssh2.md#u-dba956aff80d), [libssh2-error-mapping](r13-ssh-libssh2.md#u-6c67e4f87551)

**Uncertainties.**

- ssh_state_sftp_readdir_link maps a negative symlink read to CURLE_OUT_OF_MEMORY, which may conflate remote errors with allocation failure; that mapping is taken as written.

<a id="u-174e17ed09e1"></a>
### `libssh2-statemach-drivers`

`static void ssh_block2waitfor(struct Curl_easy *data, struct ssh_conn *sshc, bool block)` · [lib/vssh/libssh2.c:L3155-L3172][f1]

Drivers around the state machine.

ssh_block2waitfor translates libssh2's block-direction bits into sshc->waitfor (REQ_IO_RECV/REQ_IO_SEND) when block is set; if no direction is known or block is false it clears waitfor so default wait bits are restored. ssh_multi_statemach (non-blocking, multi interface) loops ssh_statemachine until an error, SSH_STOP, or a block; it requires both connection and easy metadata or returns CURLE_FAILED_INIT, then records wait directions. ssh_block_statemach (blocking, used for DO completion and disconnect) loops until SSH_STOP or error; unless disconnecting it checks progress and the operation time limit (timeout returns CURLE_OPERATION_TIMEDOUT); when disconnecting it gives up silently after one second with CURLE_OK. While blocked it polls the primary socket for the directions libssh2 requests, capped at one second per wait.

calls: [ssh_statemachine](r13-ssh-libssh2.md#u-cdca991e9300)

<a id="u-b969eb76ef91"></a>
### `libssh2-tls-proxy-io`

`static ssize_t ssh_tls_recv(libssh2_socket_t sock, void *buffer, size_t length, int f…` · [lib/vssh/libssh2.c:L3302-L3328][f1]

libssh2 recv/send callbacks used when the SSH session runs through an HTTPS proxy; absent when proxy support is disabled.

Each resolves the easy handle from *abstract, finds the socket index, and temporarily swaps the connection's recv/send function for the stored TLS-layer function (sshc->tls_recv/tls_send) for the duration of one Curl_conn_recv/Curl_conn_send call, restoring the SSH function afterwards. CURLE_AGAIN maps to -EAGAIN (libssh2's retry signal), any other error to -1, and success logs the transferred data via Curl_debug and returns the byte count. A missing ssh_conn metadata yields -1.

<a id="u-c576e6b2543f"></a>
### `sftp_download_stat`

`static CURLcode sftp_download_stat(struct Curl_easy *data, struct ssh_conn *sshc, str…` · [lib/vssh/libssh2.c:L1257-L1350][f1]

Stats the remote file for an SFTP download and computes the transfer size.

EAGAIN defers via *blockp. If the stat fails, lacks the SIZE attribute, or reports size 0, the size is treated as unknown (-1) and download proceeds unbounded. A negative file size returns CURLE_BAD_DOWNLOAD_RESUME. With a range configured, Curl_ssh_range splits it into start and end, and the SFTP handle is seeked to the start. Resume handling: negative resume_from means last N bytes and is converted relative to the file size; an offset beyond the file size returns CURLE_BAD_DOWNLOAD_RESUME in both forms; the remaining byte count is stored in data->req.size/maxdownload and the handle seeked. If the computed size is zero, the transfer is set to nop and it goes to SSH_STOP (file already complete); otherwise the transfer is set to receive on FIRSTSOCKET and it moves to SSH_STOP.

uses: [libssh2-error-mapping](r13-ssh-libssh2.md#u-6c67e4f87551)

**Uncertainties.**

- Curl_ssh_range's exact split semantics are external to this file.

<a id="u-7983b8d73cd0"></a>
### `sftp_quote_stat`

`static CURLcode sftp_quote_stat(struct Curl_easy *data, struct ssh_conn *sshc, struct…` · [lib/vssh/libssh2.c:L1146-L1255][f1]

Builds the attribute set for a chgrp/chmod/chown/atime/mtime quote command before SETSTAT.

A leading '*' sets acceptfail. For anything other than chmod it first stats quote_path2 to obtain current ownership (libssh2 sets owner and group together); EAGAIN defers via *blockp, and a stat failure fails unless acceptfail. chmod parses quote_path1 as octal up to 07777 (any parse failure goes to fail); chgrp/chown parse a decimal id (parse failure tolerated only under acceptfail); atime/mtime parse a date via Curl_getdate_capped, additionally rejecting dates above 0xffffffff when time_t is larger than long. On success it fills sshp->quote_attrs and dispatches to SSH_SFTP_QUOTE_SETSTAT. The fail path frees both quote paths and returns CURLE_QUOTE_ERROR.

**Notes.**

- failure: Date parse errors and the 32-bit overflow are fatal even when the command is marked acceptable, unlike remote-side setstat failures.

<a id="u-dba956aff80d"></a>
### `sftp_readdir`

`static CURLcode sftp_readdir(struct Curl_easy *data, struct ssh_conn *sshc, struct SS…` · [lib/vssh/libssh2.c:L1352-L1409][f1]

Reads one directory entry for an SFTP directory listing.

EAGAIN defers via *blockp. A positive return NUL-terminates the filename; in list_only mode it writes the filename plus a newline as body data and returns on write failure. Otherwise it accumulates the longentry into sshp->readdir; when permissions indicate a symlink it appends path+filename to readdir_link and moves to SSH_SFTP_READDIR_LINK, else to SSH_SFTP_READDIR_BOTTOM. A zero return means end of listing and moves to SSH_SFTP_READDIR_DONE. A negative return maps the SFTP error (CURLE_SSH when the SFTP error is zero), logs a failure, and transitions to SSH_SFTP_CLOSE.

**Notes.**

- failure: The negative-return failure message text ('Could not open remote file for reading') is reused from download despite this being a directory read.

<a id="u-c44a198cd17d"></a>
### `sftp_upload_init`

`static CURLcode sftp_upload_init(struct Curl_easy *data, struct ssh_conn *sshc, struc…` · [lib/vssh/libssh2.c:L944-L1125][f1]

Opens the remote file for SFTP upload and prepares the send transfer.

With a negative resume_from it stats the remote file and uses its size as the resume offset (a bad/negative size returns CURLE_BAD_DOWNLOAD_RESUME); a stat EAGAIN sets *blockp and defers. Flags: remote_append creates with WRITE|CREAT|APPEND; resume_from>0 uses plain WRITE (never APPEND, since some servers force EOF writes); otherwise WRITE|CREAT|TRUNC. On open failure: EAGAIN defers via *blockp; the SFTP error is read only when the session errno is LIBSSH2_ERROR_SFTP_PROTOCOL. If missing-file-like errors coincide with ftp_create_missing_dirs and a path longer than '/', it retries once via SSH_SFTP_CREATE_DIRS_INIT (secondCreateDirs); after that retry fails, or otherwise, it goes to SSH_SFTP_CLOSE and returns the mapped SFTP error, substituting CURLE_SSH when the mapped code is zero because libssh2 sometimes reports a zero SFTP error. With resume_from>0 and no explicit append, it seeks the input: user seek_func failure other than CANTSEEK returns CURLE_FTP_COULDNT_USE_REST; CANTSEEK triggers a manual read-and-discard loop (read abort or short read also fails the transfer). It then shrinks infilesize, seeks the SFTP handle, sets request size/progress, switches the transfer to send on FIRSTSOCKET, marks the multi dirty and moves to SSH_STOP.

**Notes.**

- side_effect: Adjusts data->state.infilesize, data->req.size, progress and conn->recv_idx, and seeks both the input stream and the SFTP handle when resuming.

<a id="u-a6ad2056daef"></a>
### `ssh_check_fingerprint`

`static CURLcode ssh_check_fingerprint(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh2.c:L481-L628][f1]

Verifies the host key against user-configured MD5/SHA256 fingerprints or a callback, falling back to known-hosts.

If a SHA256 fingerprint is configured: it takes the 32-byte SHA256 hostkey hash (static storage, not freed), base64-encodes it, and compares both strings up to (excluding) any '=' padding; any length or content mismatch — or a missing hash or encode failure — frees the session and returns CURLE_PEER_FAILED_VERIFICATION. The MD5 path formats the 16-byte hash as 32 hex chars and requires a case-insensitive exact match with the configured string, so the configured value must be exactly 32 characters or verification fails; missing hash or mismatch again frees the session and fails. When neither fingerprint is set: a user hostkey callback receives the raw key and must return CURLKHMATCH_OK or verification fails; with no callback the check delegates to ssh_knownhost(). When any fingerprint matched, the known-hosts check is skipped entirely and CURLE_OK returned.

calls: [ssh_knownhost](r13-ssh-libssh2.md#u-ac5fe69eb50a), [libssh2-key-callbacks](r13-ssh-libssh2.md#u-19176ee84c57)

<a id="u-98134158c6c6"></a>
### `ssh_connect`

`static CURLcode ssh_connect(struct Curl_easy *data, bool *done)` · [lib/vssh/libssh2.c:L3363-L3461][f1]

Entry point for establishing the SSH session, called from protocol connect.

Logs the crypto backend for libssh2 >= 1.11 and the username; missing connection metadata returns CURLE_FAILED_INIT. It creates the libssh2 session with the custom curl allocators (mandatory so kbd_callback allocations can be freed), failing with CURLE_FAILED_INIT. A configured server_response_timeout sets the libssh2 packet read timeout on libssh2 >= 1.11. For an HTTPS proxy (when proxies are enabled) it installs ssh_tls_recv/ssh_tls_send as libssh2 callbacks — via callback_set2 on libssh2 >= 1.1b01, otherwise via a union-based cast around callback_set — and stores the underlying TLS recv/send pointers. Channel recv/send are then set to scp or sftp variants per protocol. Compression is requested when configured (failure only logged). When a knownhosts file is configured, the knownhost store is initialized (failure frees the session and returns CURLE_FAILED_INIT) and the file is read in OpenSSH format; a read failure is only logged. Finally it transitions to SSH_INIT and runs ssh_multi_statemach, propagating its result.

calls: [libssh2-statemach-drivers](r13-ssh-libssh2.md#u-174e17ed09e1); uses: [libssh2-memory-callbacks](r13-ssh-libssh2.md#u-34f38efec289), [libssh2-tls-proxy-io](r13-ssh-libssh2.md#u-b969eb76ef91)

<a id="u-5746f8bb2955"></a>
### `ssh_force_knownhost_key_type`

`static CURLcode ssh_force_knownhost_key_type(struct Curl_easy *data, struct ssh_conn …` · [lib/vssh/libssh2.c:L634-L773][f1]

Scans the loaded known-hosts entries for the target host and, if found, pins the libssh2 hostkey method to the algorithm of the stored key so the server must offer a compatible key.

It only runs when a knownhosts handle exists and no MD5/SHA256 fingerprint is configured. Host matching: entries named '[host]:port' are parsed with curlx_str_number and matched when the port equals the origin port and the bracketed name matches; plain entries match by strcmp. Nameless entries use their key blob with checkp, and a per-key-type 'absent_type' cache skips re-scanning a type already proven absent. RSA1 or unknown key types fail with CURLE_SSH. On a found entry it maps the stored type to a method string (ED25519, ECDSA 256/384/521, rsa-sha2-256,rsa-sha2-512,ssh-rsa, or ssh-dss when defined) and calls libssh2_session_method_pref; a nonzero return is logged with libssh2_session_last_error and translated via libssh2_session_error_to_CURLE. No match found returns CURLE_OK.

calls: [libssh2-error-mapping](r13-ssh-libssh2.md#u-6c67e4f87551)

<a id="u-ac5fe69eb50a"></a>
### `ssh_knownhost`

`static CURLcode ssh_knownhost(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh2.c:L306-L479][f1]

Performs the known-hosts verification of the remote SSH host key.

If no knownhosts file is configured it succeeds without checking. Otherwise it fetches the session host key; a missing key is rejected (SSH_SESSION_FREE, CURLE_PEER_FAILED_VERIFICATION). For an unsupported key type it rejects outright. It runs libssh2_knownhost_checkp against the origin hostname, using port -1 for the default SSH port; the check result enum is cast directly to curl_khmatch and passed to the user's key callback (or sshkeycallback). Callback verdicts: REJECT or unknown codes free the session and return CURLE_PEER_FAILED_VERIFICATION; DEFER returns the same code but keeps the SSH_HOSTKEY state; FINE/FINE_ADD_TO_FILE/FINE_REPLACE proceed and, if the key was not an exact match, add it in memory via libssh2_knownhost_addc (host:port in brackets for non-default ports), writing the whole in-memory set to the known_hosts file for ADD_TO_FILE/REPLACE; allocation or write failures only log warnings, they do not fail the transfer.

calls: [libssh2-key-callbacks](r13-ssh-libssh2.md#u-19176ee84c57); uses: [libssh2-key-callbacks](r13-ssh-libssh2.md#u-19176ee84c57)

**Uncertainties.**

- The CURLKHSTAT_DEFER path leaves sshc->state unchanged here; which state the machine revisits depends on the caller.

<a id="u-450e4d2396a4"></a>
### `ssh_setup_connection`

`static CURLcode ssh_setup_connection(struct Curl_easy *data, struct connectdata *conn)` · [lib/vssh/libssh2.c:L3272-L3296][f1]

Allocates and attaches the per-connection ssh_conn and per-easy SSHPROTO metadata, then loads key settings.

Any allocation or metadata-registration failure returns CURLE_OUT_OF_MEMORY. The readdir buffers are initialized to CURL_PATH_MAX*2 and CURL_PATH_MAX. Ends by delegating to Curl_ssh_setup_pkey for public/private key configuration.

uses: [libssh2-mem-dtors](r13-ssh-libssh2.md#u-47c73781997f)

**Uncertainties.**

- If Curl_conn_meta_set succeeds but a later step fails, the already-registered metadata and its destructor own cleanup; the exact double-free safety is not provable from this file.

<a id="u-cdca991e9300"></a>
### `ssh_statemachine`

`static CURLcode ssh_statemachine(struct Curl_easy *data, struct ssh_conn *sshc, struc…` · [lib/vssh/libssh2.c:L2889-L3146][f1]

Runs the SSH connection/transfer state machine as far as possible without blocking.

Each iteration dispatches on sshc->state to the matching ssh_state_* handler; SSH_INIT and SSH_S_STARTUP fall through to the next state on success, and SSH_QUIT or an unknown state simply stops. The do/while continues while there is no error, the state is not SSH_STOP, and the handler did not request blocking via *block. A CURLE_AGAIN result is converted to *block=TRUE with CURLE_OK returned, so callers just wait for socket readiness. Errors other than AGAIN propagate unchanged and end the loop.

calls: [libssh2-session-states](r13-ssh-libssh2.md#u-8300c4be93dd), [libssh2-auth-states](r13-ssh-libssh2.md#u-fb2673af056b), [libssh2-sftp-states](r13-ssh-libssh2.md#u-bfe085693a69), [libssh2-scp-states](r13-ssh-libssh2.md#u-aa3573289a11)

<a id="u-9c02038aded2"></a>
### `lib/vssh/libssh2.c:sshc_cleanup`

`static CURLcode sshc_cleanup(struct ssh_conn *sshc, struct Curl_easy *data, bool block)` · [lib/vssh/libssh2.c:L2487-L2585][f1]

Tears down all libssh2 objects held by the connection, in order: knownhost store, agent (disconnect then free, clearing identity pointers), sftp handle, channel, sftp session, ssh session.

With block=FALSE, any EAGAIN from agent disconnect, sftp close, channel free, sftp shutdown or session free is returned as CURLE_AGAIN leaving the object in place for a retry; with block=TRUE (or after non-EAGAIN results) each object is released and NULLed. Negative results are logged via infof when data is non-NULL. Debug assertions then verify everything is released, and passphrase, key paths, quote paths and homedir are freed. Always ends with CURLE_OK once nothing blocks.

**Notes.**

- contract: Callers must treat CURLE_AGAIN as 'not yet torn down' and re-enter; with block=TRUE the function cannot return EAGAIN.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vssh/libssh2.c
