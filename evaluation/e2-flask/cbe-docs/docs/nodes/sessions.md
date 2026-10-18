# Session Support

**Capability.** Session backend abstraction: SessionInterface defines open/save and config-driven cookie attributes, SessionMixin supplies mutable-mapping conventions, SecureCookieSession tracks modification for signed-cookie storage, NullSession is the read-only fallback, and SecureCookieSessionInterface is the default signed, timestamped cookie backend.

Use this subtree to understand how sessions open, persist, and land in cookies, and how to swap backends by replacing the interface class. With no secret key, behavior falls back to NullSession.

Parent: [Flask App Region](flask-app-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
