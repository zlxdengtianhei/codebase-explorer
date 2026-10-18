# Terminal password input

**Capability.** Per-platform no-echo password reading (portable termios, VMS, Windows) with terminal echo toggling and the platform-conditional header scaffolding.

Three mutually exclusive getpass_r implementations share the ttyecho helper where applicable. Use the platform guards to locate the variant compiled for a given system.

Parent: [Command-line tool support](r15-tool-cli.md)

## Units (9)

<a id="u-dccdf913c398"></a>
### `tool_getpass.c module code (L1–L55)`

`module_region` · [src/tool_getpass.c:L1-L55][f1]

Includes and platform guards: undefines HAVE_TERMIOS_H on classic Amiga, includes termios/termio, VMS, Windows conio, and unistd headers per platform, and the whole file compiles only when HAVE_GETPASS_R is undefined.

<a id="u-a426903accf8"></a>
### `getpass_r`

`char *getpass_r(const char *prompt, char *buffer, size_t buflen)` · [src/tool_getpass.c:L56-L62][f1]

Portable fallback getpass_r opens /dev/tty read-only, falling back to STDIN_FILENO if the open fails, disables echo via ttyecho, prints the prompt to tool_stderr, and reads up to buflen bytes.

On positive read it overwrites the trailing newline with NUL; on zero or negative read it NUL-terminates at index 0. If echo was actually disabled it prints a newline and restores echo; then it closes the fd unless stdin is in use, and always returns the buffer. Read errors are thus indistinguishable from an empty password.

calls: [ttyecho](r15-cli-terminal-input.md#u-7572967baf59)

**Uncertainties.**

- A returned empty string may mean either an empty password or a read failure.

<a id="u-bc887626a1da"></a>
### `tool_getpass.c module code (L112–L125)`

`module_region` · [src/tool_getpass.c:L112-L125][f1]

Selects struct_term between struct termios and struct termio, or undefines it when neither header exists, controlling ttyecho's code paths.

<a id="u-7572967baf59"></a>
### `ttyecho`

`static bool ttyecho(bool enable, int fd)` · [src/tool_getpass.c:L126-L162][f1]

ttyecho toggles terminal echo on the given fd.

With enable false, under HAVE_TERMIOS_H it saves the current termios into a static withecho, clears ECHO, and applies TCSANOW; under HAVE_TERMIO_H it does the same with ioctl TCGETA/TCSETA; if neither header exists it cannot disable echo and returns FALSE. With enable true it restores the saved withecho (TCSAFLUSH or TCSETA) and returns TRUE; without either header it returns FALSE. Static saved-term buffers make it non-reentrant across different fds.

**Notes.**

- side_effect: Permanently modifies the process-static withedecho/noecho terminal settings shared by all callers.
- failure: Return values of tcgetattr/tcsetattr/ioctl are ignored; failure of these calls is not detected.

<a id="u-5520f954e86c"></a>
### `src/tool_getpass.c:getpass_r (2)`

`char *getpass_r(const char *prompt, char *buffer, size_t buflen)` · [src/tool_getpass.c:L89-L112][f1]

VMS-only implementation of getpass_r that reads a no-echo password from the terminal.

It empties the buffer, assigns the 'TT' device via sys$assign, and on success issues sys$qiow with IO$_READPROMPT | IO$M_NOECHO, passing the prompt and its length. Only if both the QIO status and iosb status have the low bit set does it terminate the string at iosb.iosb$w_bcnt. It always frees the channel with sys$dassgn and always returns the buffer, regardless of any failure, so callers cannot detect read errors from this variant.

uses: [_isb](r15-cli-terminal-input.md#u-f5191bb30100)

**Uncertainties.**

- Exact semantics of the VMS sys$ calls are outside the supplied source.

<a id="u-f5191bb30100"></a>
### `_isb`

`struct _isb` · [src/tool_getpass.c:L62-L66][f1]

Inline struct used only in the VMS getpass_r variant to emulate iosbdef.h, which was missing on VAX v7.2 and CC 6.4.

It holds a short status field, a short byte count, and an unused int.

uses: [src/tool_getpass.c:getpass_r (2)](r15-cli-terminal-input.md#u-5520f954e86c)

<a id="u-82a08f15a412"></a>
### `tool_getpass.c module code (L84–L88)`

`module_region` · [src/tool_getpass.c:L84-L88][f1]

Two-line residue between the VMS and Windows implementations; only the DONE macro definition separating guarded blocks.

<a id="u-c8943741b0c0"></a>
### `src/tool_getpass.c:getpass_r (3)`

`char *getpass_r(const char *prompt, /* prompt to display */ char *buffer, /* buffer t…` · [src/tool_getpass.c:L164-L193][f1]

Windows implementation of getpass_r prints the prompt to tool_stderr, then reads up to buflen keys via _getch with echo disabled.

On carriage return or newline it stores a NUL at that position and stops; on backspace it rewinds the index by two (removing the backspace and the previous character) unless already at index 0, where only the backspace position is removed. If the loop filled the whole buffer without ENTER, it force-terminates buffer[buflen-1]. It always prints a newline afterwards and returns the buffer, never signalling failure.

uses: [getpass_r](r15-cli-terminal-input.md#u-a426903accf8)

**Uncertainties.**

- Backspace at index 0 sets i to SIZE_MAX-sized wraparound (i - 1 on unsigned); behavior of the next iteration depends on unsigned wrap and is not fully provable from this excerpt.

<a id="u-808e8e4b8dd3"></a>
### `tool_getpass.c module code (L193–L196)`

`module_region` · [src/tool_getpass.c:L193-L196][f1]

Closing guards for the DONE and HAVE_GETPASS_R conditionals; no code.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_getpass.c
