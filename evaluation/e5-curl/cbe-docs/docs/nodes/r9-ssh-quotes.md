# SFTP quote commands

**Capability.** Parses and runs FTP-style quote commands against SFTP: per-command executors following the SSH_AGAIN/acceptfail template, attribute-modifying operations, statvfs, quote list advancement, error paths (myssh_quote_error, quote_error), and postquote initiation.

Use this child to see how user quote commands execute and fail. All failures converge on myssh_quote_error, which transitions to SSH_SFTP_CLOSE with CURLE_QUOTE_ERROR.

**Depends on.**

- [SFTP and SCP transfer states](r9-ssh-transfers.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [SFTP and SCP transfer states](r9-ssh-transfers.md) · model-inferred · 0 edge(s)

Parent: [SSH backend \(libssh\)](r9-ssh-backend.md)

## Units (8)

<a id="u-9fa8d9685a41"></a>
### `myssh-in-sftp-quote-stat`

`static int myssh_in_SFTP_QUOTE_STAT(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L1669-L1743][f1]

Attribute-modifying quote execution.

The .if fragment at lines 1743-1746 is part of myssh_in_SFTP_QUOTE_STAT's control flow (the compiler-visible split of its conditional chain) and carries no separate behavior. myssh_in_SFTP_QUOTE_STAT re-reads the command (honoring the '*' acceptfail prefix), stats quote_path2 (failure routes to myssh_quote_error), then applies the requested change: chgrp sets gid from a decimal number (max UINT_MAX), chmod sets permissions from an octal value (mask 07777), chown sets uid likewise, and atime/mtime parse a date via Curl_getdate_capped, rejecting unparseable dates and, on 64-bit time_t, dates above 0xffffffff; the matching field is set with the ACMODTIME flag. Number/date syntax failures and stat failure all go through myssh_quote_error (CURLE_QUOTE_ERROR). Success advances to SSH_SFTP_QUOTE_SETSTAT, which calls sftp_setstat: SSH_AGAIN returns for retry, a real failure with acceptfail unset routes to myssh_quote_error, and success (or tolerated failure) moves to SSH_SFTP_NEXT_QUOTE.

<a id="u-86db61df0947"></a>
### `quote-executors`

`static int myssh_in_SFTP_QUOTE_SYMLINK(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L1947-L1960][f1]

Simple SFTP quote executors, all following the same template: perform the libssh call; SSH_AGAIN returns for a retry; a nonzero failure routes to myssh_quote_error (recording CURLE_QUOTE_ERROR) unless acceptfail is set, in which case execution continues; success advances to SSH_SFTP_NEXT_QUOTE.

Variants: SETSTAT uses sftp_setstat on quote_path2 with quote_attrs; SYMLINK uses sftp_symlink with quote_path2 (target) and quote_path1; MKDIR uses sftp_mkdir on quote_path1 with new_directory_perms; RENAME uses sftp_rename(path1, path2); RMDIR uses sftp_rmdir on quote_path1; UNLINK uses sftp_unlink on quote_path1.

<a id="u-598da704748e"></a>
### `myssh_in_SFTP_NEXT_QUOTE`

`static int myssh_in_SFTP_NEXT_QUOTE(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L1646-L1667][f1]

Advances the quote list: frees quote_path1/2 and moves to the next quote_item.

If another item remains the machine returns to SSH_SFTP_QUOTE; otherwise a saved nextstate (e.g. postquote) is restored and cleared, else the machine proceeds to SSH_SFTP_GETINFO.

<a id="u-b3c73bac6661"></a>
### `myssh_in_SFTP_POSTQUOTE_INIT`

`static int myssh_in_SFTP_POSTQUOTE_INIT(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L1422-L1434][f1]

Runs post-transfer quote commands if postquote is set (entering SSH_SFTP_QUOTE with quote_item pointing at the list), otherwise stops the machine.

<a id="u-f276d20efe80"></a>
### `myssh_in_SFTP_QUOTE`

`static int myssh_in_SFTP_QUOTE(struct Curl_easy *data, struct ssh_conn *sshc, struct …` · [lib/vssh/libssh.c:L1448-L1644][f1]

Parses and dispatches one FTP-style quote command against SFTP.

A leading '*' enables acceptfail so later failures are tolerated. 'pwd' writes an FTP-like 257 header via Curl_debug and client-write (allocation or write failure closes SFTP with the error recorded). Any other command must contain a space; a missing separator or a failed first-pathname parse fails with CURLE_QUOTE_ERROR or the parse result. Command dispatch: chgrp/chmod/chown/atime/mtime and ln/symlink and rename need a second pathname (parse failure or trailing text via quote_error aborts); mkdir, rmdir, rm, and (with HAS_STATVFS_SUPPORT) statvfs require no trailing text and transition to their dedicated states; anything unknown fails with CURLE_QUOTE_ERROR. All syntax failures route to SSH_SFTP_CLOSE with nextstate cleared.

**Uncertainties.**

- Whether atime/mtime here reach QUOTE_STAT with a date string as quote_path1 (parsed later) is confirmed only by the dispatch above.

<a id="u-8c25cf80328c"></a>
### `myssh_in_SFTP_QUOTE_STATVFS`

`static int myssh_in_SFTP_QUOTE_STATVFS(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L626-L680][f1]

Implements the 'statvfs' quote command.

sftp_statvfs on quote_path1: on failure with acceptfail unset it routes through myssh_quote_error; on failure with acceptfail set it simply continues to the next quote. On success it formats all statvfs fields as a 'statvfs:' header block (64-bit format macro varies for MSVC/old MinGW), frees the struct, and writes it as a client header; allocation or write failure transitions to SSH_SFTP_CLOSE with the actualcode set. Successful or tolerated paths advance to SSH_SFTP_NEXT_QUOTE.

<a id="u-60460e10a718"></a>
### `myssh_quote_error`

`static void myssh_quote_error(struct Curl_easy *data, struct ssh_conn *sshc, const ch…` · [lib/vssh/libssh.c:L613-L624][f1]

Common quote-command failure path: optionally logs '<cmd> command failed: <libssh error>' when cmd is non-NULL, frees quote_path1/2, transitions to SSH_SFTP_CLOSE, cancels the pending nextstate (SSH_NO_STATE), and records CURLE_QUOTE_ERROR.

<a id="u-f241a51d9b72"></a>
### `quote_error`

`static int quote_error(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L1436-L1446][f1]

Handles trailing garbage after a quote command: logs 'Suspicious data after the command line', frees quote_path1/2, transitions to SSH_SFTP_CLOSE with nextstate cleared and CURLE_QUOTE_ERROR recorded.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vssh/libssh.c
