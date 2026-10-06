# Explicit advanced providers

The default workflow uses the main agent's signed-in native subagent tool.
Choose a provider only when the user explicitly needs direct API/argv execution.
Subscription login is not a generic API credential; do not extract or proxy tokens.

The existing `cbe produce` interface invokes a configured public argv provider.
See `cbe produce --help` and the package README for its options. The provider
configuration declares argv/model and its receipt contract; the product does not
import private host runners or bundle a key. A direct HTTP provider must retain
its call/prompt/model binding and actual usage evidence. An unknown receipt or
interrupted delivery protects only that call from unsafe resend.

The lower-level claim/delivery/import commands remain for integrations. Native
`--event` is a compatibility JSON interface; ordinary native users should use
`--status`, `--host`, the actual child handle and an explicit result/session file.
Do not have an agent manually assemble generation/hash/envelope fields.

Existing weighted-v1 workflows are documented in
[legacy-workflows.md](legacy-workflows.md). Their strict compatibility policy is
separate from new module-first native report policy. Do not rewrite historical
usage or claim a prior provider experiment tested native subscription production.
