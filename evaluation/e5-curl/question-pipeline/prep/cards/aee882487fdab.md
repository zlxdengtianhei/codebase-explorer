# aee882487fdab

函数／公开声明：`socks_proxy_cf_connect`
文件：`lib/socks.c:1182`
区域：连接过滤器与套接字（filters）
类型：function；分派锚点：true
建议层：3；源码包含间接调用，适合追踪跨单元分派链。

仅来源于指定 Joern 图和源码；条件编译分支并存，不代表某种构建全部启用。
公共声明的图根为同名 lib 实现；分派处不据词法匹配推断真实目标。

## 两跳内已解析调用者

- 图中无可列出的已解析邻接函数。

## 两跳内已解析被调者

- 1 跳：`Curl_conn_cf_get_ip_info` — `lib/cfilters.c:862`
- 1 跳：`Curl_creds_unlink` — `lib/creds.c:142`
- 1 跳：`Curl_infof` — `lib/curl_trc.c:270`
- 1 跳：`socks4_connect` — `lib/socks.c:447`
- 1 跳：`socks5_connect` — `lib/socks.c:1018`
- 2 跳：`Curl_bufq_cwrite` — `lib/bufq.c:394`
- 2 跳：`Curl_bufq_reset` — `lib/bufq.c:243`
- 2 跳：`Curl_bufq_write` — `lib/bufq.c:367`
- 2 跳：`Curl_failf` — `lib/curl_trc.c:176`
- 2 跳：`Curl_trc_cf_infof` — `lib/curl_trc.c:281`
- 2 跳：`trc_infof` — `lib/curl_trc.c:246`
- 2 跳：`curlx_memzero` — `lib/curlx/strdup.c:112`
- 2 跳：`socks4_check_resp` — `lib/socks.c:359`
- 2 跳：`socks4_req_add_hd` — `lib/socks.c:262`
- 2 跳：`socks4_req_add_user` — `lib/socks.c:281`
- 2 跳：`socks4_resolving` — `lib/socks.c:312`
- 2 跳：`socks5_auth_init` — `lib/socks.c:680`
- 2 跳：`socks5_check_auth_resp` — `lib/socks.c:733`
- 2 跳：`socks5_check_resp0` — `lib/socks.c:622`
- 2 跳：`socks5_recv_resp1` — `lib/socks.c:920`
- 2 跳：`socks5_req0_init` — `lib/socks.c:564`
- 2 跳：`socks5_req1_init` — `lib/socks.c:758`
- 2 跳：`socks5_resolving` — `lib/socks.c:827`
- 2 跳：`socks_failed` — `lib/socks.c:194`
- 2 跳：`socks_flush` — `lib/socks.c:204`
- 2 跳：`socks_recv` — `lib/socks.c:228`
- 2 跳：`socksstate` — `lib/socks.c:167`
- 2 跳：`free` — `src/tool_xattr.c:150`

## 相关函数指针表（词法引用；同文件或引用锚点／邻接函数）

- `Curl_cftype Curl_cft_socks_proxy` — `lib/socks.c:1313`；函数：`Curl_cf_def_cntrl`, `Curl_cf_def_conn_is_alive`, `Curl_cf_def_conn_keep_alive`, `Curl_cf_def_data_pending`, `Curl_cf_def_recv`, `Curl_cf_def_send`, `Curl_cf_def_shutdown`, `socks_cf_adjust_pollset`, `socks_cf_query`, `socks_proxy_cf_connect`, `socks_proxy_cf_destroy`

## 相关间接调用点

table_type_candidate_only 仅表示表类型相容；不是已解析调用关系。

