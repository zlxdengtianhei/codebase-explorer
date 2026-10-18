# af5b18b82e5db

函数／公开声明：`Curl_cf_ngtcp2_cmn_conn_is_alive`
文件：`lib/vquic/cf-ngtcp2-cmn.c:1981`
区域：HTTP/1/2/3（http）
类型：function；分派锚点：true
建议层：4；源码包含间接调用，适合分析替换回调或接口契约的影响。

仅来源于指定 Joern 图和源码；条件编译分支并存，不代表某种构建全部启用。
公共声明的图根为同名 lib 实现；分派处不据词法匹配推断真实目标。

## 两跳内已解析调用者

- 图中无可列出的已解析邻接函数。

## 两跳内已解析被调者

- 图中无可列出的已解析邻接函数。

## 相关函数指针表（词法引用；同文件或引用锚点／邻接函数）

- `Curl_cftype Curl_cft_h3_proxy` — `lib/vquic/cf-ngtcp2-proxy.c:1206`；函数：`Curl_cf_def_cntrl`, `Curl_cf_def_conn_keep_alive`, `Curl_cf_ngtcp2_cmn_conn_is_alive`, `Curl_cf_ngtcp2_cmn_query`, `cf_h3_proxy_adjust_pollset`, `cf_h3_proxy_connect`, `cf_h3_proxy_data_pending`, `cf_h3_proxy_destroy`, `cf_h3_proxy_recv`, `cf_h3_proxy_send`, `cf_h3_proxy_shutdown`
- `Curl_cftype Curl_cft_http3` — `lib/vquic/cf-ngtcp2.c:1053`；函数：`Curl_cf_def_conn_keep_alive`, `Curl_cf_def_data_pending`, `Curl_cf_ngtcp2_cmn_conn_is_alive`, `Curl_cf_ngtcp2_cmn_shutdown`, `cf_ngtcp2_adjust_pollset`, `cf_ngtcp2_cntrl`, `cf_ngtcp2_connect`, `cf_ngtcp2_destroy`, `cf_ngtcp2_query`, `cf_ngtcp2_recv`, `cf_ngtcp2_send`

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
- `lib/cfilters.c:869`；所属函数 `Curl_conn_cf_get_ip_info`；`cf->cft->query(`；table_type_candidate_only
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
- `lib/socks.c:1195`；所属函数 `socks_proxy_cf_connect`；`cf->next->cft->do_connect(`；table_type_candidate_only
- `lib/socks.c:1309`；所属函数 `socks_cf_query`；`cf->next->cft->query(`；table_type_candidate_only
- `lib/vquic/cf-capsule.c:67`；所属函数 `cf_capsule_connect`；`cf->next->cft->do_connect(`；table_type_candidate_only
- `lib/vquic/cf-capsule.c:168`；所属函数 `cf_capsule_data_pending`；`cf->next->cft->has_data_pending(`；table_type_candidate_only
- `lib/vquic/cf-capsule.c:208`；所属函数 `cf_capsule_query`；`cf->next->cft->query(`；table_type_candidate_only
- `lib/vquic/cf-ngtcp2-cmn.c:1042`；所属函数 `cf_connect_start`；`cf->next->cft->query(`；table_type_candidate_only
- `lib/vquic/cf-ngtcp2-cmn.c:2009`；所属函数 `Curl_cf_ngtcp2_cmn_conn_is_alive`；`cf->next->cft->is_alive(`；anchor_or_two_hop_function
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
