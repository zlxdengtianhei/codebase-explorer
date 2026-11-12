# Platform and Dragonbox Support

**Capability.** Wraps platform FILE and locale internals and supplies Dragonbox caches, decimal helpers, and assertion support for formatting internals.

Use this group for platform-facing internals and Dragonbox/assertion helpers. Platform wrappers form the larger child; Dragonbox cache and assertion code is the smaller support child.

**Children.**

- [Platform File and Locale Internals](platform-file-and-locale-internals.md) `platform-file-and-locale-internals` · 26 unit(s)
- [Dragonbox Cache and Assertions](dragonbox-cache-and-assertions.md) `dragonbox-cache-and-assertions` · 7 unit(s)

**Depends on.**

- [Low-Level Formatting Primitives](low-level-formatting-primitives.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Big Integer Float Formatting](big-integer-float-formatting.md) · graph-confirmed · 12 edge(s) · big-integer-float-formatting depends on platform-and-dragonbox-support for Dragonbox and platform support.
- [Low-Level Formatting Primitives](low-level-formatting-primitives.md) · graph-confirmed · 13 edge(s)

Parent: [Core Formatting Internals](core-formatting-internals.md)

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.
