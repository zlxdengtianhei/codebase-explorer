# SSH/SFTP/SCP shared client

**Capability.** Shared SSH-family helpers: URL path and home-relative working-path resolution, quote-command filename parsing, byte-range computation, public-key auth setup, state naming, and multi-interface pollsets.

Use when backends under lib/vssh need path, range, or authentication-option handling. The ssh.h header defines the common types all SSH backends share.

**Depends on.**

- [Multi-handle core](r12-multi-core.md) · model-inferred · 0 edge(s)

Parent: [Protocol engines](r12-protocol-engines.md)

## Units (8)

<a id="u-7a72fa9e0e4f"></a>
### `ssh-h-header`

`enum` · [lib/vssh/ssh.h:L52-L117][f1]

Declares the shared SSH/SFTP/SCP data types and interface for curl's SSH backends.

Forward declarations expose Curl_protocol_sftp/scp; conditional includes pick libssh2 or libssh headers when USE_SSH is set, and define the meta keys CURL_META_SSH_EASY/CONN. The sshstate enum orders the state machine: connect states (SSH_INIT..SSH_SFTP_REALPATH), SFTP quote/transfer states, SCP states, and shutdown states, with SSH_NO_STATE=-1 and SSH_STOP=0 as sentinels and SSH_LAST unused as bound marker. SSHPROTO holds per-easy-handle data (path, plus libssh2-only readdir/quote scratch buffers); the comment bans connection-related state here. struct ssh_conn holds connection-scoped state: authlist, key/passphrase strings, state/nextstate slots, quote scratch, homedir, waitfor override bits, and backend-specific handles (libssh session/SFTP/SCP/keys under USE_LIBSSH, libssh2 session/channel/SFTP/agent/knownhosts under USE_LIBSSH2). Preprocessor #error fires when libssh <0.9.0 or libssh2 <1.9.0 is detected. Under !USE_SSH, Curl_ssh_statename(x) collapses to "" and Curl_ssh_init() to 0 so callers compile unchanged.

**Notes.**

- field: ssh_conn.state/nextstate must be changed only via the state helper per the header comment; Curl_ssh_set_state in vssh.c is that entry point.

