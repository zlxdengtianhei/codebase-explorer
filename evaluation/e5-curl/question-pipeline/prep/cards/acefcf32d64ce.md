# acefcf32d64ce

函数／公开声明：`curl_slist_append`
文件：`include/curl/curl.h:2878`
区域：公共 API include/（public_api）
类型：public_declaration；分派锚点：false
建议层：3；可结合图中的邻接单元或公开声明对应实现追踪流程。

仅来源于指定 Joern 图和源码；条件编译分支并存，不代表某种构建全部启用。
公共声明的图根为同名 lib 实现；分派处不据词法匹配推断真实目标。

## 两跳内已解析调用者

- 1 跳：`make_headers` — `lib/http_aws_sigv4.c:370`
- 1 跳：`cookiefile` — `lib/setopt.c:1548`
- 1 跳：`setopt_cptr_misc` — `lib/setopt.c:2276`
- 1 跳：`Curl_slist_duplicate` — `lib/slist.c:104`
- 1 跳：`check_telnet_options` — `lib/telnet.c:828`
- 1 跳：`doh_probe_run` — `lib/vdns/doh.c:234`
- 1 跳：`slist_wc_append` — `src/slist_wc.c:34`
- 1 跳：`buffer_header` — `src/tool_cb_hdr.c:252`
- 1 跳：`slist_append` — `src/tool_formparse.c:428`
- 1 跳：`add2list` — `src/tool_paramhlp.c:601`
- 2 跳：`curl_easy_duphandle` — `lib/easy.c:1002`
- 2 跳：`make_canonical_request` — `lib/http_aws_sigv4.c:926`
- 2 跳：`mime_duppart` — `lib/mime.c:1146`
- 2 跳：`setopt_cptr_http_mqtt` — `lib/setopt.c:2010`
- 2 跳：`telnet_do` — `lib/telnet.c:1220`
- 2 跳：`Curl_doh` — `lib/vdns/doh.c:403`
- 2 跳：`content_disposition` — `src/tool_cb_hdr.c:340`
- 2 跳：`tool_header_cb` — `src/tool_cb_hdr.c:425`
- 2 跳：`easysrc_add` — `src/tool_easysrc.c:99`
- 2 跳：`param_headers` — `src/tool_formparse.c:545`
- 2 跳：`read_field_headers` — `src/tool_formparse.c:443`
- 2 跳：`opt_string` — `src/tool_getparam.c:2484`
- 2 跳：`parse_header` — `src/tool_getparam.c:1293`
- 2 跳：`parse_quote` — `src/tool_getparam.c:1419`
- 2 跳：`etag_compare` — `src/tool_operate.c:897`
- 2 跳：`get_args` — `src/tool_paramhlp.c:673`

## 两跳内已解析被调者

- 1 跳：`Curl_slist_append_nodup` — `lib/slist.c:54`
- 1 跳：`free` — `src/tool_xattr.c:150`
- 2 跳：`slist_get_last` — `lib/slist.c:29`

## 相关函数指针表（词法引用；同文件或引用锚点／邻接函数）

- `Curl_protocol Curl_protocol_telnet` — `lib/telnet.c:1556`；函数：`telnet_do`, `telnet_done`

## 相关间接调用点

table_type_candidate_only 仅表示表类型相容；不是已解析调用关系。

- 未匹配到相关调用点。
