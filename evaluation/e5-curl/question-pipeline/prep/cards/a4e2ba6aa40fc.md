# a4e2ba6aa40fc

函数／公开声明：`Curl_cpool_init`
文件：`lib/conncache.c:246`
区域：连接池与共享（pool）
类型：function；分派锚点：false
建议层：2；可围绕该单元的输入、分支与返回行为核实。

仅来源于指定 Joern 图和源码；条件编译分支并存，不代表某种构建全部启用。
公共声明的图根为同名 lib 实现；分派处不据词法匹配推断真实目标。

## 两跳内已解析调用者

- 1 跳：`curl_share_setopt` — `lib/curl_share.c:194`
- 1 跳：`Curl_multi_handle` — `lib/multi.c:223`
- 2 跳：`easy_perform` — `lib/easy.c:770`
- 2 跳：`curl_multi_init` — `lib/multi.c:377`
- 2 跳：`share_setopt` — `src/tool_operate.c:2394`

## 两跳内已解析被调者

- 1 跳：`Curl_hash_init` — `lib/hash.c:213`
- 1 跳：`Curl_uint32_bset_init` — `lib/uint-bset.c:32`
- 1 跳：`Curl_uint32_tbl_init` — `lib/uint-table.c:32`

## 相关函数指针表（词法引用；同文件或引用锚点／邻接函数）

- 未匹配到相关表。

## 相关间接调用点

table_type_candidate_only 仅表示表类型相容；不是已解析调用关系。

- 未匹配到相关调用点。
