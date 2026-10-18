# af290ccad7bde

函数／公开声明：`set_url`
文件：`lib/urlapi.c:1828`
区域：传输与 multi 状态机（transport）
类型：function；分派锚点：false
建议层：4；可结合邻接单元和源码契约分析改动影响；设计理由须另核注释。

仅来源于指定 Joern 图和源码；条件编译分支并存，不代表某种构建全部启用。
公共声明的图根为同名 lib 实现；分派处不据词法匹配推断真实目标。

## 两跳内已解析调用者

- 1 跳：`curl_url_set` — `lib/urlapi.c:2090`
- 2 跳：`effective_url` — `lib/getinfo.c:80`
- 2 跳：`follow_fake` — `lib/http.c:1270`
- 2 跳：`follow_parse_url` — `lib/http.c:1216`
- 2 跳：`http_target` — `lib/http.c:2161`
- 2 跳：`set_auto_referer` — `lib/http.c:1180`
- 2 跳：`start_req` — `lib/http1.c:131`
- 2 跳：`Curl_peer_from_url` — `lib/peer.c:360`
- 2 跳：`parse_proxy` — `lib/proxy.c:369`
- 2 跳：`hsts_upgrade` — `lib/url.c:1217`
- 2 跳：`url_set_data_creds_netrc` — `lib/url.c:1269`
- 2 跳：`url_set_data_origin_and_creds` — `lib/url.c:2068`
- 2 跳：`url_proto_and_rewrite` — `src/config2setopts.c:143`
- 2 跳：`write_linked_location` — `src/tool_cb_hdr.c:63`
- 2 跳：`ipfs_url_rewrite` — `src/tool_ipfs.c:103`
- 2 跳：`append2query` — `src/tool_operate.c:855`
- 2 跳：`add_file_name_to_url` — `src/tool_operhlp.c:84`
- 2 跳：`get_url_file_name` — `src/tool_operhlp.c:185`
- 2 跳：`peek_ipv6` — `src/tool_urlglob.c:366`
- 2 跳：`urlpart` — `src/tool_writeout.c:81`

## 两跳内已解析被调者

- 1 跳：`Curl_is_absolute_url` — `lib/urlapi.c:213`
- 1 跳：`curl_url_get` — `lib/urlapi.c:1682`
- 1 跳：`parseurl_and_replace` — `lib/urlapi.c:1317`
- 1 跳：`redirect_url` — `lib/urlapi.c:1334`
- 1 跳：`free` — `src/tool_xattr.c:150`
- 2 跳：`Curl_memrchr` — `lib/curl_memrchr.c:37`
- 2 跳：`curlx_dyn_addn` — `lib/curlx/dynbuf.c:162`
- 2 跳：`curlx_dyn_free` — `lib/curlx/dynbuf.c:56`
- 2 跳：`curlx_dyn_init` — `lib/curlx/dynbuf.c:38`
- 2 跳：`curlx_dyn_ptr` — `lib/curlx/dynbuf.c:237`
- 2 跳：`curl_msnprintf` — `lib/mprintf.c:1272`
- 2 跳：`Curl_get_scheme` — `lib/protocol.c:626`
- 2 跳：`Curl_raw_tolower` — `lib/strcase.h:42`
- 2 跳：`free_urlhandle` — `lib/urlapi.c:69`
- 2 跳：`parseurl` — `lib/urlapi.c:1224`
- 2 跳：`urlencode_str` — `lib/urlapi.c:127`
- 2 跳：`urlget_format` — `lib/urlapi.c:1487`
- 2 跳：`urlget_url` — `lib/urlapi.c:1569`

## 相关函数指针表（词法引用；同文件或引用锚点／邻接函数）

- 未匹配到相关表。

## 相关间接调用点

table_type_candidate_only 仅表示表类型相容；不是已解析调用关系。

- 未匹配到相关调用点。
