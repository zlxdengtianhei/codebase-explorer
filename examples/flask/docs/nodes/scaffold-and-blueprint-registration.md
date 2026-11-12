# Scaffold and Blueprint Registration

**Capability.** Defines how routes, handlers and callbacks are declared and deferred, through the shared Scaffold base and the sansio Blueprint that builds on it.

Look here for decorator-based setup and deferred registration. The scaffold supplies the common registration decorators and path helpers, and the blueprint extends them by recording functions to replay when registered on an app.

**Children.**

- [Scaffold Base and Setup Decorators](scaffold-base-and-setup-decorators.md) `scaffold-base-and-setup-decorators` · 22 unit(s)
- [Blueprint Deferred Registration](blueprint-deferred-registration.md) `blueprint-deferred-registration` · 21 unit(s)

**Depended on by.**

- [Sansio App Base and Logging](sansio-app-base-and-logging.md) · graph-confirmed · 9 edge(s) · The App base class uses the scaffold and blueprint registration logic to declare routes, handlers and callbacks.

Parent: [Sansio App and Scaffold Foundations](sansio-app-and-scaffold-foundations.md)

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.