contract: [Curl_ssh_set_state](r12-ssh-client.md#u-7fb2dcec18e3), [Curl_ssh_statename](r12-ssh-client.md#u-d2b2115d2ed2)

**Uncertainties.**

- If USE_SSH is set with neither USE_LIBSSH2 nor USE_LIBSSH, no backend headers are included; resulting behavior is not visible here.

<a id="u-d61a443b040b"></a>
### `Curl_getworkingpath`

`CURLcode Curl_getworkingpath(struct Curl_easy *data, const char *homedir, /* when SFT…` · [lib/vssh/vssh.c:L131-L199][f2]

Resolves the request URL path into the working path for SCP/SFTP, translating home-relative '/~/' notation.

It first URL-decodes data->state.up.path; a decode failure returns that result with no output. A dynbuf limited to MAX_SSHPATH_LEN (100000) accumulates a rewritten path. For an SCP path starting '/~/' (and longer than 3 bytes), the prefix is stripped and the remainder appended. For an SFTP path exactly '/~' or starting '/~/', homedir is prepended; for the longer form, a separating '/' is copied from index 2 when homedir lacks a trailing slash (index 3 otherwise), and bare '/~' appends '/'. Any dynbuf growth failure frees the decoded path and returns CURLE_OUT_OF_MEMORY. If the dynbuf was grown, *path receives its pointer; otherwise the decoded path is returned unchanged. A DEBUGASSERT requires non-empty output.

<a id="u-a9d784fe9918"></a>
### `Curl_get_pathname`

`CURLcode Curl_get_pathname(const char **cpp, char **path, const char *homedir)` · [lib/vssh/vssh.c:L203-L288][f2]

Parses one filename token from an SFTP quote command string.

Outputs are cleared first; an empty input or NULL homedir returns CURLE_QUOTE_ERROR. Leading blanks are skipped. For a quoted name (single or double quote), characters are copied until the matching quote; backslash escapes are honored only for quote and backslash characters, premature end-of-string or an empty quoted body fails via the fail label (freeing the dynbuf, CURLE_QUOTE_ERROR), while dynbuf allocation errors propagate directly. For unquoted names, a leading '/~/' is replaced by homedir plus '/'; then curlx_str_word reads to whitespace or terminator. An over-long word returns CURLE_TOO_LARGE after freeing the dynbuf; an absent word with no home-prepended content fails to CURLE_QUOTE_ERROR, and a present word is appended. Trailing blanks are skipped and the remaining cursor is returned through *cpp so a second parameter can be parsed; *path receives the built buffer.

**Uncertainties.**

- The success path does not free the dynbuf; ownership of the returned *path buffer relative to the dynbuf wrapper is not settled by this source.

<a id="u-969ba2e0ae76"></a>
### `Curl_ssh_range`

`CURLcode Curl_ssh_range(struct Curl_easy *data, const char *range, curl_off_t filesiz…` · [lib/vssh/vssh.c:L290-L334][f2]

Parses a byte-range string against a file size and computes a start offset and transfer length.

Parsing the start number returns CURLE_RANGE_ERROR on overflow. After skipping blanks, a '-' is consumed; then the end number is parsed: an end overflow, a failed end when no start was given either, or trailing residue after the end all return CURLE_RANGE_ERROR. When no start is given, the value is relative to the end: '-0' is rejected; an end beyond the file size is clamped to the size; from becomes filesize-to and to becomes filesize-1. With an explicit start beyond the file size, failf reports the offset and CURLE_RANGE_ERROR is returned. When the end is omitted (STRE_NO_NUM) or at/past the file size, it is clamped to filesize-1. from greater than to fails with a failf message, as does a span equal to CURL_OFF_T_MAX (overflow guard). On success *startp=from and *sizep=to-from+1.

<a id="u-372f682177bd"></a>
### `Curl_ssh_setup_pkey`

`CURLcode Curl_ssh_setup_pkey(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/vssh.c:L365-L453][f2]

Populates public-key authentication fields on ssh_conn from easy-handle options; it returns CURLE_OK immediately unless CURLSSH_AUTH_PUBLICKEY is requested.

With a configured private-key string it is duplicated. Without one, it probes common locations: $HOME/.ssh/id_rsa, then $HOME/.ssh/id_dsa (each verified with curlx_stat), then id_rsa and id_dsa in the current directory; if none exists, priv_key is set to an empty string to suppress later info messages. A public-key option is honored only if non-empty (empty treated as unset, letting the SSH library derive the public key from the private key file). A configured key password is duplicated into sshc->passphrase. infof reports the public/private key files, or a notice when authenticating without a private key. Any allocation failure jumps to fail, which frees home, priv_key and pub_key and returns CURLE_OUT_OF_MEMORY.

**Notes.**

- side_effect: On failure, previously assigned pub_key/priv_key on sshc are freed and left dangling/cleared by safefree; passphrase assigned before failure is not freed in the fail path.

**Uncertainties.**

- The fail path does not free sshc->passphrase even though it may already be assigned, so a failed setup can leave passphrase set; whether callers clean it is not visible here.

<a id="u-7fb2dcec18e3"></a>
### `Curl_ssh_set_state`

`void Curl_ssh_set_state(struct Curl_easy *data, struct ssh_conn *sshc, sshstate nowst…` · [lib/vssh/vssh.c:L112-L126][f2]

Sets the SSH state machine slot on the connection struct.

Under CURLVERBOSE it logs old-to-new state names only when the state actually changes; without it, data is unused. Unconditionally assigns sshc->state = nowstate; nextstate is not touched here and remains managed by callers.

<a id="u-d2b2115d2ed2"></a>
### `Curl_ssh_statename`

`const char *Curl_ssh_statename(sshstate state)` · [lib/vssh/vssh.c:L38-L105][f2]

Maps an sshstate value to its canonical name for verbose logging.

Returns the static names table entry indexed by state; any state at or beyond the table size yields "". A DEBUGASSERT checks that the table length equals SSH_LAST, active only in debug builds. Compiled only under CURLVERBOSE; the header substitutes an empty-string macro otherwise.

<a id="u-6fad740ff175"></a>
### `Curl_ssh_pollset`

`CURLcode Curl_ssh_pollset(struct Curl_easy *data, struct easy_pollset *ps)` · [lib/vssh/vssh.c:L338-L363][f2]

Builds the socket wait set for the multi interface during DO_DONE/PERFORM/WAITPERFORM.

It fetches the per-connection ssh_conn via the CURL_META_SSH_CONN meta key and the first socket; a missing ssh_conn or a bad socket returns CURLE_FAILED_INIT. waitfor prefers sshc->waitfor, falling back to data->req.io_flags; when set, REQ_IO_RECV/REQ_IO_SEND bits map to CURL_POLL_IN/CURL_POLL_OUT (asserted nonzero) and Curl_pollset_change updates the pollset. With no explicit wait flags, an open sshc->ssh_session causes listening for incoming data (CURL_POLL_IN); otherwise the pollset is left unchanged and CURLE_OK is returned.

uses: [ssh-h-header](r12-ssh-client.md#u-7a72fa9e0e4f)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vssh/ssh.h
[f2]: ../../../../../../eval/curl-2c04412/lib/vssh/vssh.c
