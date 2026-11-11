# Sansio App Base and Logging

**Capability.** Defines the framework-agnostic application base class and the logger setup it uses, covering app construction, configuration and Jinja environment preparation.

Read this when you need the app's non-WSGI foundation. The base class handles construction, registrations and URL support using the scaffold, and the small logging module configures the default application logger.

**Children.**

- [Sansio App Base Class](sansio-app-base-class.md) `sansio-app-base-class` · 26 unit(s)
- [Application Logging Setup](application-logging-setup.md) `application-logging-setup` · 5 unit(s)

**Depends on.**

- [Scaffold and Blueprint Registration](scaffold-and-blueprint-registration.md) · graph-confirmed · 9 edge(s) · The App base class uses the scaffold and blueprint registration logic to declare routes, handlers and callbacks.

Parent: [Sansio App and Scaffold Foundations](sansio-app-and-scaffold-foundations.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
