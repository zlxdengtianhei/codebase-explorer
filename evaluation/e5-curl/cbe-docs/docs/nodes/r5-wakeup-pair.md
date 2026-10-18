# Wakeup Socket Pair

**Capability.** Provides a signalable, pollable fd pair used to wake event loops, with platform backends selected at compile time: eventfd, pipe, AF_UNIX socketpair, and a loopback-TCP fallback verified by a round trip.

Consult when a thread must interrupt a blocking poll. Curl_wakeup_init dispatches to the backend; signal/consume/destroy operate uniformly regardless of which backend was created.

**Depends on.**

- [Polling and Pollsets](r5-poll-waiting.md) · graph-confirmed · 2 edge(s)

Parent: [Event and Concurrency Infrastructure](r5-async-event-infrastructure.md)

## Units (8)

<a id="u-206f56c660d8"></a>
### `Curl_wakeup_consume`

`CURLcode Curl_wakeup_consume(curl_socket_t socks[2], bool all)` · [lib/socketpair.c:L343-L366][f1]

Drains pending wakeup data from socks[0] in 64-byte reads.

A read of 0 or EAGAIN stops the loop; EINTR retries (non-Windows); any other read error stops with CURLE_READ_ERROR. When all is true the loop repeats until a terminal condition above, draining everything currently readable; when false it stops after the first successful read. Returns CURLE_OK when drained or paused on EAGAIN.