- `lib/cf-h1-proxy.c:288`；所属函数 `send_CONNECT`；`cf->next->cft->do_send(`；table_type_candidate_only
- `lib/cf-h1-proxy.c:787`；所属函数 `cf_h1_proxy_connect`；`cf->next->cft->do_connect(`；table_type_candidate_only
- `lib/cf-h1-proxy.c:846`；所属函数 `cf_h1_proxy_adjust_pollset`；`cf->next->cft->adjust_pollset(`；table_type_candidate_only
- `lib/cf-h1-proxy.c:854`；所属函数 `cf_h1_proxy_data_pending`；`cf->next->cft->has_data_pending(`；table_type_candidate_only
- `lib/cf-h1-proxy.c:893`；所属函数 `cf_h1_proxy_query`；`cf->next->cft->query(`；table_type_candidate_only
- `lib/cf-h2-proxy.c:1105`；所属函数 `cf_h2_proxy_data_pending`；`cf->next->cft->has_data_pending(`；table_type_candidate_only
- `lib/cf-h2-proxy.c:1369`；所属函数 `proxy_h2_connisalive`；`cf->next->cft->is_alive(`；table_type_candidate_only
- `lib/cf-h2-proxy.c:1445`；所属函数 `cf_h2_proxy_query`；`cf->next->cft->query(`；table_type_candidate_only
- `lib/cf-haproxy.c:119`；所属函数 `cf_haproxy_connect`；`cf->next->cft->do_connect(`；table_type_candidate_only
- `lib/cf-https-connect.c:84`；所属函数 `cf_hc_baller_reply_ms`；`b->cf->cft->query(`；table_type_candidate_only
- `lib/cf-https-connect.c:92`；所属函数 `cf_hc_baller_data_pending`；`b->cf->cft->has_data_pending(`；table_type_candidate_only
- `lib/cf-https-connect.c:605`；所属函数 `cf_hc_shutdown`；`b->cf->cft->do_shutdown(`；table_type_candidate_only
- `lib/cf-https-connect.c:653`；所属函数 `cf_hc_data_pending`；`cf->next->cft->has_data_pending(`；table_type_candidate_only
- `lib/cf-https-connect.c:683`；所属函数 `cf_hc_query`；`cf->next->cft->query(`；table_type_candidate_only
- `lib/cf-ip-happy.c:631`；所属函数 `cf_ip_ballers_shutdown`；`a->cf->cft->do_shutdown(`；table_type_candidate_only
- `lib/cf-ip-happy.c:662`；所属函数 `cf_ip_ballers_pending`；`a->cf->cft->has_data_pending(`；table_type_candidate_only
- `lib/cf-ip-happy.c:675`；所属函数 `cf_ip_ballers_min_reply_ms`；`a->cf->cft->query(`；table_type_candidate_only
- `lib/cf-ip-happy.c:926`；所属函数 `cf_ip_happy_data_pending`；`cf->next->cft->has_data_pending(`；table_type_candidate_only
- `lib/cf-ip-happy.c:948`；所属函数 `cf_ip_happy_query`；`cf->next->cft->query(`；table_type_candidate_only
- `lib/cf-recvbuf.c:64`；所属函数 `cf_recvbuf_recv`；`cf->next->cft->do_recv(`；table_type_candidate_only
- `lib/cf-recvbuf.c:78`；所属函数 `cf_recvbuf_data_pending`；`cf->next->cft->has_data_pending(`；table_type_candidate_only
- `lib/cf-socket.c:1895`；所属函数 `cf_socket_query`；`cf->next->cft->query(`；table_type_candidate_only
- `lib/cfilters.c:47`；所属函数 `Curl_cf_def_connect`；`cf->next->cft->do_connect(`；table_type_candidate_only
- `lib/cfilters.c:81`；所属函数 `Curl_cf_def_data_pending`；`cf->next->cft->has_data_pending(`；table_type_candidate_only
- `lib/cfilters.c:89`；所属函数 `Curl_cf_def_send`；`cf->next->cft->do_send(`；table_type_candidate_only
- `lib/cfilters.c:98`；所属函数 `Curl_cf_def_recv`；`cf->next->cft->do_recv(`；table_type_candidate_only
- `lib/cfilters.c:108`；所属函数 `Curl_cf_def_conn_is_alive`；`cf->next->cft->is_alive(`；table_type_candidate_only
- `lib/cfilters.c:116`；所属函数 `Curl_cf_def_conn_keep_alive`；`cf->next->cft->keep_alive(`；table_type_candidate_only
- `lib/cfilters.c:125`；所属函数 `Curl_cf_def_query`；`cf->next->cft->query(`；table_type_candidate_only
- `lib/cfilters.c:172`；所属函数 `Curl_conn_cf_discard_chain`；`cf->cft->destroy(`；table_type_candidate_only
- `lib/cfilters.c:197`；所属函数 `Curl_cf_recv`；`cf->cft->do_recv(`；table_type_candidate_only
- `lib/cfilters.c:216`；所属函数 `Curl_cf_send`；`cf->cft->do_send(`；table_type_candidate_only
- `lib/cfilters.c:368`；所属函数 `Curl_conn_cf_connect`；`cf->cft->do_connect(`；table_type_candidate_only
- `lib/cfilters.c:377`；所属函数 `Curl_conn_cf_send`；`cf->cft->do_send(`；table_type_candidate_only
- `lib/cfilters.c:386`；所属函数 `Curl_conn_cf_recv`；`cf->cft->do_recv(`；table_type_candidate_only
- `lib/cfilters.c:413`；所属函数 `Curl_conn_cf_is_ip_connected`；`cf->cft->query(`；table_type_candidate_only
- `lib/cfilters.c:444`；所属函数 `Curl_conn_remove_setup_filters`；`cf->cft->destroy(`；table_type_candidate_only
- `lib/cfilters.c:545`；所属函数 `Curl_conn_get_ssl_info`；`cf->cft->query(`；table_type_candidate_only
- `lib/cfilters.c:627`；所属函数 `Curl_conn_http_version`；`cf->cft->query(`；table_type_candidate_only
- `lib/cfilters.c:655`；所属函数 `Curl_conn_data_pending`；`cf->cft->has_data_pending(`；table_type_candidate_only
- `lib/cfilters.c:665`；所属函数 `Curl_conn_cf_needs_flush`；`cf->cft->query(`；table_type_candidate_only
- `lib/cfilters.c:692`；所属函数 `Curl_conn_cf_adjust_pollset`；`cf->cft->adjust_pollset(`；table_type_candidate_only
- `lib/cfilters.c:782`；所属函数 `Curl_conn_get_current_host`；`cf_proxy->cft->query(`；table_type_candidate_only
- `lib/cfilters.c:815`；所属函数 `Curl_conn_cf_cntrl`；`cf->cft->cntrl(`；table_type_candidate_only
- `lib/cfilters.c:826`；所属函数 `Curl_conn_cf_get_socket`；`cf->cft->query(`；table_type_candidate_only
- `lib/cfilters.c:835`；所属函数 `Curl_conn_cf_get_transport`；`cf->cft->query(`；table_type_candidate_only
- `lib/cfilters.c:845`；所属函数 `Curl_conn_cf_get_alpn_negotiated`；`cf->cft->query(`；table_type_candidate_only
- `lib/cfilters.c:856`；所属函数 `cf_get_remote_addr`；`cf->cft->query(`；table_type_candidate_only
- `lib/cfilters.c:869`；所属函数 `Curl_conn_cf_get_ip_info`；`cf->cft->query(`；anchor_or_two_hop_function
- `lib/cfilters.c:941`；所属函数 `Curl_conn_is_alive`；`cf->cft->is_alive(`；table_type_candidate_only
- `lib/cfilters.c:953`；所属函数 `Curl_conn_keep_alive`；`cf->cft->keep_alive(`；table_type_candidate_only
- `lib/cfilters.c:970`；所属函数 `Curl_conn_get_max_concurrent`；`cf->cft->query(`；table_type_candidate_only
- `lib/cfilters.c:990`；所属函数 `Curl_conn_get_stream_error`；`cf->cft->query(`；table_type_candidate_only
- `lib/connect.c:297`；所属函数 `Curl_conn_connect`；`cf->cft->do_connect(`；table_type_candidate_only
- `lib/cshutdn.c:165`；所属函数 `Curl_cshutdn_try_once_idx`；`cf->cft->do_shutdown(`；table_type_candidate_only
- `lib/http2.c:564`；所属函数 `http2_connisalive`；`cf->next->cft->is_alive(`；table_type_candidate_only
- `lib/http2.c:1920`；所属函数 `h2_progress_ingress`；`cf->next->cft->has_data_pending(`；table_type_candidate_only
- `lib/http2.c:2701`；所属函数 `cf_h2_data_pending`；`cf->next->cft->has_data_pending(`；table_type_candidate_only
- `lib/http2.c:2777`；所属函数 `cf_h2_query`；`cf->next->cft->query(`；table_type_candidate_only
- `lib/http2.c:2958`；所属函数 `Curl_http2_upgrade`；`cf->cft->cntrl(`；table_type_candidate_only
- `lib/http_proxy.c:562`；所属函数 `http_proxy_cf_connect`；`cf->next->cft->do_connect(`；table_type_candidate_only
- `lib/http_proxy.c:683`；所属函数 `cf_http_proxy_query`；`cf->next->cft->query(`；table_type_candidate_only
- `lib/socks.c:1195`；所属函数 `socks_proxy_cf_connect`；`cf->next->cft->do_connect(`；anchor_or_two_hop_function
- `lib/socks.c:1309`；所属函数 `socks_cf_query`；`cf->next->cft->query(`；table_type_candidate_only
- `lib/vquic/cf-capsule.c:67`；所属函数 `cf_capsule_connect`；`cf->next->cft->do_connect(`；table_type_candidate_only
- `lib/vquic/cf-capsule.c:168`；所属函数 `cf_capsule_data_pending`；`cf->next->cft->has_data_pending(`；table_type_candidate_only
- `lib/vquic/cf-capsule.c:208`；所属函数 `cf_capsule_query`；`cf->next->cft->query(`；table_type_candidate_only
- `lib/vquic/cf-ngtcp2-cmn.c:1042`；所属函数 `cf_connect_start`；`cf->next->cft->query(`；table_type_candidate_only
- `lib/vquic/cf-ngtcp2-cmn.c:2009`；所属函数 `Curl_cf_ngtcp2_cmn_conn_is_alive`；`cf->next->cft->is_alive(`；table_type_candidate_only
- `lib/vquic/cf-ngtcp2-cmn.c:2093`；所属函数 `Curl_cf_ngtcp2_cmn_query`；`cf->next->cft->query(`；table_type_candidate_only
- `lib/vquic/cf-ngtcp2-proxy.c:1022`；所属函数 `cf_h3_proxy_data_pending`；`cf->next->cft->has_data_pending(`；table_type_candidate_only
- `lib/vquic/cf-quiche.c:1583`；所属函数 `cf_quiche_query`；`cf->next->cft->query(`；table_type_candidate_only
- `lib/vquic/cf-quiche.c:1606`；所属函数 `cf_quiche_conn_is_alive`；`cf->next->cft->is_alive(`；table_type_candidate_only
- `lib/vtls/openssl.c:1873`；所属函数 `ossl_shutdown`；`cf->next->cft->is_alive(`；table_type_candidate_only
- `lib/vtls/vtls.c:978`；所属函数 `ssl_cf_connect`；`cf->next->cft->do_connect(`；table_type_candidate_only
- `lib/vtls/vtls.c:1109`；所属函数 `ssl_cf_data_pending`；`cf->next->cft->has_data_pending(`；table_type_candidate_only
- `lib/vtls/vtls.c:1264`；所属函数 `ssl_cf_query`；`cf->next->cft->query(`；table_type_candidate_only
- `lib/vtls/vtls.c:1307`；所属函数 `cf_ssl_is_alive`；`cf->next->cft->is_alive(`；table_type_candidate_only
- `lib/vtls/wolfssl.c:1918`；所属函数 `wssl_shutdown`；`cf->next->cft->is_alive(`；table_type_candidate_only
