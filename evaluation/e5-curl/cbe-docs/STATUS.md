# CBE run status

Run `03f6c1` · status **complete** · updated 2026-10-18T05:56:03Z · review sample · jobs 2 · host api

Semantic review: mode **sample**; 1/1 reviewed by a separate reader of the source. This is independent of the deterministic structure/coverage checks and does not prove whole-map truth.

Counts: done 208

id_corrected 17

- module_10: ` lib/select.c::function::cpfds_add_sock::11025 ` → ` lib/select.c::function::cpfds_add_sock::11520 ` (units[24].id)
- module_10: ` lib/select.c::function::cpfds_add_sock::11025 ` → ` lib/select.c::function::cpfds_add_sock::11520 ` (dispositions[lib/select.c::function::cpfds_increase::11025].unit)
- module_10: ` lib/select.c::function::cpfds_add_sock::11025 ` → ` lib/select.c::function::cpfds_add_sock::11520 ` (dispositions[lib/select.c::function::cpfds_add_sock::11520].unit)
- module_111: ` lib/socks.c::function::socks5_connect::13303 ` → ` lib/socks.c::function::socks5_connect::31368 ` (dispositions[lib/socks.c::function::socks5_connect::13303] key)
- module_117: ` lib/thrdqueue.c::function::thrdq_item_destroy::2427 ` → ` lib/thrdqueue.c::function::thrdq_item_destroy::2431 ` (units[20].id)
- module_117: ` lib/thrdqueue.c::function::thrdq_item_destroy::2427 ` → ` lib/thrdqueue.c::function::thrdq_item_destroy::2431 ` (units[22].relations[0].target)
- module_117: ` lib/thrdqueue.c::function::thrdq_item_destroy::2427 ` → ` lib/thrdqueue.c::function::thrdq_item_destroy::2431 ` (dispositions[lib/thrdqueue.c::function::thrdq_item_destroy::2427].unit)
- module_117: ` lib/thrdqueue.c::function::thrdq_item_destroy::2427 ` → ` lib/thrdqueue.c::function::thrdq_item_destroy::2431 ` (dispositions[lib/thrdqueue.c::function::thrdq_item_destroy::2427] key)
- module_156: ` lib/vauth/spnego_sspi.c::function::Curl_auth_decode_spnego_message::2335 ` → ` lib/vauth/spnego_sspi.c::function::Curl_auth_decode_spnego_message::2605 ` (units[12].id)
- module_156: ` lib/vauth/spnego_sspi.c::function::Curl_auth_decode_spnego_message::2335 ` → ` lib/vauth/spnego_sspi.c::function::Curl_auth_decode_spnego_message::2605 ` (dispositions[lib/vauth/spnego_sspi.c::function::Curl_auth_decode_spnego_message::2335].unit)
- module_156: ` lib/vauth/spnego_sspi.c::function::Curl_auth_decode_spnego_message::2335 ` → ` lib/vauth/spnego_sspi.c::function::Curl_auth_decode_spnego_message::2605 ` (dispositions[lib/vauth/spnego_sspi.c::function::Curl_auth_decode_spnego_message::2335] key)
- module_161: ` lib/vdns/asyn-thrdd.c::function::Curl_async_pollset::698 ` → ` lib/vdns/asyn-thrdd.c::function::Curl_async_pollset::19190 ` (units[23].id)
- module_95: ` lib/pop3.c::function::pop3_state_starttls_resp::960 ` → ` lib/pop3.c::function::pop3_state_starttls_resp::26244 ` (units[23].id)
- module_95: ` lib/pop3.c::function::pop3_state_starttls_resp::960 ` → ` lib/pop3.c::function::pop3_state_starttls_resp::26244 ` (dispositions[lib/pop3.c::function::pop3_state_starttls_resp::26244].unit)
- repair_175: ` lib/vtls/openssl.c::function::use_privatekey_blob::25170-placeholder ` → ` lib/vtls/openssl.c::function::use_privatekey_blob::25989 ` (units[8].id)
- repair_175: ` lib/vtls/openssl.c::function::load_cacert_from_memory::2794-placeholder ` → ` lib/vtls/openssl.c::function::load_cacert_from_memory::79788 ` (units[35].id)
- repair_175: ` lib/vtls/openssl.c::function::ossl_set_cached_x509_store::96360-placeholder ` → ` lib/vtls/openssl.c::function::ossl_set_cached_x509_store::97127 ` (units[44].id)

