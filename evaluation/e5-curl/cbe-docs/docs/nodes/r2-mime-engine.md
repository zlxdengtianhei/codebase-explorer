# MIME Multipart Engine

**Capability.** Building and streaming MIME/multipart message structures: the public part-assembly API, the state-machine readback pipeline with encoders, and the client-reader integration.

Use this subtree for MIME bodies: the curl_mime_* API to assemble parts and headers, the readback machinery that streams boundaries and encoded content, and the creader wrapper exposing a mime as a transfer body source.

**Children.**

- [MIME Assembly API](r2-mime-api.md) `r2-mime-api` · 24 unit(s)
- [MIME Readback & Encoders](r2-mime-readback.md) `r2-mime-readback` · 19 unit(s)
- [MIME Client Reader](r2-mime-creader.md) `r2-mime-creader` · 2 unit(s)

Parent: [libcurl Transfer Runtime](r2-libcurl-runtime.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
