# Chunked transfer decoding header

**Capability.** Declares the state-machine vocabulary (states, structs, result codes) for decoding HTTP/1.1 chunked transfer encoding; declarations only.

Use this header as the contract reference for the chunked-decoding state machine consumers implement. No decoding logic is in this excerpt.

Parent: [curl codebase](r9-curl-source.md)

## Units (1)

<a id="u-7985db0528b7"></a>
### `http-chunks-header`

`enum` · [lib/http_chunks.h:L42-L83][f1]

Declares the state machine vocabulary for decoding HTTP/1.1 chunked transfer encoding.

ChunkyState enumerates the parser phases: CHUNK_HEX buffers hexadecimal digits until a non-hex byte, CHUNK_LF waits for the line feed, CHUNK_DATA consumes the chunker's stated byte count, CHUNK_POSTLF expects CR then LF (a missing CR is tolerated), CHUNK_TRAILER handles optional trailer lines, CHUNK_TRAILER_CR and CHUNK_TRAILER_POSTCR validate the trailer line terminator (a wrong byte signals CHUNKE_BAD_CHUNK, an empty trailer signals CHUNKE_STOP per the comments, otherwise trailers are written to the client), ending in CHUNK_DONE or CHUNK_FAILED. CHUNKcode values report the outcome, including CHUNKE_TOO_LONG_HEX, CHUNKE_ILLEGAL_HEX, CHUNKE_OUT_OF_MEMORY, CHUNKE_PASSTHRU_ERROR (carrying a CURLcode), and CHUNKE_TRAILER_LIMIT. struct Curl_chunker carries the cross-call state: remaining datasize, current state, last_code, a dynbuf holding trailers, hexindex/hexbuffer sized by CHUNK_MAXNUM_LEN (17 hex digits plus terminator), and flags ignore_body and in_connect. The function declarations (implementation in http_chunks.c) cover init/reset/free of the state, Curl_httpchunk_read consuming buffer bytes and emitting decoded body plus trailers to the client with ASCII hex handling, a done predicate, two write-callback type externals, and a helper that adds the chunked reader to the transfer's reader stack.

**Notes.**

- contract: Curl_httpchunk_read reports consumed input via *pconsumed only on success, per the comment contract.
- field: CHUNK_MAXNUM_LEN is 17 to fit 16 hex digits plus one accepted leading zero, bounded by 64-bit curl_off_t.

**Uncertainties.**

- All function behavior here is declared only; the http_chunks.c implementation is not in this batch, so exact error propagation and client-write sequencing remain unproven.
- The comment states CHUNKE_STOP is signalled for an empty trailer, but the implementing code is not visible.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http_chunks.h
