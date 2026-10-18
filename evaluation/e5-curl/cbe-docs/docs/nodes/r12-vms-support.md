# VMS support

**Capability.** VMS-specific tool behavior: LIB$INITIALIZE-time DECC$* feature initialization, DCL-vs-Unix shell detection, and shell-appropriate exit status encoding.

Read when adjusting VMS build or exit semantics; decc_init runs before main via the PSECT pragma blocks in the module regions.

Parent: [Platform adaptation](r12-platform-adaptation.md)

## Units (4)

<a id="u-a7b177c13267"></a>
### `tool_vms-c-module-regions`

`struct decc_feat_t` · [src/tool_vms.c:L122-L125][f1]

Non-behavioral and supporting regions of tool_vms.c: license header, __VMS-guarded includes and declarations of decc$__posix_exit/decc$exit, the vms_shell static, the decc_feat_t struct and decc_feat_array/decc_init_done definitions, and the LIB$INITIALIZE PSECT pragma blocks.

<a id="u-ca75c05944fe"></a>
### `decc_init`

`static void decc_init(void)` · [src/tool_vms.c:L144-L188][f1]

LIB$INITIALIZE-time initializer that sets a fixed list of DECC$* C RTL features on non-VAX VMS, reporting invalid names or values.

**Notes.**

- side_effect: Sets decc_init_done = 1 on entry; for each feature in decc_feat_array, fetches its index and min/max values, sets the value only when it differs and lies within range.
- failure: A negative feature index prints 'UNKNOWN DECC FEATURE'; a desired value outside min/max prints 'INVALID DECC FEATURE VALUE' via curl_mprintf; neither aborts the loop.
- field: The trailing pragma region places x_decc_init into the LIB$INITIALIZE PSECT and adds a fake LIB$INITIALIZE reference to force loading.

uses: [tool_vms-c-module-regions](r12-vms-support.md#u-a7b177c13267)

**Uncertainties.**

- The sts result of decc$feature_set_value is stored but never checked

<a id="u-7f3c9e2c8afc"></a>
### `is_vms_shell`

`int is_vms_shell(void)` · [src/tool_vms.c:L45-L69][f1]

Caches and reports whether the process runs under the VMS DCL shell versus a ported Unix shell, based on the SHELL environment variable.

**Notes.**

- side_effect: Memoizes the result in the static vms_shell flag (init -1), so the environment is inspected only once per process.
- condition: Returns 1 (DCL) when SHELL is unset or equals "DCL"; returns 0 for any other SHELL value.

<a id="u-45b5338928d4"></a>
### `vms_special_exit`

`void vms_special_exit(int code, int vms_show)` · [src/tool_vms.c:L88-L106][f1]

Terminates curl on VMS, choosing the POSIX or VMS-encoded exit path according to the detected shell type.

**Notes.**

- condition: On CRTL >= 7.0, a Unix shell (is_vms_shell() == 0) exits via decc$__posix_exit(code) and never reaches the VMS path.
- condition: On the DCL path, codes above CURL_LAST are clamped to CURL_LAST (keeping curlmsg.h in sync); otherwise the exit code is vms_cond[code] OR-ed with vms_show, passed to decc$exit().

calls: [is_vms_shell](r12-vms-support.md#u-7f3c9e2c8afc)

**Uncertainties.**

- On CRTL < 7.0 the POSIX branch is compiled out and DCL exit is always used, even under a Unix shell

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_vms.c