index_only_filled 2

- module_117: ` lib/thrdqueue.c::module_residual::::10966 ` (invalid)
- module_160: ` lib/vdns/dnscache.c::function::Curl_dnscache_add_negative.if::23206 ` (missing)

answer_fallback 4

- module_10: accepted attempt 2 (final attempt 3)
- module_156: accepted attempt 2 (final attempt 3)
- module_160: accepted attempt 2 (final attempt 3)
- repair_175: accepted attempt 2 (final attempt 3)

| Task | Module | State | Attempts | Seconds | Output | Note |
|---|---|---|---:|---:|---|---|
| names |  | done | 1 | 47.0 | host/accepted/names.json |  |
| module_1 | Alternative services tracking and curl-native file access | done | 2 | 116.0 | host/accepted/module_1.json |  |
| module_2 | AmigaOS platform support | done | 1 | 48.0 | host/accepted/module_2.json |  |
| module_3 | API entry helpers and threading primitives | done | 1 | 205.0 | host/accepted/module_3.json |  |
| module_4 | Telnet protocol option definitions | done | 1 | 92.0 | host/accepted/module_4.json |  |
| module_5 | Buffer queue and receive buffer management | done | 1 | 134.0 | host/accepted/module_5.json |  |
| module_6 | LDAP protocol and buffer reference utilities | done | 2 | 127.0 | host/accepted/module_6.json |  |
| module_7 | HTTP/1 proxy filter with string case helpers | done | 3 | 101.0 | host/accepted/module_7.json |  |
| module_8 | HTTP/2 proxy connection filter | done | 1 | 130.0 | host/accepted/module_8.json |  |
| module_9 | HTTP proxy tunneling and dynamic header handling | done | 1 | 101.0 | host/accepted/module_9.json |  |
| module_10 | HAProxy protocol filter and select/poll wrappers | done | 3 | 132.0 | host/accepted/module_10.json | normalized (51); id_corrected 3; answer_fallback attempt 2 |
| module_11 | Connection filter and tracing declarations | done | 1 | 129.0 | host/accepted/module_11.json |  |
| module_12 | HTTPS connect filter and multi interface hooks | done | 1 | 126.0 | host/accepted/module_12.json |  |
| module_13 | Happy eyeballs IP connection filter | done | 1 | 128.0 | host/accepted/module_13.json |  |
| module_14 | Connection filter setup helpers | done | 1 | 74.0 | host/accepted/module_14.json |  |
| module_15 | Socket connection filter implementation | done | 2 | 178.0 | host/accepted/module_15.json |  |
| module_16 | Connection filter core, URL and error string declarations | done | 1 | 150.0 | host/accepted/module_16.json |  |
| module_17 | Connection filter API and pause writer | done | 3 | 69.0 | host/accepted/module_17.json |  |
| module_18 | Mac platform configuration | done | 1 | 28.0 | host/accepted/module_18.json |  |
| module_19 | OS/400 platform configuration | done | 2 | 32.0 | host/accepted/module_19.json |  |
| module_20 | Windows platform configuration | done | 1 | 41.0 | host/accepted/module_20.json |  |
| module_21 | Connection cache management and share declarations | done | 2 | 120.0 | host/accepted/module_21.json |  |
| module_22 | Connection establishment with integer set/table utilities | done | 2 | 114.0 | host/accepted/module_22.json |  |
| module_23 | Connect setup and content encoding decoding | done | 1 | 112.0 | host/accepted/module_23.json |  |
| module_24 | Cookie engine | done | 1 | 118.0 | host/accepted/module_24.json |  |
| module_25 | Cookie engine declarations | done | 1 | 43.0 | host/accepted/module_25.json |  |
| module_26 | Credential handling | done | 1 | 57.0 | host/accepted/module_26.json |  |
| module_27 | Connection shutdown, pointer arrays and SIGPIPE handling | done | 2 | 148.0 | host/accepted/module_27.json |  |
| module_28 | Address info construction and fake resolver | done | 1 | 101.0 | host/accepted/module_28.json |  |
| module_29 | Peer address resolution and IDN declarations | done | 1 | 120.0 | host/accepted/module_29.json |  |
| module_30 | Character classification helpers | done | 1 | 58.0 | host/accepted/module_30.json |  |
| module_31 | HTTP message signatures, ed25519 keys and linked lists | done | 2 | 107.0 | host/accepted/module_31.json |  |
| module_32 | Endian conversion helpers | done | 2 | 64.0 | host/accepted/module_32.json |  |
| module_33 | Filename pattern matching | done | 1 | 75.0 | host/accepted/module_33.json |  |
| module_34 | Line reading, tracing declarations and netrc support | done | 2 | 134.0 | host/accepted/module_34.json |  |
| module_35 | Local hostname lookup | done | 1 | 32.0 | host/accepted/module_35.json |  |
| module_36 | GSSAPI shared helpers | done | 1 | 90.0 | host/accepted/module_36.json |  |
| module_37 | GSSAPI declarations and SOCKS5 GSS-API proxy | done | 1 | 72.0 | host/accepted/module_37.json |  |
| module_38 | MD5 and SHA digest interfaces | done | 2 | 120.0 | host/accepted/module_38.json |  |
| module_39 | NTLM core support and HTTP NTLM authentication | done | 2 | 113.0 | host/accepted/module_39.json |  |
| module_40 | Reverse memory search helper | done | 1 | 92.0 | host/accepted/module_40.json |  |
| module_41 | URL escaping and printf abstraction | done | 1 | 85.0 | host/accepted/module_41.json |  |
| module_42 | Range parsing and FILE:// protocol | done | 1 | 86.0 | host/accepted/module_42.json |  |
| module_43 | SASL authentication framework | done | 1 | 121.0 | host/accepted/module_43.json |  |
| module_44 | Build configuration definitions | done | 1 | 47.0 | host/accepted/module_44.json |  |
| module_45 | SHA-512/256 digest implementation | done | 3 | 98.0 | host/accepted/module_45.json | normalized (12) |
| module_46 | Share interface implementation | done | 1 | 87.0 | host/accepted/module_46.json |  |
| module_47 | Windows SSPI support and SSPI-based SOCKS proxy | done | 1 | 77.0 | host/accepted/module_47.json |  |
| module_48 | Output writer, Gopher protocol and send declarations | done | 2 | 117.0 | host/accepted/module_48.json |  |
| module_49 | DICT protocol | done | 1 | 36.0 | host/accepted/module_49.json |  |
| module_50 | Protocol handler registry and protocol declarations | done | 1 | 73.0 | host/accepted/module_50.json |  |
| module_51 | Windows DLL entry point | done | 1 | 41.0 | host/accepted/module_51.json |  |
| module_52 | Dynamic header list implementation | done | 1 | 72.0 | host/accepted/module_52.json |  |
| module_53 | Easy interface implementation | done | 1 | 162.0 | host/accepted/module_53.json |  |
| module_54 | Version reporting and lock primitives | done | 1 | 80.0 | host/accepted/module_54.json |  |
| module_55 | Easy option parsing and option tables | done | 1 | 82.0 | host/accepted/module_55.json |  |
| module_56 | Easy interface declarations | done | 2 | 50.0 | host/accepted/module_56.json |  |
| module_57 | File metadata and FTP list parsing with linked list declarations | done | 1 | 167.0 | host/accepted/module_57.json |  |
| module_58 | Multipart form and MIME data construction | done | 1 | 95.0 | host/accepted/module_58.json |  |
| module_59 | PING/PONG command-response protocol framework | done | 1 | 105.0 | host/accepted/module_59.json |  |
| module_60 | FTP protocol implementation | done | 3 | 277.0 | host/accepted/module_60.json |  |
| module_61 | FTP protocol declarations | done | 1 | 24.0 | host/accepted/module_61.json |  |
| module_62 | FTP list parser declarations | done | 1 | 31.0 | host/accepted/module_62.json |  |
| module_63 | Protocol function type definitions | done | 1 | 21.0 | host/accepted/module_63.json |  |
| module_64 | Environment variable retrieval | done | 1 | 25.0 | host/accepted/module_64.json |  |
| module_65 | Transfer information reporting | done | 2 | 66.0 | host/accepted/module_65.json |  |
| module_66 | Transfer handling and option/HSTS/RTSP declarations | done | 1 | 150.0 | host/accepted/module_66.json |  |
| module_67 | Hash table implementation | done | 1 | 81.0 | host/accepted/module_67.json |  |
| module_68 | Hash declarations and multi-handle event infrastructure | done | 2 | 131.0 | host/accepted/module_68.json |  |
| module_69 | HTTP header collection and callback API | done | 1 | 92.0 | host/accepted/module_69.json |  |
| module_70 | HMAC digest implementation | done | 1 | 39.0 | host/accepted/module_70.json |  |
| module_71 | HSTS policy handling | done | 2 | 80.0 | host/accepted/module_71.json |  |
| module_72 | HTTP protocol implementation | done | 1 | 344.0 | host/accepted/module_72.json |  |
| module_73 | HTTP/1.x message parsing and sending | done | 1 | 51.0 | host/accepted/module_73.json |  |
| module_74 | HTTP/2 protocol implementation | done | 1 | 280.0 | host/accepted/module_74.json |  |
| module_75 | AWS SigV4 request signing | done | 2 | 112.0 | host/accepted/module_75.json |  |
| module_76 | HTTP chunked transfer encoding decoding | done | 1 | 90.0 | host/accepted/module_76.json |  |
| module_77 | Chunked encoding declarations | done | 1 | 79.0 | host/accepted/module_77.json |  |
| module_78 | HTTP Digest authentication | done | 1 | 65.0 | host/accepted/module_78.json |  |
| module_79 | HTTP Negotiate (SPNEGO) authentication | done | 1 | 54.0 | host/accepted/module_79.json |  |
| module_80 | Internationalized domain name handling | done | 1 | 85.0 | host/accepted/module_80.json |  |
| module_81 | Interface to IP address mapping | done | 1 | 85.0 | host/accepted/module_81.json |  |
| module_82 | IMAP protocol implementation | done | 1 | 299.0 | host/accepted/module_82.json |  |
| module_83 | IMAP protocol declarations | done | 2 | 31.0 | host/accepted/module_83.json |  |
| module_84 | Linked list implementation | done | 3 | 59.0 | host/accepted/module_84.json |  |
| module_85 | Classic Mac OS platform support | done | 1 | 55.0 | host/accepted/module_85.json |  |
| module_86 | MD4 digest implementation | done | 1 | 79.0 | host/accepted/module_86.json |  |
| module_87 | Memory allocation debug tracing | done | 1 | 121.0 | host/accepted/module_87.json |  |
| module_88 | MIME/form data engine implementation | done | 5 | 231.0 | host/accepted/module_88.json |  |
| module_89 | printf-style formatting engine | done | 1 | 159.0 | host/accepted/module_89.json |  |
| module_90 | MQTT protocol and random declarations | done | 2 | 129.0 | host/accepted/module_90.json |  |
| module_91 | Multi interface event engine | done | 3 | 357.0 | host/accepted/module_91.json |  |
| module_92 | Multi interface notifications | done | 2 | 58.0 | host/accepted/module_92.json |  |
| module_93 | LDAP protocol via OpenLDAP | done | 2 | 122.0 | host/accepted/module_93.json |  |
| module_94 | Date and time parsing | done | 1 | 82.0 | host/accepted/module_94.json |  |
| module_95 | POP3 protocol implementation | done | 3 | 133.0 | host/accepted/module_95.json | normalized (40); id_corrected 2 |
| module_96 | Transfer progress, PSL and transfer declarations | done | 2 | 101.0 | host/accepted/module_96.json |  |
| module_97 | Proxy configuration and resolution | done | 1 | 65.0 | host/accepted/module_97.json |  |
| module_98 | Public Suffix List declarations | done | 1 | 17.0 | host/accepted/module_98.json |  |
| module_99 | Random number generation | done | 1 | 31.0 | host/accepted/module_99.json |  |
| module_100 | Transfer rate limiting | done | 1 | 97.0 | host/accepted/module_100.json |  |
| module_101 | Per-request state management | done | 1 | 97.0 | host/accepted/module_101.json |  |
| module_102 | RTSP protocol implementation | done | 2 | 105.0 | host/accepted/module_102.json |  |
| module_103 | Send/receive and data formatting | done | 2 | 180.0 | host/accepted/module_103.json |  |
| module_104 | Easy option setting | done | 2 | 213.0 | host/accepted/module_104.json |  |
| module_105 | OS/400 platform setup | done | 1 | 19.0 | host/accepted/module_105.json |  |
| module_106 | VMS platform setup | done | 1 | 42.0 | host/accepted/module_106.json |  |
| module_107 | Windows platform setup | done | 1 | 86.0 | host/accepted/module_107.json |  |
| module_108 | SHA-256 digest implementation | done | 1 | 85.0 | host/accepted/module_108.json |  |
| module_109 | SMTP protocol implementation | done | 3 | 175.0 | host/accepted/module_109.json |  |
| module_110 | Socketpair helper | done | 1 | 58.0 | host/accepted/module_110.json |  |
| module_111 | SOCKS proxy support | done | 3 | 97.0 | host/accepted/module_111.json | normalized (35); id_corrected 1 |
| module_112 | Splay tree implementation | done | 2 | 68.0 | host/accepted/module_112.json |  |
| module_113 | Case-insensitive string comparison | done | 1 | 30.0 | host/accepted/module_113.json |  |
| module_114 | Error message strings | done | 3 | 32.0 | host/accepted/module_114.json |  |
| module_115 | Telnet protocol implementation | done | 1 | 134.0 | host/accepted/module_115.json |  |
| module_116 | TFTP protocol implementation | done | 1 | 120.0 | host/accepted/module_116.json |  |
| module_117 | Thread pool and thread-safe queue | done | 3 | 149.0 | host/accepted/module_117.json | normalized (38); id_corrected 4; index_only_filled 1 |
| module_118 | 32-bit key pointer set | done | 1 | 60.0 | host/accepted/module_118.json |  |
| module_119 | 8-bit key string set | done | 2 | 71.0 | host/accepted/module_119.json |  |
| module_120 | Sparse bitset implementation | done | 1 | 73.0 | host/accepted/module_120.json |  |
| module_121 | Integer-keyed table implementation | done | 1 | 70.0 | host/accepted/module_121.json |  |
| module_122 | URL parsing and connection setup orchestration | done | 3 | 198.0 | host/accepted/module_122.json |  |
| module_123 | URL parsing API implementation | done | 1 | 185.0 | host/accepted/module_123.json |  |
| module_124 | Central curl data structures | done | 1 | 81.0 | host/accepted/module_124.json |  |
| module_125 | WebSocket protocol implementation | done | 2 | 192.0 | host/accepted/module_125.json |  |
| module_126 | WebSocket declarations | done | 1 | 17.0 | host/accepted/module_126.json |  |
| module_127 | Base64, error strings and Windows fopen helpers | done | 1 | 93.0 | host/accepted/module_127.json |  |
| module_128 | Dynamic buffers, string parsing and time helpers | done | 2 | 127.0 | host/accepted/module_128.json |  |
| module_129 | Network address conversion and portable utility helpers | done | 2 | 126.0 | host/accepted/module_129.json |  |
| module_130 | Portable string, socket and system utility library | done | 1 | 88.0 | host/accepted/module_130.json |  |
| module_131 | Public libcurl API header | done | 1 | 174.0 | host/accepted/module_131.json |  |
| module_132 | GCC compile-time option type checking | done | 1 | 39.0 | host/accepted/module_132.json |  |
| module_133 | Easy and multi interface public headers with system types | done | 2 | 47.0 | host/accepted/module_133.json |  |
| module_134 | Public headers for versioning, headers API, printf and URL/WebSocket APIs | done | 1 | 100.0 | host/accepted/module_134.json |  |
| module_135 | curl command-line parameter parsing | done | 2 | 154.0 | host/accepted/module_135.json |  |
| module_136 | curl transfer operation execution | done | 2 | 207.0 | host/accepted/module_136.json |  |
| module_137 | Config file to option mapping | done | 1 | 143.0 | host/accepted/module_137.json |  |
| module_138 | Header and read callbacks with configuration declarations | done | 1 | 152.0 | host/accepted/module_138.json |  |
| module_139 | curl main entry, URL globbing and platform stderr | done | 1 | 100.0 | host/accepted/module_139.json |  |
| module_140 | Form parsing, config file and message declarations | done | 1 | 121.0 | host/accepted/module_140.json |  |
| module_141 | Parameter helpers and tool declarations | done | 2 | 161.0 | host/accepted/module_141.json |  |
| module_142 | Write-out formatting including JSON output | done | 1 | 104.0 | host/accepted/module_142.json |  |
| module_143 | Terminal handling and help text listing | done | 1 | 68.0 | host/accepted/module_143.json |  |
| module_144 | Windows/DOS filename handling and utility functions | done | 1 | 124.0 | host/accepted/module_144.json |  |
| module_145 | Password prompting and option setting for the tool | done | 1 | 112.0 | host/accepted/module_145.json |  |
| module_146 | Tool configuration, IPFS gateway and variable expansion | done | 1 | 116.0 | host/accepted/module_146.json |  |
| module_147 | Write callbacks, file lookup and config file reading | done | 1 | 113.0 | host/accepted/module_147.json |  |
| module_148 | Debug callbacks, directory creation, help and SSL session persistence | done | 5 | 108.0 | host/accepted/module_148.json |  |
| module_149 | Progress display and extended attribute handling | done | 1 | 102.0 | host/accepted/module_149.json |  |
| module_150 | Wide-character list and operation helper utilities | done | 1 | 104.0 | host/accepted/module_150.json |  |
| module_151 | Read and socket callbacks, messages and VMS support | done | 1 | 69.0 | host/accepted/module_151.json |  |
| module_152 | Tool time parsing and formatting helpers | done | 1 | 14.0 | host/accepted/module_152.json |  |
| module_153 | Digest and GSASL authentication | done | 2 | 88.0 | host/accepted/module_153.json |  |
| module_154 | NTLM authentication core and auth framework | done | 1 | 93.0 | host/accepted/module_154.json |  |
| module_155 | Cleartext and SSPI-based digest/krb5 authentication | done | 2 | 72.0 | host/accepted/module_155.json |  |
| module_156 | SSPI NTLM, OAuth2 and SPNEGO authentication | done | 3 | 54.0 | host/accepted/module_156.json | normalized (14); id_corrected 3; answer_fallback attempt 2 |
| module_157 | CRAM-MD5, GSSAPI Kerberos and auth declarations | done | 3 | 76.0 | host/accepted/module_157.json |  |
| module_158 | DNS-over-HTTPS resolver | done | 3 | 116.0 | host/accepted/module_158.json |  |
| module_159 | Host name to address resolution core | done | 2 | 107.0 | host/accepted/module_159.json |  |
| module_160 | DNS cache with filter declarations | done | 3 | 130.0 | host/accepted/module_160.json | normalized (19); answer_fallback attempt 2; index_only_filled 1 |
| module_161 | Threaded resolver and HTTPS resource records | done | 3 | 150.0 | host/accepted/module_161.json | normalized (38); id_corrected 1 |
| module_162 | c-ares async resolver and async base | done | 2 | 126.0 | host/accepted/module_162.json |  |
| module_163 | DNS filter and IPv4 host resolution | done | 1 | 112.0 | host/accepted/module_163.json |  |
| module_164 | Async resolver declarations and IPv6/HTTPS RR support | done | 2 | 33.0 | host/accepted/module_164.json |  |
| module_165 | Shared ngtcp2 connection filter code | done | 1 | 216.0 | host/accepted/module_165.json |  |
| module_166 | QUIC via quiche backend | done | 1 | 165.0 | host/accepted/module_166.json |  |
| module_167 | QUIC common support code | done | 1 | 142.0 | host/accepted/module_167.json |  |
| module_168 | QUIC proxy tunneling via ngtcp2 | done | 2 | 138.0 | host/accepted/module_168.json |  |
| module_169 | QUIC via ngtcp2 backend | done | 1 | 96.0 | host/accepted/module_169.json |  |
| module_170 | WebTransport capsules and QUIC TLS support | done | 2 | 106.0 | host/accepted/module_170.json |  |
| module_171 | QUIC backend declarations | done | 2 | 37.0 | host/accepted/module_171.json |  |
| module_172 | SFTP/SCP via libssh2 backend | done | 1 | 239.0 | host/accepted/module_172.json |  |
| module_173 | SFTP/SCP via libssh backend | done | 1 | 222.0 | host/accepted/module_173.json |  |
| module_174 | SSH common framework | done | 2 | 50.0 | host/accepted/module_174.json |  |
| module_175 | TLS via OpenSSL backend | done | 3 | 255.0 | host/accepted/module_175.json |  |
| module_176 | TLS via Windows Schannel backend | done | 2 | 186.0 | host/accepted/module_176.json |  |
| module_177 | TLS via wolfSSL backend | done | 2 | 176.0 | host/accepted/module_177.json |  |
| module_178 | TLS via GnuTLS backend | done | 3 | 165.0 | host/accepted/module_178.json |  |
| module_179 | TLS via mbedTLS backend | done | 2 | 133.0 | host/accepted/module_179.json |  |
| module_180 | TLS layer common engine | done | 1 | 218.0 | host/accepted/module_180.json |  |
| module_181 | Cipher suite name mapping | done | 1 | 58.0 | host/accepted/module_181.json |  |
| module_182 | TLS via rustls backend | done | 3 | 107.0 | host/accepted/module_182.json |  |
| module_183 | TLS session cache | done | 2 | 113.0 | host/accepted/module_183.json |  |
| module_184 | X.509 ASN.1 certificate parsing | done | 2 | 102.0 | host/accepted/module_184.json |  |
| module_185 | Certificate verification and TLS session packing | done | 1 | 85.0 | host/accepted/module_185.json |  |
| module_186 | Apple TLS backend and vtls configuration | done | 1 | 99.0 | host/accepted/module_186.json |  |
| module_187 | TLS backend internal declarations | done | 1 | 45.0 | host/accepted/module_187.json |  |
| module_188 | TLS backend declarations and host/key checks | done | 2 | 40.0 | host/accepted/module_188.json |  |
| repair_175 | TLS via OpenSSL backend | done | 3 | 292.0 | host/accepted/repair_175.json | normalized (139); id_corrected 3; answer_fallback attempt 2 |
| tree |  | done | 3 | 24.0 | host/accepted/tree.json |  |
| tree_region-0001 |  | done | 1 | 142.0 | host/accepted/tree_region-0001.json |  |
| tree_region-0002 |  | done | 2 | 189.0 | host/accepted/tree_region-0002.json |  |
| tree_region-0003 |  | done | 1 | 171.0 | host/accepted/tree_region-0003.json |  |
| tree_region-0004 |  | done | 1 | 216.0 | host/accepted/tree_region-0004.json |  |
| tree_region-0005 |  | done | 1 | 157.0 | host/accepted/tree_region-0005.json |  |
| tree_region-0006 |  | done | 2 | 89.0 | host/accepted/tree_region-0006.json |  |
| tree_region-0007 |  | done | 1 | 194.0 | host/accepted/tree_region-0007.json |  |
| tree_region-0008 |  | done | 1 | 193.0 | host/accepted/tree_region-0008.json |  |
| tree_region-0009 |  | done | 2 | 119.0 | host/accepted/tree_region-0009.json | normalized (1) |
| tree_region-0010 |  | done | 2 | 233.0 | host/accepted/tree_region-0010.json | normalized (2) |
| tree_region-0011 |  | done | 1 | 213.0 | host/accepted/tree_region-0011.json |  |
| tree_region-0012 |  | done | 2 | 192.0 | host/accepted/tree_region-0012.json | normalized (1) |
| tree_region-0013 |  | done | 2 | 63.0 | host/accepted/tree_region-0013.json |  |
| tree_region-0014 |  | done | 1 | 164.0 | host/accepted/tree_region-0014.json |  |
| tree_region-0015 |  | done | 2 | 153.0 | host/accepted/tree_region-0015.json |  |
| review_175 | TLS via OpenSSL backend | done | 1 | 81.0 | host/accepted/review_175.json |  |
| system |  | done | 2 | 39.0 | host/accepted/system.json |  |
