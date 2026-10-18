# SSH connection, auth and lifecycle

**Capability.** Session startup, host-key verification (myssh_is_known), keyboard-interactive/public-key/password/GSSAPI authentication states, connection setup and destructors, global init/version, and socket-forgetting/disconnect teardown.

Read this child for everything from ssh_connect to an authenticated session and its eventual teardown. myssh_block2waitfor and the blocking statemach drivers support the multi interface.

**Depends on.**

- [SFTP and SCP transfer states](r9-ssh-transfers.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [SFTP and SCP transfer states](r9-ssh-transfers.md) · model-inferred · 0 edge(s)

Parent: [SSH backend \(libssh\)](r9-ssh-backend.md)

## Units (32)

<a id="u-43f4b054cd66"></a>
### `Curl_ssh_cleanup`

`void Curl_ssh_cleanup(void)` · [lib/vssh/libssh.c:L3125-L3128][f1]

Global libssh teardown: calls ssh_finalize and discards its result.

<a id="u-6f1cffed0956"></a>
### `Curl_ssh_init`

`CURLcode Curl_ssh_init(void)` · [lib/vssh/libssh.c:L3116-L3123][f1]

Global libssh initialization: ssh_init failure logs in debug builds and returns CURLE_FAILED_INIT, otherwise CURLE_OK.

<a id="u-d666bd0c3a48"></a>
### `Curl_ssh_version`

`void Curl_ssh_version(char *buffer, size_t buflen)` · [lib/vssh/libssh.c:L3130-L3133][f1]

Writes a version string of the form 'libssh/<version>' (from ssh_version(0)) into the caller's buffer.

<a id="u-370131ff46d7"></a>
### `conn_forget_socket`

`static void conn_forget_socket(struct Curl_easy *data, int8_t sockindex)` · [lib/vssh/libssh.c:L1765-L1775][f1]

Makes the connection layer forget a socket that libssh closed behind its back: for a valid socket index it sends CF_CTRL_FORGET_SOCKET to the connect filter and fake-closes the stored descriptor, setting it to CURL_SOCKET_BAD.

No-op when conn is missing or the index is invalid.

<a id="u-16917b54dcdc"></a>
### `myssh_SESSION_DISCONNECT`

`static void myssh_SESSION_DISCONNECT(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L1777-L1808][f1]

Disconnect teardown state: frees any leftover scp_session, closes the sftp_file and frees the sftp_session (each nulled), calls ssh_disconnect, and—on libssh older than 0.10.0 where ssh_disconnect closes the socket itself—calls conn_forget_socket on the first socket.

Then frees homedir and moves to SSH_SESSION_FREE.

calls: [conn_forget_socket](r9-ssh-conn-auth.md#u-370131ff46d7)

<a id="u-53af3f479595"></a>
### `myssh_auth_interactive`

`static int myssh_auth_interactive(struct connectdata *conn, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L682-L745][f1]

Drives keyboard-interactive authentication across three internal kbd_state phases.

State 0 starts ssh_userauth_kbdint; SSH_AUTH_AGAIN propagates as SSH_AGAIN, any result other than SSH_AUTH_INFO is an error, and anything but exactly one prompt is rejected; the connection password is set as the single answer. State 1 re-invokes kbdint: AGAIN returns, SUCCESS maps to SSH_OK, and a follow-up SSH_AUTH_INFO with zero prompts advances to state 2 and restarts; other outcomes fail. State 2 performs the final kbdint, mapping AGAIN and SUCCESS as usual and everything else to SSH_ERROR. Any unknown state fails. On completion kbd_state resets to 0 and the final rc is returned.

**Uncertainties.**

- Exact semantics of the zero-prompt INFO-then-restart sequence depend on libssh's kbdint internals and are not shown here.

<a id="u-a8122882d705"></a>
### `myssh_block2waitfor`

`static void myssh_block2waitfor(struct connectdata *conn, struct ssh_conn *sshc, bool…` · [lib/vssh/libssh.c:L765-L779][f1]

Records which I/O directions the state machine must wait for.

When blocking, it translates ssh_get_poll_flags bits into sshc->waitfor: SSH_READ_PENDING becomes REQ_IO_RECV, SSH_WRITE_PENDING becomes REQ_IO_SEND; when not blocking waitfor is cleared to 0.

<a id="u-f7d631c8b998"></a>
### `myssh_block_statemach`

`static CURLcode myssh_block_statemach(struct Curl_easy *data, struct ssh_conn *sshc, …` · [lib/vssh/libssh.c:L2473-L2510][f1]

Blocking driver used for DO-phase completion and disconnect.

It loops the state machine until SSH_STOP or a CURLcode error. Unless disconnecting, it checks progress (aborting on callback abort) and enforces the operation timeout (CURLE_OPERATION_TIMEDOUT, after 'Operation timed out'). When the machine signals blocking it waits up to 1 second (or the remaining time, if shorter and nonzero) for the first socket to become readable before re-running.

<a id="u-1b7863c9db10"></a>
### `myssh_conn_dtor`

`static void myssh_conn_dtor(const void *key, size_t klen, void *entry)` · [lib/vssh/libssh.c:L2521-L2528][f1]

Metadata destructor for the connection-level ssh_conn: runs sshc_cleanup to release all libssh resources, then frees the struct.

Keys are ignored.

calls: [sshc_cleanup](r9-ssh-transfers.md#u-3ef92b70c050)

<a id="u-35f0fdb05244"></a>
### `myssh_connect`

`static CURLcode myssh_connect(struct Curl_easy *data, bool *done)` · [lib/vssh/libssh.c:L2563-L2678][f1]

Connection entry point.

It installs the right recv/send callbacks (scp_* for SCP protocols, sftp_* otherwise), creates the libssh session (failure: CURLE_FAILED_INIT), and sets options: host from the IPv6-bracketed or IDN hostname, config file parsing (failure only logged), the first socket fd, user (when creds provide one), knownhosts file set as both per-user and global options, port when nonzero, and the compression preference when enabled. Public/pub key files: pubkey is imported here when pub_key is set (failure: CURLE_FAILED_INIT); private key verification is deferred to the state machine. Finally the machine enters SSH_INIT and myssh_multi_statemach runs. Any ssh_options_set failure aborts with CURLE_FAILED_INIT after a failf message.

<a id="u-1a7e3b96baf5"></a>
### `myssh_easy_dtor`

`static void myssh_easy_dtor(const void *key, size_t klen, void *entry)` · [lib/vssh/libssh.c:L2512-L2519][f1]

Metadata destructor for the per-easy SSHPROTO struct: frees sshp->path and the struct itself.

Keys are ignored.

<a id="u-a395d2bd4107"></a>
### `myssh_in_AUTHLIST`

`static int myssh_in_AUTHLIST(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L801-L855][f1]

Begins authentication by trying ssh_userauth_none: SSH_AUTH_AGAIN returns for retry, immediate success marks authed and jumps to SSH_AUTH_DONE, and SSH_AUTH_ERROR fails with CURLE_LOGIN_DENIED.

Otherwise it lists the server's accepted methods, logs them, and picks the first available in priority order: publickey (only when a private key file or agent auth is configured), GSSAPI, keyboard-interactive, password; if none match, it fails with CURLE_LOGIN_DENIED.

<a id="u-36f0afa34cf3"></a>
### `myssh_in_AUTH_DONE`

`static int myssh_in_AUTH_DONE(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L1001-L1023][f1]

Finalizes authentication.

If authed is not set it fails with CURLE_LOGIN_DENIED. Otherwise it records the appconnect timer, points recv at the first socket with send deselected, and branches by protocol: SFTP proceeds to SSH_SFTP_INIT, plain SSH stops the machine (connect phase done).

<a id="u-41011da80ece"></a>
### `myssh_in_AUTH_GSSAPI`

`static int myssh_in_AUTH_GSSAPI(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L928-L947][f1]

GSSAPI authentication.

If GSSAPI is not in the enabled auth types it falls back to key auth. Otherwise ssh_userauth_gssapi runs: AGAIN returns for retry, success marks authed and completes to SSH_AUTH_DONE, and any other outcome falls back to key auth.

<a id="u-f97ab06b56b3"></a>
### `myssh_in_AUTH_KEY`

`static int myssh_in_AUTH_KEY(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L959-L974][f1]

Runs one step of keyboard-interactive auth.

SSH_AGAIN propagates; success marks authed, logs, and completes to SSH_AUTH_DONE; failure falls back to password auth.

<a id="u-3d952510e32c"></a>
### `myssh_in_AUTH_KEY_INIT`

`static int myssh_in_AUTH_KEY_INIT(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L949-L957][f1]

Keyboard-interactive gate: proceeds to SSH_AUTH_KEY only when CURLSSH_AUTH_KEYBOARD is enabled, otherwise falls back to password auth.

<a id="u-8359d6a4c5ee"></a>
### `myssh_in_AUTH_PASS`

`static int myssh_in_AUTH_PASS(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L985-L999][f1]

Authenticates with the connection password via ssh_userauth_password.

AGAIN returns for retry, success marks authed and completes to SSH_AUTH_DONE, and any other result (including explicit failure) fails with CURLE_LOGIN_DENIED.

<a id="u-6a5ba1e2978d"></a>
### `myssh_in_AUTH_PASS_INIT`

`static int myssh_in_AUTH_PASS_INIT(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L976-L983][f1]

Password auth gate: fails with CURLE_LOGIN_DENIED if CURLSSH_AUTH_PASSWORD is disabled, else advances to SSH_AUTH_PASS.

<a id="u-e79fa0cfa58e"></a>
### `myssh_in_AUTH_PKEY`

`static int myssh_in_AUTH_PKEY(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L910-L926][f1]

Authenticates with the imported private key via ssh_userauth_publickey.

AGAIN returns for retry; success marks authed and completes to SSH_AUTH_DONE; any other result logs and falls back to GSSAPI auth.

<a id="u-c41da3686244"></a>
### `myssh_in_AUTH_PKEY_INIT`

`static int myssh_in_AUTH_PKEY_INIT(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L857-L908][f1]

Public-key authentication setup.

If publickey auth is not enabled it defers to GSSAPI fallback. With a configured private key file it optionally probes with ssh_userauth_try_publickey (when a pubkey is loaded and no passphrase set), then imports the key file; import failure fails with CURLE_LOGIN_DENIED, success moves to SSH_AUTH_PKEY. Without a private key file it runs ssh_userauth_publickey_auto: AGAIN returns, success marks authed and completes to SSH_AUTH_DONE, otherwise it falls back to GSSAPI.

<a id="u-9c334cacaf6f"></a>
### `myssh_in_S_STARTUP`

`static int myssh_in_S_STARTUP(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L781-L799][f1]

Opens the SSH session with ssh_connect.

SSH_AGAIN records the wait direction and returns so the caller retries; any other non-OK result fails with CURLE_FAILED_INIT via myssh_to_ERROR; success advances to SSH_HOSTKEY.

<a id="u-d13ea5faf1eb"></a>
### `myssh_in_SESSION_FREE`

`static CURLcode myssh_in_SESSION_FREE(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L2235-L2248][f1]

Final teardown state: runs sshc_cleanup, captures sshc->actualcode as the result, zeroes the whole ssh_conn struct, marks the connection for close, restores state to SSH_SESSION_FREE with a cleared nextstate, and stops the machine.

The returned CURLcode is the recorded actualcode (CURLE_OK if none was set).

<a id="u-278059f475fa"></a>
### `myssh_is_known`

`static int myssh_is_known(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L123-L373][f1]

Verifies the server host key before authentication, returning SSH_OK or SSH_ERROR.

Priority order: (1) if a SHA256 fingerprint is set, the computed key hash is base64-encoded and compared after stripping '=' padding positions; any length or content mismatch fails and no further checks run. (2) Else if an MD5 fingerprint is set, the hash is formatted as 32 hex chars and compared case-insensitively; mismatch fails. (3) Else, with a knownhosts file configured, the session's known-hosts entry is fetched: an entry without a public key leaves knownkeyp NULL; the vstate maps to keymatch OK/MISMATCH/MISSING (SSH_KNOWN_HOSTS_OTHER maps to MISMATCH, NOT_FOUND/UNKNOWN/ERROR to MISSING, others to MISMATCH). If a key callback is configured it receives known vs found keys and its verdict is honored: FINE_ADD_TO_FILE updates the knownhosts file (failure propagates), FINE continues, anything else (REJECT/DEFER) fails; without a callback, only keymatch OK passes. Failures skip to cleanup, which frees libssh-allocated base64 strings with system free, clears pubkey hashes, the pubkey, and the knownhosts entry.

**Uncertainties.**

- Whether a knownhostsentry exists without a publickey is left to libssh behavior; in that case keymatch still evaluates from vstate with knownkeyp NULL, which the callback would observe as a NULL known key.

<a id="u-3a70c19f9e20"></a>
### `myssh_setup_connection`

`static CURLcode myssh_setup_connection(struct Curl_easy *data, struct connectdata *conn)` · [lib/vssh/libssh.c:L2533-L2554][f1]

Allocates and registers SSH per-connection and per-easy state.

It zero-allocates an ssh_conn (initialized TRUE, readdir_buf sized to 2*CURL_PATH_MAX) and attaches it to the connection with myssh_conn_dtor as destructor, then allocates an SSHPROTO attached to the easy handle with myssh_easy_dtor. Any allocation or registration failure returns CURLE_OUT_OF_MEMORY (the ssh_conn meta set failure path does not free the already-allocated sshc here). Finally it delegates to Curl_ssh_setup_pkey to load key settings.

**Notes.**

- failure: If Curl_conn_meta_set fails, sshc is leaked by this function as written.

uses: [myssh_conn_dtor](r9-ssh-conn-auth.md#u-1b7863c9db10), [myssh_easy_dtor](r9-ssh-conn-auth.md#u-1a7e3b96baf5)

<a id="u-6fa4de180c6d"></a>
### `myssh_state_init`

`static void myssh_state_init(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L747-L763][f1]

Initializes SSH connection state: clears secondCreateDirs, nextstate and actualcode, puts the libssh session in non-blocking mode, and enters SSH_S_STARTUP.

The protocol-level log-level bump is compiled out.

<a id="u-8a90422326d7"></a>
### `myssh_to_ERROR`

`static int myssh_to_ERROR(struct Curl_easy *data, struct ssh_conn *sshc, CURLcode res…` · [lib/vssh/libssh.c:L375-L382][f1]

Transitions the SSH state machine to SSH_SESSION_DISCONNECT, records the given CURLcode in sshc->actualcode, and returns SSH_ERROR to signal an error to the caller.

<a id="u-bf4d8b870c65"></a>
### `libssh.c module code (L1–L86)`

`module_region` · [lib/vssh/libssh.c:L1-L86][f1]

Compile-time setup for the libssh SSH backend: conditional includes plus the SSH_STRING_FREE_CHAR and SSH_S_IFMT/SSH_S_IFLNK fallback macros.

No behavior beyond macro expansion.

<a id="u-1e9728608ef9"></a>
### `libssh.c module code (L109–L122)`

`module_region` · [lib/vssh/libssh.c:L109-L122][f1]

Short residual region between sftp_error_to_CURLE and myssh_is_known; contains no behavioral statements visible in this excerpt.

**Uncertainties.**

- Content not present in the supplied source; treated as non-behavioral.

<a id="u-522cacd6fd24"></a>
### `libssh.c module code (L2248–L2255)`

`module_region` · [lib/vssh/libssh.c:L2248-L2255][f1]

Short residual region between myssh_in_SESSION_FREE and myssh_statemachine; no behavioral statements visible in the supplied source.

**Uncertainties.**

- Content not present in the supplied source.

<a id="u-c9359ad54e1e"></a>
### `libssh.c module code (L2451–L2453)`

`module_region` · [lib/vssh/libssh.c:L2451-L2453][f1]

Two-line residual between the statemachine and myssh_multi_statemach; no behavioral statements visible.

**Uncertainties.**

- Content not present in the supplied source.

<a id="u-3c778112d731"></a>
### `libssh.c module code (L2528–L2532)`

`module_region` · [lib/vssh/libssh.c:L2528-L2532][f1]

Residual lines between the destructors and myssh_setup_connection; no behavioral statements visible.

**Uncertainties.**

- Content not present in the supplied source.

<a id="u-5ebdda8e49ee"></a>
### `libssh.c module code (L2554–L2562)`

`module_region` · [lib/vssh/libssh.c:L2554-L2562][f1]

Residual region containing the static forward declarations of scp_recv/scp_send and sftp_recv/sftp_send before myssh_connect; non-behavioral declarations.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vssh/libssh.c
