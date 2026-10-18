# c-ares getaddrinfo shim

**Capability.** A drop-in getaddrinfo/freeaddrinfo replacement built on c-ares, converting ares results into native addrinfo lists via an async callback context.

Read this only when USE_FAKE_GETADDRINFO is relevant; r_getaddrinfo drives the c-ares query, async_addrinfo_cb captures the result, and mk_getaddrinfo/r_freeaddrinfo manage the native-shaped list.

**Depends on.**

- [DNS cache](r11-dnscache.md) · model-inferred · 0 edge(s)

Parent: [DNS resolution](r11-dns-resolution.md)

## Units (5)

<a id="u-32f2853c95f0"></a>
### `fake_addrinfo-module-regions`

`struct context` · [lib/fake_addrinfo.c:L43-L46][f1]

Non-behavioral regions of fake_addrinfo.c: license header, curl_setup/fake_addrinfo includes, the USE_FAKE_GETADDRINFO and ares.h conditional includes, and the struct context definition (a two-field holder for the ares result pointer and status) plus the file's closing conditional guard.

<a id="u-9a3a1ef32f83"></a>
### `async_addrinfo_cb`

`static void async_addrinfo_cb(void *userp, int status, int timeouts, struct ares_addr…` · [lib/fake_addrinfo.c:L48-L57][f1]

c-ares completion callback storing the result into a caller-supplied context struct.

It always records the status code, ignoring timeouts; only on ARES_SUCCESS does it also store the ares_addrinfo pointer, so a failed lookup leaves any prior addr unset (the context is zero-initialized by the caller).

<a id="u-ad88e866e7ee"></a>
### `mk_getaddrinfo`

`static struct addrinfo *mk_getaddrinfo(const struct ares_addrinfo *aihead)` · [lib/fake_addrinfo.c:L60-L130][f1]

Converts a c-ares ares_addrinfo result into a native addrinfo list.

It reads the name from aihead->name and walks aihead->nodes; AF_INET and AF_INET6 elements with a valid ai_addr, positive ai_addrlen, and ai_addrlen at least the family's sockaddr size are each packed into one allocation (struct, sockaddr copy, then canonname copy). The canonname is attached only to the first converted element: after copying, the local name pointer is set to NULL, matching real addrinfo chains where only the head owns the name. Elements of other families or with bogus sizes are skipped. On curlx_malloc failure the partially built list is freed with r_freeaddrinfo and NULL is returned; the caller treats NULL as failure.

calls: [r_freeaddrinfo](r11-fake-resolver.md#u-ee60adef0c2b)

**Uncertainties.**

- If aihead->name itself were NULL the canonname is simply omitted; the source takes the name only from aihead, not per-node names.

<a id="u-ee60adef0c2b"></a>
### `r_freeaddrinfo`

`void r_freeaddrinfo(struct addrinfo *cahead)` · [lib/fake_addrinfo.c:L32-L41][f1]

Frees a system-shape addrinfo list built by this fake resolver: walks ai_next, saving the next pointer before curlx_free of each node.

Mirrors Curl_freeaddrinfo but operates on struct addrinfo. Compiled only under USE_FAKE_GETADDRINFO.

<a id="u-f282d225706a"></a>
### `r_getaddrinfo`

`int r_getaddrinfo(const char *node, const char *service, const struct addrinfo *hints…` · [lib/fake_addrinfo.c:L136-L200][f1]

Drop-in getaddrinfo replacement backed by c-ares, compiled under USE_FAKE_GETADDRINFO, returning 0 on success or EAI_* codes.

It initializes a c-ares channel with the default event-thread system; ares_init_options failure returns EAI_MEMORY. If CURL_DNS_SERVER is set in the environment the channel's servers are set from that CSV string; ares_set_servers_ports_csv failure prints to stderr, destroys the channel, and returns EAI_MEMORY. It copies hints fields (flags, family, socktype, protocol) into ares hints when hints is non-NULL, issues ares_getaddrinfo with async_addrinfo_cb and a zeroed context, and blocks in ares_queue_wait_empty until the queue drains. Afterwards: if the callback stored an address, the result is converted by mk_getaddrinfo, the c-ares data freed with ares_freeaddrinfo, and 0 returned; ARES_ENOTFOUND or ARES_ENODATA yields EAI_NONAME; any other failure yields EAI_AGAIN. The channel is destroyed before returning. Note mk_getaddrinfo's NULL return (its own allocation failure) is not distinguished here from success.

calls: [mk_getaddrinfo](r11-fake-resolver.md#u-ad88e866e7ee), [async_addrinfo_cb](r11-fake-resolver.md#u-9a3a1ef32f83)

**Uncertainties.**

- If mk_getaddrinfo returns NULL after a successful lookup, *res is set to NULL and rc stays 0, so the caller receives a success code with a NULL list; whether that occurs in practice is not provable from this source.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/fake_addrinfo.c
