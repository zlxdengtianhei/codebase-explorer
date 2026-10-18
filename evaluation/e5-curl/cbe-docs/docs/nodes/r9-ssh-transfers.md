# SFTP and SCP transfer states

**Capability.** The DO-phase state machine for SFTP and SCP: working-path resolution, SFTP init/realpath, upload (with directory creation), download (with fstat), directory listing, filetime, mode dispatch (SSH_SFTP_TRANS_INIT), SCP channel states, plus the protocol entry points (myssh_do_it, done, doing, disconnect) and data callbacks sftp_send/recv and scp_send/recv.

Use this child to follow a transfer from QUOTE_INIT through TRANS_INIT to completion and teardown (SFTP_CLOSE/SHUTDOWN, CHANNEL_FREE). Error transitions route via myssh_to_ERROR and myssh_to_SFTP_CLOSE with sftp_error_to_CURLE mapping.

**Depends on.**

- [SSH connection, auth and lifecycle](r9-ssh-conn-auth.md) · model-inferred · 0 edge(s)
- [SFTP quote commands](r9-ssh-quotes.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [SSH connection, auth and lifecycle](r9-ssh-conn-auth.md) · model-inferred · 0 edge(s)
- [SFTP quote commands](r9-ssh-quotes.md) · model-inferred · 0 edge(s)

Parent: [SSH backend \(libssh\)](r9-ssh-backend.md)

## Units (55)

<a id="u-c02b9d98131a"></a>
### `myssh_SSH_SCP_DOWNLOAD`

`static int myssh_SSH_SCP_DOWNLOAD(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L1810-L1831][f1]

Handles an SCP download request: ssh_scp_pull_request must return SSH_SCP_REQUEST_NEWFILE, otherwise the libssh error is logged and the machine fails with CURLE_REMOTE_FILE_NOT_FOUND.

On success the request size becomes req.maxdownload, the transfer enters recv mode for that byte count with send_idx 0, and the machine stops awaiting data.

<a id="u-27de83a3985b"></a>
### `myssh_do_it`

`static CURLcode myssh_do_it(struct Curl_easy *data, bool *done)` · [lib/vssh/libssh.c:L3089-L3114][f1]

Shared DO entry for SCP and SFTP.

Fails with CURLE_FAILED_INIT without ssh_conn metadata; resets req.size to unknown, clears actualcode and secondCreateDirs, resets progress, then dispatches to scp_perform or sftp_perform based on the connection protocol. Result and done flag pass through.

<a id="u-5c7de3d996ac"></a>
### `myssh_done`

`static CURLcode myssh_done(struct Curl_easy *data, struct ssh_conn *sshc, CURLcode st…` · [lib/vssh/libssh.c:L2751-L2770][f1]

Shared done handler for SCP and SFTP.

When the incoming status is OK and SSHPROTO metadata exists, it runs myssh_block_statemach (with progress/timeout checks) to finish remaining states (e.g. quotes, channel close); otherwise the status becomes the result. Then it reports progress completion (abort maps to CURLE_ABORTED_BY_CALLBACK) and clears the request's pending I/O flags before returning the result.

<a id="u-9043139911cb"></a>
### `myssh_in_SCP_CHANNEL_FREE`

`static int myssh_in_SCP_CHANNEL_FREE(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L2220-L2233][f1]

Frees the scp_session (nulled after), traces phase completion, restores non-blocking mode on the SSH session, and transitions to SSH_SESSION_DISCONNECT.

<a id="u-50663ebeaed6"></a>
### `myssh_in_SCP_DONE`

`static int myssh_in_SCP_DONE(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L2188-L2196][f1]

SCP completion routing: uploads go to SSH_SCP_SEND_EOF to close the channel properly, downloads go directly to SSH_SCP_CHANNEL_FREE.

<a id="u-5bbdf8568200"></a>
### `myssh_in_SCP_DOWNLOAD_INIT`

`static int myssh_in_SCP_DOWNLOAD_INIT(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L2174-L2186][f1]

Prepares an SCP download: ssh_scp_init failure logs and fails with CURLE_COULDNT_CONNECT; success advances to SSH_SCP_DOWNLOAD to await the pull request.

<a id="u-7dcaff8a2272"></a>
### `myssh_in_SCP_SEND_EOF`

`static int myssh_in_SCP_SEND_EOF(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L2198-L2218][f1]

Signals end-of-file on an SCP upload by ssh_scp_close.

SSH_AGAIN returns for retry (the comment notes the underlying wait is blocking); a non-OK close is logged as info but not fatal. Then the machine moves to SSH_SCP_CHANNEL_FREE. A NULL scp_session skips the close entirely.

<a id="u-28170886049b"></a>
### `myssh_in_SCP_UPLOAD_INIT`

`static int myssh_in_SCP_UPLOAD_INIT(struct Curl_easy *data, struct ssh_conn *sshc, st…` · [lib/vssh/libssh.c:L2139-L2172][f1]

Prepares an SCP upload: ssh_scp_init failure or ssh_scp_push_file64 failure (path, infilesize, new_file_perms) logs the libssh error and fails with CURLE_UPLOAD_FAILED.

Success switches the transfer to send mode with recv on the first socket and stops the machine to await data. Missing SSHPROTO fails.

<a id="u-a2ba4990e623"></a>
### `myssh_in_SFTP_CLOSE`

`static int myssh_in_SFTP_CLOSE(struct Curl_easy *data, struct ssh_conn *sshc, struct …` · [lib/vssh/libssh.c:L1297-L1323][f1]

Post-transfer SFTP cleanup: closes and clears sftp_file, frees sshp->path, and either jumps to a pending nextstate (when set and not SSH_SFTP_CLOSE itself, leaving nextstate as SSH_SFTP_CLOSE so control returns) or stops the machine.

Missing SSHPROTO fails first.

<a id="u-43cad98eace9"></a>
### `myssh_in_SFTP_CREATE_DIRS`

`static int myssh_in_SFTP_CREATE_DIRS(struct Curl_easy *data, struct ssh_conn *sshc, s…` · [lib/vssh/libssh.c:L2085-L2102][f1]

Advances to the next '/' in the path from slash_pos.

If found, the path is temporarily truncated there, the intermediate directory is announced, and the machine enters SSH_SFTP_CREATE_DIRS_MKDIR; when no separator remains all directories exist and the machine proceeds to SSH_SFTP_UPLOAD_INIT. Missing SSHPROTO fails.

<a id="u-cc5f638eac7a"></a>
### `myssh_in_SFTP_CREATE_DIRS_INIT`

`static int myssh_in_SFTP_CREATE_DIRS_INIT(struct Curl_easy *data, struct ssh_conn *ss…` · [lib/vssh/libssh.c:L2068-L2083][f1]

Begins remote directory creation for an upload: if the path is longer than the leading '/', slash_pos starts after it and the machine enters SSH_SFTP_CREATE_DIRS; a bare '/' path skips straight to SSH_SFTP_UPLOAD_INIT.

Missing SSHPROTO fails.

<a id="u-1b37e879cc5b"></a>
### `myssh_in_SFTP_CREATE_DIRS_MKDIR`

`static int myssh_in_SFTP_CREATE_DIRS_MKDIR(struct Curl_easy *data, struct ssh_conn *s…` · [lib/vssh/libssh.c:L2104-L2137][f1]

Creates one intermediate directory from the truncated path with new_directory_perms.

SSH_AGAIN returns for retry. Afterwards the separator is restored and slash_pos advances regardless of outcome. A failed mkdir is tolerated when the error is FILE_ALREADY_EXISTS, unspecific FAILURE, or PERMISSION_DENIED (later segments may still succeed); any other error routes to myssh_to_SFTP_CLOSE. Success or tolerated failure continues to SSH_SFTP_CREATE_DIRS. Missing SSHPROTO fails.

<a id="u-478f85731fda"></a>
### `myssh_in_SFTP_DOWNLOAD_INIT`

`static int myssh_in_SFTP_DOWNLOAD_INIT(struct Curl_easy *data, struct ssh_conn *sshc,…` · [lib/vssh/libssh.c:L1178-L1199][f1]

Opens the remote file read-only for download.

Missing SSHPROTO fails; any previous sftp_file is closed first. sftp_open failure logs and routes to myssh_to_SFTP_CLOSE; success marks the file non-blocking and moves to SSH_SFTP_DOWNLOAD_STAT.

<a id="u-439989857f3c"></a>
### `myssh_in_SFTP_DOWNLOAD_STAT`

`static int myssh_in_SFTP_DOWNLOAD_STAT(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L1201-L1295][f1]

Determines download size via sftp_fstat.

If stat fails, size is absent, or size is 0, the transfer size stays unknown (-1) and size is treated as 0. A valid negative size fails with CURLE_BAD_DOWNLOAD_RESUME. With a range configured, Curl_ssh_range computes the start offset (errors propagate via myssh_to_ERROR) and sftp_seek64 seeks there (failure routes to SFTP_CLOSE). Resume handling: negative resume_from means last N bytes and is converted relative to size (offset beyond size fails); positive resume beyond size also fails; the remaining byte count becomes req.size/maxdownload and the file is seeked. If the final size is zero the transfer is a nop and the machine stops; otherwise it enters recv mode with sftp_recv_state reset.

<a id="u-1f5bf32ed515"></a>
### `myssh_in_SFTP_FILETIME`

`static int myssh_in_SFTP_FILETIME(struct Curl_easy *data, struct ssh_conn *sshc, stru…` · [lib/vssh/libssh.c:L2030-L2046][f1]

Fetches the remote file's modification time: stats sshp->path and, on success, stores attrs->mtime in data->info.filetime and frees the attributes; a stat failure is silently ignored.

Either way the machine moves to SSH_SFTP_TRANS_INIT. Missing SSHPROTO fails first.

<a id="u-d4df5fcd6128"></a>
### `myssh_in_SFTP_GETINFO`

`static int myssh_in_SFTP_GETINFO(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L2020-L2028][f1]

Routes after quotes: to SSH_SFTP_FILETIME when get_filetime is requested, otherwise directly to SSH_SFTP_TRANS_INIT.

<a id="u-bf9ce57150cb"></a>
### `myssh_in_SFTP_INIT`

`static int myssh_in_SFTP_INIT(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L1353-L1374][f1]

Initializes the SFTP subsystem, temporarily in blocking mode.

sftp_new failure fails with CURLE_COULDNT_CONNECT; sftp_init failure fails with the mapping of SSH_FX_FAILURE (CURLE_SSH). Success advances to SSH_SFTP_REALPATH.

<a id="u-d70dabd3e14c"></a>
### `myssh_in_SFTP_QUOTE_INIT`

`static int myssh_in_SFTP_QUOTE_INIT(struct Curl_easy *data, struct ssh_conn *sshc, st…` · [lib/vssh/libssh.c:L1398-L1420][f1]

Begins the SFTP DO phase: resolves the working path with Curl_getworkingpath (failure stores the code and stops the machine).

If pre-quote commands exist, quote_item points at them and the machine enters SSH_SFTP_QUOTE; otherwise it moves to SSH_SFTP_GETINFO. Missing SSHPROTO fails.

<a id="u-f7b3d12caf76"></a>
### `myssh_in_SFTP_READDIR`

`static int myssh_in_SFTP_READDIR(struct Curl_easy *data, struct ssh_conn *sshc, struc…` · [lib/vssh/libssh.c:L449-L521][f1]

Reads one directory entry per invocation.

It resets readdir_buf, frees the previous attributes, then calls sftp_readdir. With an entry: in list-only mode it writes just the filename plus newline to the client body (memory failure routes to SSH_SFTP_CLOSE with CURLE_OUT_OF_MEMORY; a client-write failure stops the machine with actualcode set); otherwise it appends the long entry to readdir_buf, and if permissions indicate a symlink (SSH_S_IFMT/SSH_S_IFLNK) it builds readdir_linkPath from path+name and moves to SSH_SFTP_READDIR_LINK, else to READDIR_BOTTOM. Without an entry, end-of-directory moves to READDIR_DONE while a real read error logs and goes to myssh_to_SFTP_CLOSE.

<a id="u-03ee3c47bdb6"></a>
### `myssh_in_SFTP_READDIR_BOTTOM`

`static int myssh_in_SFTP_READDIR_BOTTOM(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L577-L599][f1]

Finishes one listing line: appends a newline to readdir_buf (failure yields CURLE_OUT_OF_MEMORY) then writes the buffer to the client body.

Frees readdir_tmp. On write failure the machine stops with actualcode set; on success it loops back to SSH_SFTP_READDIR for the next entry.

<a id="u-bdc266e54ea6"></a>
### `myssh_in_SFTP_READDIR_DONE`

`static int myssh_in_SFTP_READDIR_DONE(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L601-L611][f1]

Ends a directory listing: closes the sftp_dir handle, clears it, sets the transfer to a nop since no data remains, and stops the state machine.

<a id="u-7c74647c4b8b"></a>
### `myssh_in_SFTP_READDIR_INIT`

`static int myssh_in_SFTP_READDIR_INIT(struct Curl_easy *data, struct ssh_conn *sshc, …` · [lib/vssh/libssh.c:L422-L447][f1]

Starts an SFTP directory listing.

A missing SSHPROTO fails with CURLE_FAILED_INIT. Download size is set unknown; if the transfer has no body the machine stops immediately. Otherwise sftp_opendir opens sshp->path; failure logs and routes to myssh_to_SFTP_CLOSE, success moves to SSH_SFTP_READDIR.

calls: [myssh_to_SFTP_CLOSE](r9-ssh-transfers.md#u-a6ec95216494)

<a id="u-a25760c20765"></a>
### `myssh_in_SFTP_READDIR_LINK`

`static int myssh_in_SFTP_READDIR_LINK(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L523-L575][f1]

Resolves a symlink found during directory listing.

It lstats readdir_linkPath; stat failure routes to myssh_to_SFTP_CLOSE. If the lstat result has no name it sftp_readlink's the target (readdir_len 0 on failure) and uses that string, else uses the lstat name/longname. It then appends ' -> <target>' to readdir_buf; a dyn_add failure explicitly sets actualcode CURLE_OUT_OF_MEMORY (not an SFTP error, per the in-code comment) and returns SSH_ERROR. Attribute temporaries are freed and the machine moves to READDIR_BOTTOM.

<a id="u-026e3bdaab4f"></a>
### `myssh_in_SFTP_REALPATH`

`static int myssh_in_SFTP_REALPATH(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L1376-L1396][f1]

Fetches the home directory by canonicalizing '.'.

Failure fails with CURLE_COULDNT_CONNECT. The homedir is duplicated into data->state.most_recent_ftp_entrypath (out-of-memory fails via CURLE_OUT_OF_MEMORY, after freeing the previous entry path) and the machine stops, completing the SFTP connect phase.

<a id="u-79dd9b6cbb56"></a>
### `myssh_in_SFTP_SHUTDOWN`

`static int myssh_in_SFTP_SHUTDOWN(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L1325-L1351][f1]

SFTP teardown used during disconnect: re-asserts non-blocking mode, frees any AIO objects on libssh > 0.11, closes the sftp_file and frees the sftp_session (each nulled after release), frees homedir, and transitions to SSH_SESSION_DISCONNECT.

<a id="u-ff696b18bdcf"></a>
### `myssh_in_SFTP_TRANS_INIT`

`static int myssh_in_SFTP_TRANS_INIT(struct Curl_easy *data, struct ssh_conn *sshc, st…` · [lib/vssh/libssh.c:L2048-L2066][f1]

Chooses the SFTP transfer mode: upload goes to SSH_SFTP_UPLOAD_INIT; otherwise a path ending in '/' selects directory listing (SSH_SFTP_READDIR_INIT) and anything else download (SSH_SFTP_DOWNLOAD_INIT).

Missing SSHPROTO fails.

<a id="u-b1a92a48ba55"></a>
### `myssh_in_TRANS_INIT`

`static int myssh_in_TRANS_INIT(struct Curl_easy *data, struct ssh_conn *sshc, struct …` · [lib/vssh/libssh.c:L1833-L1873][f1]

SCP DO-phase entry.

Missing SSHPROTO fails; working path resolution failure stops the machine with the error stored. The session is switched to blocking because SCP calls cannot return SSH_AGAIN. Upload requires a known infilesize (else CURLE_UPLOAD_FAILED) and creates an SSH_SCP_WRITE session moving to SCP_UPLOAD_INIT; download creates SSH_SCP_READ moving to SCP_DOWNLOAD_INIT. A NULL scp_session after ssh_scp_new fails with CURLE_UPLOAD_FAILED.

<a id="u-ac006dec898f"></a>
### `myssh_in_UPLOAD_INIT`

`static int myssh_in_UPLOAD_INIT(struct Curl_easy *data, struct ssh_conn *sshc, struct…` · [lib/vssh/libssh.c:L1025-L1176][f1]

Opens the remote file for SFTP upload and prepares the data pump.

A missing SSHPROTO fails. Negative resume_from (resume based on remote size) stats the file and adopts its size, or resets to 0 if absent; a negative remote size fails with CURLE_BAD_DOWNLOAD_RESUME. Open flags: append mode uses O_WRONLY|O_CREAT|O_APPEND, positive resume uses plain O_WRONLY (deliberately not O_APPEND so a seek works), otherwise O_WRONLY|O_CREAT|O_TRUNC. Any pre-existing sftp_file is closed first. If sftp_open fails with NO_SUCH_FILE/FAILURE/NO_SUCH_PATH and create-missing-dirs is on and the path is long enough, the machine retries via SSH_SFTP_CREATE_DIRS_INIT; otherwise it fails via myssh_to_SFTP_CLOSE. With resume: the input stream is seeked (or manually read-through on CANTSEEK, failing with CURLE_FTP_COULDNT_USE_REST on hard seek errors or read shortfalls), infilesize is reduced and progress set (resume beyond size fails with CURLE_BAD_FUNCTION_ARGUMENT), and sftp_seek64 positions the remote file (failure routes to SFTP_CLOSE). Finally the transfer is set to send mode, marked dirty, and, on libssh > 0.11, sftp_send_state resets before stopping the machine.

**Notes.**

- side_effect: Closes any pre-existing sshc->sftp_file before reopening, and mutates data->state.resume_from and infilesize.

<a id="u-7e493036cd08"></a>
### `myssh_multi_statemach`

`static CURLcode myssh_multi_statemach(struct Curl_easy *data, bool *done)` · [lib/vssh/libssh.c:L2454-L2471][f1]

Non-blocking entry point called repeatedly by the multi interface.

It fetches the connection-level ssh_conn and easy-level SSHPROTO metadata (missing either yields CURLE_FAILED_INIT), runs myssh_statemachine once, reports done when the state reaches SSH_STOP, and translates the block flag into socket-wait directions via myssh_block2waitfor.

<a id="u-7758c83c29d2"></a>
### `myssh_statemachine`

`static CURLcode myssh_statemachine(struct Curl_easy *data, struct ssh_conn *sshc, str…` · [lib/vssh/libssh.c:L2256-L2451][f1]

Core SSH/SFTP state machine driver.

Each iteration dispatches the current sshc->state to its handler (SSH_INIT falls through into S_STARTUP, which falls through to HOSTKEY on success; SCP_DOWNLOAD_INIT falls through to SSH_SCP_DOWNLOAD on success; CHANNEL_FREE, SESSION_DISCONNECT and SESSION_FREE chain via fallthrough). The loop continues until a handler returns SSH_AGAIN or the state becomes SSH_STOP; other SSH-level error codes still progress the state inside the handlers, so the loop keeps running until STOP or AGAIN. A verification failure at HOSTKEY maps to CURLE_PEER_FAILED_VERIFICATION; SSH_QUIT/unknown states just stop. On SSH_AGAIN the block flag is set so the caller waits on the socket. On stop, sshc->actualcode becomes the returned CURLcode if the handlers recorded one; otherwise CURLE_OK.

**Notes.**

- contract: Handlers may return SSH_AGAIN, SSH_ERROR, SSH_OK/SSH_NO_ERROR, or CURLcode-ish ints; the machine distinguishes only STOP/AGAIN for looping.

**Uncertainties.**

- Handlers whose declared return types are int sometimes carry SSH state codes and sometimes are treated as rc==0 success; the exact meaning of nonzero non-AGAIN returns from states like CREATE_DIRS_MKDIR (returning rc from sftp calls) is not fully constrained by the visible code.

<a id="u-a6ec95216494"></a>
### `myssh_to_SFTP_CLOSE`

`static int myssh_to_SFTP_CLOSE(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L384-L390][f1]

Moves the state machine to SSH_SFTP_CLOSE and computes actualcode from the current SFTP session error via sftp_error_to_CURLE, returning SSH_ERROR.

Assumes sshc->sftp_session is live; behavior when it is NULL is unproven.

calls: [sftp_error_to_CURLE](r9-ssh-transfers.md#u-a9a719991b62)

**Uncertainties.**

- Behavior when sftp_get_error is called with a NULL sftp session is not shown in this file.

<a id="u-a310f0d5c935"></a>
### `scp_disconnect`

`static CURLcode scp_disconnect(struct Curl_easy *data, struct connectdata *conn, bool…` · [lib/vssh/libssh.c:L2731-L2747][f1]

SCP disconnect (blocking by design, since the multi interface has no async disconnect).

With a live ssh_session it jumps to SSH_SESSION_DISCONNECT and runs myssh_block_statemach with disconnect=TRUE (no progress checks or timeout). dead_connection is ignored.

<a id="u-a112e291e1c6"></a>
### `scp_doing`

`static CURLcode scp_doing(struct Curl_easy *data, bool *dophase_done)` · [lib/vssh/libssh.c:L2681-L2691][f1]

SCP DO-phase pump: runs myssh_multi_statemach and traces when the DO phase completes.

Result and dophase_done pass through unchanged.

<a id="u-7441023439ee"></a>
### `scp_done`

`static CURLcode scp_done(struct Curl_easy *data, CURLcode status, bool premature)` · [lib/vssh/libssh.c:L2772-L2784][f1]

SCP done entry: fails with CURLE_FAILED_INIT without ssh_conn metadata; on a clean status it jumps to SSH_SCP_DONE so channel close/EOF runs, then delegates to myssh_done.

premature is ignored.

<a id="u-d36d891a69ab"></a>
### `scp_perform`

`static CURLcode scp_perform(struct Curl_easy *data, bool *connected, bool *dophase_done)` · [lib/vssh/libssh.c:L2702-L2726][f1]

SCP DO-phase start: clears dophase_done, fails with CURLE_FAILED_INIT without ssh_conn metadata, jumps the machine to SSH_SCP_TRANS_INIT, runs myssh_multi_statemach, and reports connected state from the first socket.

Result and done flag pass through.

<a id="u-6ab74794805a"></a>
### `scp_recv`

`static CURLcode scp_recv(struct Curl_easy *data, int8_t sockindex, char *mem, size_t …` · [lib/vssh/libssh.c:L2820-L2848][f1]

SCP download data callback: ssh_scp_read returns the byte count or SSH_ERROR (mapped to CURLE_SSH); non-blocking handling is compiled out.

The count is reported via pnread; missing metadata yields CURLE_FAILED_INIT and pnread starts at 0.

<a id="u-9c0729a6a661"></a>
### `scp_send`

`static CURLcode scp_send(struct Curl_easy *data, int8_t sockindex, const uint8_t *mem…` · [lib/vssh/libssh.c:L2786-L2818][f1]

SCP upload data callback: ssh_scp_write is blocking, so no partial-write or EAGAIN handling exists (the wishful non-blocking code is compiled out).

A non-SSH_OK return yields CURLE_SSH; success reports the full buffer as written. Missing ssh_conn metadata yields CURLE_FAILED_INIT; pnwritten starts at 0 and eos is ignored.

<a id="u-a668c0f95018"></a>
### `sftp_disconnect`

`static CURLcode sftp_disconnect(struct Curl_easy *data, struct connectdata *conn, boo…` · [lib/vssh/libssh.c:L2905-L2924][f1]

SFTP disconnect (blocking by design).

With a live ssh_session it jumps to SSH_SFTP_SHUTDOWN and runs myssh_block_statemach with disconnect=TRUE, skipping progress and timeout checks. dead_connection is ignored.

<a id="u-9ee51ed90d22"></a>
### `sftp_doing`

`static CURLcode sftp_doing(struct Curl_easy *data, bool *dophase_done)` · [lib/vssh/libssh.c:L2892-L2900][f1]

SFTP DO-phase pump: runs myssh_multi_statemach and traces when the DO phase completes.

Result and done flag pass through.

<a id="u-e6be329bac8d"></a>
### `sftp_done`

`static CURLcode sftp_done(struct Curl_easy *data, CURLcode status, bool premature)` · [lib/vssh/libssh.c:L2926-L2943][f1]

SFTP done entry: fails with CURLE_FAILED_INIT without ssh_conn metadata.

On a clean status it moves to SSH_SFTP_CLOSE, additionally scheduling SSH_SFTP_POSTQUOTE_INIT as nextstate when postquote commands exist, the transfer was not premature, and this is not a retry connection; the CLOSE state later runs postquotes and returns. Delegates to myssh_done.

<a id="u-a9a719991b62"></a>
### `sftp_error_to_CURLE`

`static CURLcode sftp_error_to_CURLE(int err)` · [lib/vssh/libssh.c:L87-L109][f1]

Maps an SFTP error code to a curl result code.

SSH_FX_OK maps to CURLE_OK, no-such-file/path to CURLE_REMOTE_FILE_NOT_FOUND, permission-denied/write-protect to CURLE_REMOTE_ACCESS_DENIED, file-exists to CURLE_REMOTE_FILE_EXISTS, and everything else falls through to CURLE_SSH.

<a id="u-9040f719e2b7"></a>
### `sftp_perform`

`static CURLcode sftp_perform(struct Curl_easy *data, bool *connected, bool *dophase_d…` · [lib/vssh/libssh.c:L2863-L2889][f1]

SFTP DO-phase start: fails with CURLE_FAILED_INIT without ssh_conn metadata, jumps the machine to SSH_SFTP_QUOTE_INIT, runs myssh_multi_statemach, and reports connected state from the first socket.

Result and dophase_done pass through.

<a id="u-f2a46bb5b300"></a>
### `sftp_recv`

`static CURLcode sftp_recv(struct Curl_easy *data, int8_t sockindex, char *mem, size_t…` · [lib/vssh/libssh.c:L3027-L3087][f1]

SFTP download data callback using async reads.

State 0 begins the read (sftp_aio_begin_read on libssh > 0.11, else sftp_async_read_begin storing an index; failure: CURLE_RECV_ERROR) and falls into state 1, which waits for the result (sftp_aio_wait_read into mem, or sftp_async_read with the saved index); SSH_AGAIN records wait directions and returns CURLE_AGAIN, negative results are CURLE_RECV_ERROR, and completion resets sftp_recv_state and reports the read count. Unknown states return CURLE_RECV_ERROR. Missing metadata yields CURLE_FAILED_INIT; a debug assert guards len < CURL_MAX_READ_SIZE.

<a id="u-68210215286a"></a>
### `sftp_send`

`static CURLcode sftp_send(struct Curl_easy *data, int8_t sockindex, const uint8_t *me…` · [lib/vssh/libssh.c:L2946-L3021][f1]

SFTP upload data callback.

On libssh > 0.11 it uses a two-phase AIO: state 0 starts sftp_aio_begin_write (failure: CURLE_SEND_ERROR) and falls into state 1, which polls sftp_aio_wait_write; SSH_AGAIN records wait directions and returns CURLE_AGAIN, negative results are CURLE_SEND_ERROR, and completion resets the state and reports the written count. Other states are unreachable and return CURLE_SEND_ERROR. On older libssh it caps writes at 32768 bytes, calls the blocking sftp_write (negative result: CURLE_SSH), clears waitfor, and reports the written count. Missing metadata yields CURLE_FAILED_INIT.

**Uncertainties.**

- Whether sftp_write on old libssh can return SSH_AGAIN is asserted as impossible by the compiled-out code but not provable here.

<a id="u-3ef92b70c050"></a>
### `sshc_cleanup`

`static void sshc_cleanup(struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L1875-L1930][f1]

Releases all ssh_conn resources, only when sshc->initialized is set.

Order: close sftp_file, free sftp_session, free ssh_session (each nulled); DEBUGASSERTs verify no session/scp session remain (debug builds only). Then frees readdir_tmp, quote_attrs, readdir_attrs, readdir_link_attrs, privkey and pubkey keys, and the passphrase, pub_key, priv_key, quote_path1, quote_path2, readdir_linkPath strings, the readdir_buf, and homedir. Finally clears the initialized flag; calling again is a no-op.

<a id="u-17ae6697664a"></a>
### `libssh.c module code (L2678–L2680)`

`module_region` · [lib/vssh/libssh.c:L2678-L2680][f1]

Residual between myssh_connect and scp_doing; no behavioral statements visible.

**Uncertainties.**

- Content not present in the supplied source.

<a id="u-3ab71d42807f"></a>
### `libssh.c module code (L2691–L2701)`

`module_region` · [lib/vssh/libssh.c:L2691-L2701][f1]

Residual between scp_doing and scp_perform; no behavioral statements visible.

**Uncertainties.**

- Content not present in the supplied source.

<a id="u-34e3bfb3ad04"></a>
### `libssh.c module code (L2726–L2730)`

`module_region` · [lib/vssh/libssh.c:L2726-L2730][f1]

Residual between scp_perform and scp_disconnect; no behavioral statements visible.

**Uncertainties.**

- Content not present in the supplied source.

<a id="u-c0266a8feddf"></a>
### `libssh.c module code (L2747–L2750)`

`module_region` · [lib/vssh/libssh.c:L2747-L2750][f1]

Residual between scp_disconnect and myssh_done; no behavioral statements visible.

**Uncertainties.**

- Content not present in the supplied source.

<a id="u-66df4b0f3633"></a>
### `libssh.c module code (L2848–L2862)`

`module_region` · [lib/vssh/libssh.c:L2848-L2862][f1]

Residual between scp_recv and sftp_perform; no behavioral statements visible.

**Uncertainties.**

- Content not present in the supplied source.

<a id="u-22f2238063ea"></a>
### `libssh.c module code (L2889–L2891)`

`module_region` · [lib/vssh/libssh.c:L2889-L2891][f1]

Residual between sftp_perform and sftp_doing; no behavioral statements visible.

**Uncertainties.**

- Content not present in the supplied source.

<a id="u-c31226ee30aa"></a>
### `libssh.c module code (L2900–L2904)`

`module_region` · [lib/vssh/libssh.c:L2900-L2904][f1]

Residual between sftp_doing and sftp_disconnect; no behavioral statements visible.

**Uncertainties.**

- Content not present in the supplied source.

<a id="u-3d28b68623b1"></a>
### `libssh.c module code (L2943–L2945)`

`module_region` · [lib/vssh/libssh.c:L2943-L2945][f1]

Residual between sftp_done and sftp_send; no behavioral statements visible.

**Uncertainties.**

- Content not present in the supplied source.

<a id="u-a4db0cc7796d"></a>
### `libssh.c module code (L3021–L3026)`

`module_region` · [lib/vssh/libssh.c:L3021-L3026][f1]

Residual between sftp_send and sftp_recv; no behavioral statements visible.

**Uncertainties.**

- Content not present in the supplied source.

<a id="u-5bc70e5ff8e0"></a>
### `libssh.c module code (L3133–L3181)`

`static CURLcode myssh_statemachine(struct Curl_easy *data, struct ssh_conn *sshc, str…` · [lib/vssh/libssh.c:L2256-L2451][f1]

Tail of the file: the Curl_protocol_scp and Curl_protocol_sftp vtable definitions wiring the functions documented above into the curl protocol interface (setup_connection, do_it, done, connect_it, connecting, doing, pollsets, disconnect), followed by the closing USE_LIBSSH conditional.

Assignment-only; behavior lives in the referenced functions.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vssh/libssh.c
