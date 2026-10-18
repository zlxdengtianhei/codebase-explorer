# ae2d567bffc75

函数／公开声明：`Curl_conn_connect`
文件：`lib/connect.c:255`
区域：连接过滤器与套接字（filters）
类型：function；分派锚点：true
建议层：3；源码包含间接调用，适合追踪跨单元分派链。

仅来源于指定 Joern 图和源码；条件编译分支并存，不代表某种构建全部启用。
公共声明的图根为同名 lib 实现；分派处不据词法匹配推断真实目标。

## 两跳内已解析调用者

- 1 跳：`ftp_connect` — `lib/ftp.c:3535`
- 1 跳：`ftp_do_more` — `lib/ftp.c:2215`
- 1 跳：`ftp_initiate_transfer` — `lib/ftp.c:543`
- 1 跳：`ftp_pp_statemachine` — `lib/ftp.c:3180`
- 1 跳：`ftp_state_get_resp` — `lib/ftp.c:2778`
- 1 跳：`ftp_state_stor_resp` — `lib/ftp.c:2745`
- 1 跳：`multistate_connecting` — `lib/multi.c:2510`
- 2 跳：`ftp_dophase_done` — `lib/ftp.c:2378`
- 2 跳：`multi_runsingle` — `lib/multi.c:2719`

## 两跳内已解析被调者

- 1 跳：`Curl_conn_adjust_pollset` — `lib/cfilters.c:697`
- 1 跳：`Curl_conn_cf_get_socket` — `lib/cfilters.c:822`
- 1 跳：`Curl_conn_cntrl_update_info` — `lib/cfilters.c:419`
- 1 跳：`Curl_conn_flush` — `lib/cfilters.c:904`
- 1 跳：`Curl_conn_is_ssl` — `lib/cfilters.c:528`
- 1 跳：`Curl_conn_needs_flush` — `lib/cfilters.c:670`
- 1 跳：`Curl_conn_remove_setup_filters` — `lib/cfilters.c:434`
- 1 跳：`Curl_conn_trc_filters` — `lib/cfilters.c:130`
- 1 跳：`Curl_cpool_conn_was_used` — `lib/conncache.c:1089`
- 1 跳：`Curl_conn_report_failed` — `lib/connect.c:243`
- 1 跳：`Curl_timeleft_ms` — `lib/connect.c:104`
- 1 跳：`conn_connect_trace` — `lib/connect.c:210`
- 1 跳：`conn_report_stats` — `lib/connect.c:235`
- 1 跳：`Curl_failf` — `lib/curl_trc.c:176`
- 1 跳：`Curl_trc_cf_infof` — `lib/curl_trc.c:281`
- 1 跳：`Curl_pgrs_now` — `lib/progress.c:171`
- 1 跳：`Curl_poll` — `lib/select.c:199`
- 1 跳：`Curl_pollfds_add_ps` — `lib/select.c:404`
- 1 跳：`Curl_pollfds_cleanup` — `lib/select.c:347`
- 1 跳：`Curl_pollfds_init` — `lib/select.c:330`
- 1 跳：`Curl_pollfds_reset` — `lib/select.c:342`
- 1 跳：`Curl_pollset_change` — `lib/select.c:548`
- 1 跳：`Curl_pollset_cleanup` — `lib/select.c:507`
- 1 跳：`Curl_pollset_init` — `lib/select.c:487`
- 1 跳：`Curl_pollset_reset` — `lib/select.c:479`
- 2 跳：`Curl_conn_cf_adjust_pollset` — `lib/cfilters.c:677`
- 2 跳：`Curl_conn_cf_cntrl` — `lib/cfilters.c:805`
- 2 跳：`Curl_conn_cf_get_ip_info` — `lib/cfilters.c:862`
- 2 跳：`Curl_conn_cf_needs_flush` — `lib/cfilters.c:660`
- 2 跳：`Curl_conn_cntrl_report_stats` — `lib/cfilters.c:425`
- 2 跳：`cf_cntrl_all` — `lib/cfilters.c:391`
- 2 跳：`cf_is_ssl` — `lib/cfilters.c:515`
- 2 跳：`timeleft_now_ms` — `lib/connect.c:70`
- 2 跳：`Curl_infof` — `lib/curl_trc.c:270`
- 2 跳：`Curl_trc_multi` — `lib/curl_trc.c:383`
- 2 跳：`trc_infof` — `lib/curl_trc.c:246`
- 2 跳：`trc_write` — `lib/curl_trc.c:49`
- 2 跳：`curlx_strcopy` — `lib/curlx/strcopy.c:38`
- 2 跳：`curlx_pnow` — `lib/curlx/timeval.c:38`
- 2 跳：`curlx_ptimediff_ms` — `lib/curlx/timeval.c:186`
- 2 跳：`curlx_wait_ms` — `lib/curlx/wait.c:54`
- 2 跳：`curl_msnprintf` — `lib/mprintf.c:1272`
- 2 跳：`curl_mvsnprintf` — `lib/mprintf.c:1247`
- 2 跳：`cpfds_add_sock` — `lib/select.c:376`
- 2 跳：`our_select` — `lib/select.c:51`
- 2 跳：`free` — `src/tool_xattr.c:150`

## 相关函数指针表（词法引用；同文件或引用锚点／邻接函数）

- `Curl_protocol Curl_protocol_ftp` — `lib/ftp.c:4498`；函数：`ftp_connect`, `ftp_disconnect`, `ftp_do`, `ftp_do_more`, `ftp_doing`, `ftp_domore_pollset`, `ftp_done`, `ftp_multi_statemach`, `ftp_pollset`, `ftp_setup_connection`

## 相关间接调用点

table_type_candidate_only 仅表示表类型相容；不是已解析调用关系。

- `lib/cfilters.c:444`；所属函数 `Curl_conn_remove_setup_filters`；`cf->cft->destroy(`；anchor_or_two_hop_function
- `lib/cfilters.c:665`；所属函数 `Curl_conn_cf_needs_flush`；`cf->cft->query(`；anchor_or_two_hop_function
- `lib/cfilters.c:692`；所属函数 `Curl_conn_cf_adjust_pollset`；`cf->cft->adjust_pollset(`；anchor_or_two_hop_function
- `lib/cfilters.c:815`；所属函数 `Curl_conn_cf_cntrl`；`cf->cft->cntrl(`；anchor_or_two_hop_function
- `lib/cfilters.c:826`；所属函数 `Curl_conn_cf_get_socket`；`cf->cft->query(`；anchor_or_two_hop_function
- `lib/cfilters.c:869`；所属函数 `Curl_conn_cf_get_ip_info`；`cf->cft->query(`；anchor_or_two_hop_function
- `lib/connect.c:297`；所属函数 `Curl_conn_connect`；`cf->cft->do_connect(`；anchor_or_two_hop_function
