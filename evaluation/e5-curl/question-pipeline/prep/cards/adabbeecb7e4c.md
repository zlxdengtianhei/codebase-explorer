# adabbeecb7e4c

函数／公开声明：`Curl_dnscache_clear`
文件：`lib/vdns/dnscache.c:247`
区域：DNS（dns）
类型：function；分派锚点：false
建议层：3；可结合图中的邻接单元或公开声明对应实现追踪流程。

仅来源于指定 Joern 图和源码；条件编译分支并存，不代表某种构建全部启用。
公共声明的图根为同名 lib 实现；分派处不据词法匹配推断真实目标。

## 两跳内已解析调用者

- 1 跳：`curl_multi_setopt` — `lib/multi.c:3332`
- 2 跳：`easy_perform` — `lib/easy.c:770`
- 2 跳：`parallel_transfers` — `src/tool_operate.c:1992`

## 两跳内已解析被调者

- 1 跳：`Curl_hash_clean` — `lib/hash.c:424`
- 1 跳：`dnscache_get` — `lib/vdns/dnscache.c:190`
- 1 跳：`dnscache_lock` — `lib/vdns/dnscache.c:199`
- 1 跳：`dnscache_unlock` — `lib/vdns/dnscache.c:206`
- 2 跳：`Curl_share_lock` — `lib/curl_share.c:390`
- 2 跳：`Curl_share_unlock` — `lib/curl_share.c:410`
- 2 跳：`hash_elem_destroy` — `lib/hash.c:267`
- 2 跳：`hash_elem_unlink` — `lib/hash.c:274`

## 相关函数指针表（词法引用；同文件或引用锚点／邻接函数）

- 未匹配到相关表。

## 相关间接调用点

table_type_candidate_only 仅表示表类型相容；不是已解析调用关系。

- 未匹配到相关调用点。