uses: [Curl_wakeup_signal](r5-wakeup-pair.md#u-c2cd5b0fb0eb)

**Uncertainties.**

- Whether a partial 64-byte chunk leaves additional data unread when all is false depends on the writer's payload size, not visible here.

<a id="u-a1f59a1fa99f"></a>
### `Curl_wakeup_destroy`

`void Curl_wakeup_destroy(curl_socket_t socks[2])` · [lib/socketpair.c:L368-L377][f1]

Closes the wakeup pair and marks it unusable.

With eventfd both ends are the same descriptor, so only socks[0] is closed; otherwise socks[1] is closed first if valid, then socks[0]. Both entries are always reset to CURL_SOCKET_BAD. The graph links calls to Curl_if2ip here, but no such call appears in the supplied body, so that edge is treated as unverifiable.

**Uncertainties.**

- Graph evidence claims two calls to Curl_if2ip (lib/if2ip.c:222) from this function, contradicting the supplied source, which contains only close logic; recorded as unresolved.

<a id="u-d85b819d30ce"></a>
### `Curl_wakeup_init`

`int Curl_wakeup_init(curl_socket_t socks[2], bool nonblocking)` · [lib/socketpair.c:L291-L302][f1]

Dispatches wakeup-pair creation to the platform implementation selected at compile time: eventfd, pipe, AF_UNIX socketpair, or the loopback-TCP fallback, forwarding socks and nonblocking and returning the callee's 0/-1 result.

calls: [wakeup_eventfd](r5-wakeup-pair.md#u-44a24fb1a45d), [wakeup_pipe](r5-wakeup-pair.md#u-557999bc2988), [wakeup_socketpair](r5-wakeup-pair.md#u-142cd23fe229), [lib/socketpair.c:wakeup_inet](r5-wakeup-pair.md#u-c7870c0f2f94)

<a id="u-c2cd5b0fb0eb"></a>
### `Curl_wakeup_signal`

`int Curl_wakeup_signal(curl_socket_t socks[2])` · [lib/socketpair.c:L318-L341][f1]

Signals a wakeup by writing one unit (uint64_t 1 for eventfd, one byte otherwise) to socks[1].

The write retries on EINTR (non-Windows). On EAGAIN the error is cleared because a wakeup is already pending; any other write error's errno is returned, so success and already-signalled both yield 0.

**Notes.**

- condition: eventfd writes must be 8 bytes, hence the uint64_t buffer under USE_EVENTFD.

<a id="u-44a24fb1a45d"></a>
### `wakeup_eventfd`

`static int wakeup_eventfd(curl_socket_t socks[2], bool nonblocking)` · [lib/socketpair.c:L38-L47][f1]

Creates a single Linux eventfd used as both ends of a wakeup pair.

On eventfd failure it sets both socks entries to CURL_SOCKET_BAD and returns -1; on success both entries hold the same descriptor and it returns 0. The nonblocking flag selects EFD_NONBLOCK alongside EFD_CLOEXEC.

<a id="u-c7870c0f2f94"></a>
### `lib/socketpair.c:wakeup_inet`

`static int wakeup_inet(curl_socket_t socks[2], bool nonblocking)` · [lib/socketpair.c:L163-L287][f1]

Last-resort wakeup pair built from a loopback TCP connection: it creates a TCP listener on 127.0.0.1 with an ephemeral port, connects socks[0] to it, accepts socks[1] with a bounded poll, then verifies the link by writing 9 random bytes from socks[0] and reading them back from socks[1].

Address options differ by platform: non-Windows sets SO_REUSEADDR; Windows/Cygwin skips it and sets SO_EXCLUSIVEADDRUSE when available. Accept readiness waits at most one second via Curl_poll; after accept, the read loop polls up to one second per iteration and aborts if 60 seconds elapse overall. Read results: 0 (early close) fails; EAGAIN/EINTR/EINPROGRESS retry; other errors fail; partial reads advance the buffer; a full read is compared with memcmp and a mismatch fails. If nonblocking is requested, both ends are set nonblocking at the end, and SIGPIPE is suppressed on socks[1] under USE_SO_NOSIGPIPE. Success closes the listener and returns 0 with socks[0]/socks[1] holding the connected pair; any goto error closes listener and both socks, resets them to CURL_SOCKET_BAD, and returns -1.

**Notes.**

- failure: The single 'error' label performs uniform cleanup: close listener, close both socks, set them to CURL_SOCKET_BAD, return -1.
- side_effect: Curl_rand(NULL, ...) consumes random data to seed the connectivity check.

calls: [curlx_nonblock](r12-socket-and-buffer-utils.md#u-3b381dd4a464), [Curl_poll](r5-poll-waiting.md#u-23ac2d5b40d4), [curlx_now](r9-time-utils.md#u-1e54794baf3b), [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3), [Curl_rand_bytes](r10-misc-utilities.md#u-c3e86a9c4806); uses: [if2ip.c-curl_if2ip](r15-net-platform-helpers.md#u-a63d70f925b1)

**Uncertainties.**

- The graph reports four calls to Curl_if2ip from this function, but no call site is visible in the supplied source; whether this function actually invokes it cannot be confirmed here.
- swrite and sread return values: swrite result is deliberately ignored; behavior on short write is unverified because only the read side loops.

<a id="u-557999bc2988"></a>
### `wakeup_pipe`

`static int wakeup_pipe(curl_socket_t socks[2], bool nonblocking)` · [lib/socketpair.c:L55-L96][f1]

Creates a pipe as a wakeup pair, preferring atomic pipe2.

Compile-time variants: with HAVE_PIPE2 it calls pipe2 with O_CLOEXEC plus O_NONBLOCK when nonblocking, returning -1 on failure; on Apple targets with the availability guards it uses pipe2 only when the OS provides it. Otherwise it falls back to pipe() (returning -1 if that fails), then sets FD_CLOEXEC on both ends via fcntl when HAVE_FCNTL, and when nonblocking and SOCK_NONBLOCK was not built in, sets nonblocking mode on both ends with curlx_nonblock. Any fcntl or nonblock failure closes both ends, resets socks to CURL_SOCKET_BAD, and returns -1.

**Notes.**

- side_effect: All failure paths after pipe creation close both descriptors and leave socks set to CURL_SOCKET_BAD.

calls: [curlx_nonblock](r12-socket-and-buffer-utils.md#u-3b381dd4a464)

**Uncertainties.**

- sclose and Curl_sock_nosigpipe behavior are external to this file.

<a id="u-142cd23fe229"></a>
### `wakeup_socketpair`

`static int wakeup_socketpair(curl_socket_t socks[2], bool nonblocking)` · [lib/socketpair.c:L104-L138][f1]

Creates an AF_UNIX SOCK_STREAM socket pair as a wakeup pair.

SOCK_CLOEXEC is added when available; when CURL_USE_SOCK_NONBLOCK is defined and nonblocking is set, SOCK_NONBLOCK is added atomically, otherwise nonblocking mode is applied afterwards on both ends via curlx_nonblock, with failure closing both sockets, resetting socks to CURL_SOCKET_BAD, and returning -1. When USE_SO_NOSIGPIPE is defined, Curl_sock_nosigpipe on socks[1] failing triggers the same cleanup-and-fail path. CURL_SOCKETPAIR failure returns -1 directly. A build without Unix sockets hits a compile-time #error.

calls: [curlx_nonblock](r12-socket-and-buffer-utils.md#u-3b381dd4a464)

**Uncertainties.**

- Exact behavior of CURL_SOCKETPAIR macro (retry-on-EINTR wrappers etc.) is defined elsewhere.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/socketpair.c
