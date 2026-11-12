# Runtime App, Contexts and Testing

**Capability.** Covers the running application: the concrete Flask app and request lifecycle, the contexts that bind per-request state, and the tools for testing apps.

Go here to follow a request through the live app or to test one. One subgroup contains the Flask class and its dispatch, response and error flow, while the other children manage app and request contexts and provide the test client and CLI runner.

**Children.**

- [Flask App Request Lifecycle](flask-app-request-lifecycle.md) `flask-app-request-lifecycle` · 34 unit(s)
- [Test Client and CLI Runner](test-client-and-cli-runner.md) `test-client-and-cli-runner` · 15 unit(s)
- [App and Request Context Management](app-and-request-context-management.md) `app-and-request-context-management` · 15 unit(s)

**Depends on.**

- [Command Line and Public Helpers](command-line-and-public-helpers.md) · graph-confirmed · 2 edge(s) · 1 inferred relation(s)
- [Sansio App and Scaffold Foundations](sansio-app-and-scaffold-foundations.md) · graph-confirmed · 1 edge(s) · 1 inferred relation(s)
- [Session Interface and Cookies](session-interface-and-cookies.md) · graph-confirmed · 1 edge(s) · The runtime and testing modules use the session interface to open and save sessions.
- [Templates, Views and Wrappers](templates-views-and-wrappers.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Sansio App and Scaffold Foundations](sansio-app-and-scaffold-foundations.md) · graph-confirmed · 1 edge(s)

Parent: [Flask Web Framework](flask-web-framework.md)

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.
