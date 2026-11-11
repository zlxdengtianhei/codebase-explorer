# Chat Wire and Media Formats

**Capability.** Translates internal messages and content into provider-specific request payloads and back, covering chat, media, images, and transcription.

Come here when request or response formats for a provider need changing. Provider chat wire formatting handles Anthropic, Bedrock, and OpenAI chat payloads; Gemini and media integrations covers Gemini endpoints plus OpenAI media endpoints and shared helpers.

**Children.**

- [Provider chat wire formatting](provider-chat-wire-formatting.md) `provider-chat-wire-formatting` · 18 unit(s)
- [Gemini and media integrations](gemini-and-media-integrations.md) `gemini-and-media-integrations` · 18 unit(s)

**Depends on.**

- [Tool definition and execution](tool-definition-and-execution.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Tool definition and execution](tool-definition-and-execution.md) · graph-confirmed · 3 edge(s) · Tool definitions are converted into provider-specific tool declarations for chat requests.

Parent: [Provider Adapters and Tools](provider-adapters-and-tools.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
