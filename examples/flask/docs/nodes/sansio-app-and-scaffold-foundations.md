# Sansio App and Scaffold Foundations

**Capability.** Provides the framework-agnostic foundations that the concrete Flask app and blueprints build on: shared scaffold registration, blueprint recording, app base setup and logging.

Come here for the I/O-free base classes behind apps and blueprints. One child holds the scaffold and blueprint registration logic, while the other holds the app base class and logger setup that rely on it.

**Children.**

- [Scaffold and Blueprint Registration](scaffold-and-blueprint-registration.md) `scaffold-and-blueprint-registration` · 43 unit(s)
- [Sansio App Base and Logging](sansio-app-base-and-logging.md) `sansio-app-base-and-logging` · 31 unit(s)

**Depends on.**

- [Command Line and Public Helpers](command-line-and-public-helpers.md) · graph-confirmed · 3 edge(s)
- [Runtime App, Contexts and Testing](runtime-app-contexts-and-testing.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Runtime App, Contexts and Testing](runtime-app-contexts-and-testing.md) · graph-confirmed · 1 edge(s) · 1 inferred relation(s)

Parent: [Flask Web Framework](flask-web-framework.md)

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.
