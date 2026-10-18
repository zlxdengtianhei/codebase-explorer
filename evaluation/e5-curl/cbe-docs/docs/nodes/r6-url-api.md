# URL API (urlapi)

**Capability.** RFC 3986 URL parsing, validation, manipulation and retrieval behind the CURLU handle: full-parse pipeline, authority/host normalization, percent-encoding, and the public curl_url_* API.

Consumers pass URL strings in and get validated, normalized parts out. Parse pipeline, host handling, encoding and the public handle API can be read independently. Heavily reused by HTTP redirect/target handling and the command-line tool.

**Children.**

- [URL Parse Pipeline](r6-url-parse-pipeline.md) `r6-url-parse-pipeline` · 14 unit(s)
- [Authority and Host Handling](r6-url-host-authority.md) `r6-url-host-authority` · 11 unit(s)
- [URL Encoding and Retrieval](r6-url-encoding-and-getters.md) `r6-url-encoding-and-getters` · 14 unit(s)
- [CURLU Handle Management and Setters](r6-url-handle-api.md) `r6-url-handle-api` · 8 unit(s)

Parent: [curl Codebase](r6-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
