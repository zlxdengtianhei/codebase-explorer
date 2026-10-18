# Command-Line Tool Support

**Capability.** curl-tool helpers built on the libcurl URL API: URL/operation helpers, IPFS gateway rewriting, metadata side-writes, and variable expansion for --variable and {{}} syntax.

These subtrees serve the src/ tool executable only. They consume the URL API heavily and, in the case of fwrite_xattr, are called from many libcurl modules per the observed edges — treat those as cross-tree consumers of this tool helper.

**Children.**

- [Tool URL and Operation Helpers](r6-tool-operation-helpers.md) `r6-tool-operation-helpers` · 6 unit(s)
- [IPFS URL Rewriting](r6-tool-ipfs-rewrite.md) `r6-tool-ipfs-rewrite` · 2 unit(s)
- [Extended Attribute Metadata](r6-tool-xattr-metadata.md) `r6-tool-xattr-metadata` · 4 unit(s)
- [Tool Variable Store and Expansion](r6-tool-variable-store.md) `r6-tool-variable-store` · 4 unit(s)

Parent: [curl Codebase](r6-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
