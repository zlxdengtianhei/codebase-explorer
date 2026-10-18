# adc6e9adf6f3b

函数／公开声明：`curl_multi_socket`
文件：`include/curl/multi.h:317`
区域：公共 API include/（public_api）
类型：public_declaration；分派锚点：false
建议层：3；可结合图中的邻接单元或公开声明对应实现追踪流程。

仅来源于指定 Joern 图和源码；条件编译分支并存，不代表某种构建全部启用。
公共声明的图根为同名 lib 实现；分派处不据词法匹配推断真实目标。

## 两跳内已解析调用者

- 图中无可列出的已解析邻接函数。

## 两跳内已解析被调者

- 1 跳：`Curl_mapi_enter` — `lib/api.c:333`
- 1 跳：`Curl_mapi_leave` — `lib/api.c:397`
- 1 跳：`multi_socket` — `lib/multi.c:3249`
- 2 跳：`mapi_in_ntfy_cb` — `lib/api.c:155`
- 2 跳：`curlx_pnow` — `lib/curlx/timeval.c:38`
- 2 跳：`Curl_update_timer` — `lib/multi.c:3585`
- 2 跳：`multi_assess_wakeup` — `lib/multi.c:405`
- 2 跳：`multi_ischanged` — `lib/multi.c:1722`
- 2 跳：`multi_mark_expired_as_dirty` — `lib/multi.c:3170`
- 2 跳：`multi_perform` — `lib/multi.c:2898`
- 2 跳：`multi_run_dirty` — `lib/multi.c:3201`
- 2 跳：`multi_schedule_pending` — `lib/multi.c:3876`
- 2 跳：`multi_xfers_running` — `lib/multi.c:4185`
- 2 跳：`Curl_multi_ev_assess_xfer_bset` — `lib/multi_ev.c:557`
- 2 跳：`Curl_multi_ev_dirty_xfers` — `lib/multi_ev.c:585`
- 2 跳：`Curl_mntfy_dispatch_all` — `lib/multi_ntfy.c:176`

## 相关函数指针表（词法引用；同文件或引用锚点／邻接函数）

- 未匹配到相关表。

## 相关间接调用点

table_type_candidate_only 仅表示表类型相容；不是已解析调用关系。

- 未匹配到相关调用点。
