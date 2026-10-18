# OpenAI Family

**Capability.** The OpenAI adapter and its subclasses (DeepSeek, Mistral, Perplexity), which inherit OpenAI mixins and request behavior while overriding capabilities and payload details.

Start with the OpenAI core for shared behavior; the derived providers only override what differs. Capabilities derive model metadata by regex-matching model ids against families.

**Children.**

- [OpenAI Adapter](r1-openai-core.md) `r1-openai-core` · 11 unit(s)
- [OpenAI Tools](r1-openai-tools.md) `r1-openai-tools` · 4 unit(s)
- [DeepSeek Adapter](r1-deepseek-adapter.md) `r1-deepseek-adapter` · 6 unit(s)
- [Mistral Adapter](r1-mistral-adapter.md) `r1-mistral-adapter` · 4 unit(s)
- [Perplexity Adapter](r1-perplexity-adapter.md) `r1-perplexity-adapter` · 6 unit(s)

Parent: [Provider Framework](r1-provider-framework.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
