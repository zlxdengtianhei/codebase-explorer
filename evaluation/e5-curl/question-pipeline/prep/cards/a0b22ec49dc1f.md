# a0b22ec49dc1f

函数／公开声明：`curl_url_cleanup`
文件：`include/curl/urlapi.h:121`
区域：公共 API include/（public_api）
类型：public_declaration；分派锚点：false
建议层：3；可结合图中的邻接单元或公开声明对应实现追踪流程。

仅来源于指定 Joern 图和源码；条件编译分支并存，不代表某种构建全部启用。
公共声明的图根为同名 lib 实现；分派处不据词法匹配推断真实目标。

## 两跳内已解析调用者

- 1 跳：`effective_url` — `lib/getinfo.c:80`
- 1 跳：`follow_fake` — `lib/http.c:1270`
- 1 跳：`follow_parse_url` — `lib/http.c:1216`
- 1 跳：`http_target` — `lib/http.c:2161`
- 1 跳：`set_auto_referer` — `lib/http.c:1180`
- 1 跳：`start_req` — `lib/http1.c:131`
- 1 跳：`parse_proxy` — `lib/proxy.c:369`
- 1 跳：`up_free` — `lib/url.c:181`
- 1 跳：`curl_url_dup` — `lib/urlapi.c:1434`
- 1 跳：`url_proto_and_rewrite` — `src/config2setopts.c:143`
- 1 跳：`write_linked_location` — `src/tool_cb_hdr.c:63`
- 1 跳：`ipfs_url_rewrite` — `src/tool_ipfs.c:103`
- 1 跳：`append2query` — `src/tool_operate.c:855`
- 1 跳：`add_file_name_to_url` — `src/tool_operhlp.c:84`
- 1 跳：`get_url_file_name` — `src/tool_operhlp.c:185`
- 1 跳：`peek_ipv6` — `src/tool_urlglob.c:366`
- 1 跳：`urlpart` — `src/tool_writeout.c:81`
- 2 跳：`getinfo_char` — `lib/getinfo.c:119`
- 2 跳：`Curl_http_follow` — `lib/http.c:1383`
- 2 跳：`http_add_hd` — `lib/http.c:2927`
- 2 跳：`Curl_h1_req_parse_read` — `lib/http1.c:262`
- 2 跳：`Curl_proxy_init_conn` — `lib/proxy.c:519`
- 2 跳：`Curl_close` — `lib/url.c:197`
- 2 跳：`url_set_data_origin_and_creds` — `lib/url.c:2068`
- 2 跳：`config2setopts` — `src/config2setopts.c:1204`
- 2 跳：`tool_header_cb` — `src/tool_cb_hdr.c:425`
- 2 跳：`create_single` — `src/tool_operate.c:1365`
- 2 跳：`setup_outfile` — `src/tool_operate.c:1032`
- 2 跳：`setup_transfer_upload` — `src/tool_operate.c:1332`
- 2 跳：`glob_parse` — `src/tool_urlglob.c:444`
- 2 跳：`writeString` — `src/tool_writeout.c:172`

## 两跳内已解析被调者

- 1 跳：`free_urlhandle` — `lib/urlapi.c:69`
- 1 跳：`free` — `src/tool_xattr.c:150`
- 2 跳：`curlx_strzero` — `lib/curlx/strdup.c:119`

## 相关函数指针表（词法引用；同文件或引用锚点／邻接函数）

- `Curl_protocol Curl_protocol_http` — `lib/http.c:5114`；函数：`Curl_http`, `Curl_http_doing_pollset`, `Curl_http_done`, `Curl_http_follow`, `Curl_http_perform_pollset`, `Curl_http_setup_conn`, `Curl_http_write_resp`, `Curl_http_write_resp_hd`
- `Curl_protocol Curl_protocol_rtsp` — `lib/rtsp.c:1039`；函数：`Curl_http_follow`, `Curl_http_perform_pollset`, `rtsp_conn_is_dead`, `rtsp_connect`, `rtsp_do`, `rtsp_do_pollset`, `rtsp_done`, `rtsp_rtp_write_resp`, `rtsp_rtp_write_resp_hd`, `rtsp_setup_connection`
- `Curl_protocol Curl_protocol_ws` — `lib/ws.c:2012`；函数：`Curl_http`, `Curl_http_doing_pollset`, `Curl_http_done`, `Curl_http_follow`, `Curl_http_perform_pollset`, `Curl_http_write_resp`, `Curl_http_write_resp_hd`, `ws_setup_conn`

## 相关间接调用点

table_type_candidate_only 仅表示表类型相容；不是已解析调用关系。

- 未匹配到相关调用点。
