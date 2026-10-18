# cbe-q13b（B 半）跳过与未用锚点

## 跳过（按顺序轮到、但没出题）

| 锚点 id | 函数 | 区域 | 原因 |
|---|---|---|---|
| a4f4ce1ef4e35 | multissl_recv_plain | tls | 一行转发（multissl_setup 后转 Curl_ssl->recv_plain）。TLS 过滤器在 cf_ctx_new 里把 ssl_impl 绑到当时的 Curl_ssl，而全局初始化（multissl_init）已选定具体后端，所以正常路径不经过这个包装。能出的 L4 题要么靠源码里没有注释支撑的推断（例如“为什么要有这层包装”“placeholder 表 sizeof=(size_t)-1 的用意”），要么和 B13（multissl_random 的分派与后端选择）重复。按顺序改用同区下一个锚点。 |

## 未用（区内额度已满，按固定顺序没轮到）

- pool（额度 6，用前 6 个）：aff41121226d2 curl_share_setopt
- protocols（额度 6，用前 6 个）：a28b6e79a77c9 ftp_port_default_host
- tls（额度 4，跳过 1 个后用到第 5 个）：a78461d61540b multissl_init、a17dc4a0dbb90 Curl_ssl_version
- dns（额度 4，用前 4 个）：adabbeecb7e4c Curl_dnscache_clear、ac8c002a495eb Curl_conn_dns_add_addr_resolve、a6e50676b10fb Curl_async_thrdd_multi_set_props
- persistence（额度 4，用前 4 个）：a81b15e149445 Curl_altsvc_load、a63e1d4d941db cookiehash、adbb046810ffb altsvc_debugtime
- public_api（额度 4，用前 4 个）：a0b22ec49dc1f curl_url_cleanup、a91eea9902a18 curl_mime_name、acefcf32d64ce curl_slist_append

## 题面层与卡上建议层不同的锚点（为凑配额格，按清单说明“建议层不是最终题面标签”）

- ace5a1d789e47 Curl_secure_context：建议 1 → 出成 L3 Where（http.c → cookie.c → transfer.c）
- a77bd2e79a822 Curl_cookie_run：建议 2 → L2（一致）
- a59964a32bc82 curl_mime_init：建议 4 → L2 Where
- a24e4410170f4 curl_mime_free：建议 2 → L2 Why
- adc6e9adf6f3b curl_multi_socket：建议 3 → L4 How
- a71b78ae68086 curl_easy_ssls_import：建议 1 → L4 Why（跨 src/ 与 lib/）
- a5dbbffb69d3c ssl_cf_connect：建议 3 → L3 Where
- a021610de97ec Curl_ssl_get_channel_binding：建议 3 → L4 What
- aa1a4186da9e2 ftp_pollset、a8b5f1b8f5970 share_ref_inc：L1 Where；ade21b964f1c5 Curl_doh：L1 What

## 给主会话的备注

- src/ 题：B 半的锚点全在 lib/ 与 include/，只有 B25（--ssl-sessions，src/tool_ssls.c、src/tool_operate.c）用到 src/。“src 至少 4 题”要靠 A 半补。
- 每题出处都回剪枝副本源码核过（Read/grep），没用卡上未核的关系；拿不准的条已删或改写成源码里能直接看到的事实。
- 构建前提写在每题 build_assumptions；涉及 #ifdef 的（multi-SSL、libssh 与 libssh2、CURLRES_IPV4/SYNCH、CURLVERBOSE、DEBUGBUILD）都写明了。
