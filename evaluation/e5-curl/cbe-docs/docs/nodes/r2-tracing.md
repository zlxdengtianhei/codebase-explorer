# Tracing & Logging

**Capability.** Declarations and macro layer of the tracing subsystem: per-feature log levels, component-name based verbosity control, and debug/failf logging surfaces.

Use to see how trace verbosity is configured per component and how the trace macros compile under different build settings; the struct curl_trc_feat is the per-feature unit checked by the macros.

Parent: [libcurl Transfer Runtime](r2-libcurl-runtime.md)

## Units (3)

<a id="u-f5dc47baad97"></a>
### `curl_trc.h module code (L1–L98)`

`module_region` · [lib/curl_trc.h:L1-L98][f1]

Declarations of the tracing subsystem: Curl_trc_init, Curl_trc_opt (comma-separated case-insensitive component names, 'all', +/- en/disable prefixes; later calls may not take effect), Curl_debug, failf/Curl_failf and Curl_reset_fail, info-style loggers per component, log level macros, and the trailing extern declarations for feature objects guarded by build macros.

Declarations only; no implementations in this file.

<a id="u-63b4b1a6f617"></a>
### `curl_trc_feat`

`struct curl_trc_feat` · [lib/curl_trc.h:L99-L102][f1]

struct curl_trc_feat holds a component name and an int log_level; it is the unit checked by the per-feature verbosity macros.

<a id="u-61dcbf1268bf"></a>
### `curl_trc.h module code (L102–L347)`

`module_region` · [lib/curl_trc.h:L102-L347][f1]

Macro layer selecting how trace macros compile.

With CURL_HAVE_MACRO_VARARG and verbose strings, infof/CURL_TRC_* first test the matching feature's verbosity (Curl_trc_is_verbose, Curl_trc_cf_is_verbose, Curl_trc_ft_is_verbose) before calling the underlying function. With CURL_DISABLE_VERBOSE_STRINGS they compile to no-ops casting arguments away. Without macro varargs the macros alias directly to the functions. When verbose strings are disabled, the *_is_verbose macros expand to FALSE and CURL_TRC_EASY_TIMERS becomes Curl_nop_stmt. Feature externs (ftp, smtp, ssls, ssh, ws, multi, read, write, dns, doh, timer, threads) are guarded by their respective build macros.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curl_trc.h
