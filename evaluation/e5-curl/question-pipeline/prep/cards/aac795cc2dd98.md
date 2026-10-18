# aac795cc2dd98

函数／公开声明：`peer_same_hostname`
文件：`lib/peer.c:329`
区域：连接池与共享（pool）
类型：function；分派锚点：false
建议层：3；可结合图中的邻接单元或公开声明对应实现追踪流程。

仅来源于指定 Joern 图和源码；条件编译分支并存，不代表某种构建全部启用。
公共声明的图根为同名 lib 实现；分派处不据词法匹配推断真实目标。

## 两跳内已解析调用者

- 1 跳：`Curl_peer_same_destination` — `lib/peer.c:350`
- 2 跳：`Curl_peer_equal` — `lib/peer.c:321`
- 2 跳：`proxy_info_matches` — `lib/url.c:556`
- 2 跳：`url_match_destination` — `lib/url.c:889`
- 2 跳：`Curl_conn_dns_addr_result` — `lib/vdns/cf-dns.c:577`
- 2 跳：`Curl_conn_dns_get_ai` — `lib/vdns/cf-dns.c:600`
- 2 跳：`cf_dns_add_resolve` — `lib/vdns/cf-dns.c:507`

## 两跳内已解析被调者

- 1 跳：`curl_strequal` — `lib/strequal.c:76`
- 2 跳：`casecompare` — `lib/strequal.c:35`

## 相关函数指针表（词法引用；同文件或引用锚点／邻接函数）

- 未匹配到相关表。

## 相关间接调用点

table_type_candidate_only 仅表示表类型相容；不是已解析调用关系。

- 未匹配到相关调用点。
