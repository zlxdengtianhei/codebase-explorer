# a2e5f0be18f8b

函数／公开声明：`Curl_cshutdn_try_once_idx`
文件：`lib/cshutdn.c:127`
区域：连接池与共享（pool）
类型：function；分派锚点：true
建议层：3；源码包含间接调用，适合追踪跨单元分派链。

仅来源于指定 Joern 图和源码；条件编译分支并存，不代表某种构建全部启用。
公共声明的图根为同名 lib 实现；分派处不据词法匹配推断真实目标。

## 两跳内已解析调用者

- 1 跳：`cshutdn_run_once` — `lib/cshutdn.c:183`
- 1 跳：`Curl_xfer_send_shutdown` — `lib/transfer.c:160`
- 1 跳：`xfer_recv_shutdown` — `lib/transfer.c:146`
- 2 跳：`Curl_cshutdn_terminate` — `lib/cshutdn.c:236`
- 2 跳：`Curl_cshutdn_try_once` — `lib/cshutdn.c:224`
- 2 跳：`req_flush` — `lib/request.c:298`
- 2 跳：`xfer_recv_resp` — `lib/transfer.c:175`

## 两跳内已解析被调者

- 1 跳：`Curl_cshutdn_start_timer` — `lib/cshutdn.c:43`
- 1 跳：`Curl_cshutdn_timeleft_ms` — `lib/cshutdn.c:63`
- 1 跳：`Curl_infof` — `lib/curl_trc.c:270`
- 1 跳：`Curl_trc_cf_infof` — `lib/curl_trc.c:281`
- 2 跳：`Curl_trc_multi` — `lib/curl_trc.c:383`
- 2 跳：`trc_infof` — `lib/curl_trc.c:246`
- 2 跳：`curlx_ptimediff_ms` — `lib/curlx/timeval.c:186`
- 2 跳：`Curl_expire_set` — `lib/multi.c:3750`
- 2 跳：`Curl_pgrs_now` — `lib/progress.c:171`

## 相关函数指针表（词法引用；同文件或引用锚点／邻接函数）

- 未匹配到相关表。

## 相关间接调用点

table_type_candidate_only 仅表示表类型相容；不是已解析调用关系。

- `lib/cshutdn.c:165`；所属函数 `Curl_cshutdn_try_once_idx`；`cf->cft->do_shutdown(`；anchor_or_two_hop_function
