# skipped.md（cbe-q13a，A 半）

## 跳过的锚点（1 个）

| 锚点 id | 函数 | 区域 | 原因 | 补位 |
|---|---|---|---|---|
| ab1530edb0722 | `cf_quiche_conn_is_alive`（lib/vquic/cf-quiche.c） | http | 源码关系成立，但能出的可核题与本半已出的 A13（`http2_connisalive`）、A14（`Curl_cf_ngtcp2_cmn_conn_is_alive`）是同一个 is_alive 契约：先问 `cf->next->cft->is_alive`、清 `*input_pending`、处理空闲连接上积压的协议帧、出错判死。quiche 独有的差别只有一处（空闲超时交给 `quiche_conn_is_closed`/`quiche_conn_is_timed_out`），单独成题会和 A14 互相泄答案，区分度低。 | 按同区顺序补位 `cf_h2_query`（a5c35b2a36f1b）→ A18 |

## 未用的锚点（区额度已满，按固定顺序没轮到）

- transport：`set_url`（af290ccad7bde）、`curl_version`（a9e2cacbf1a9a）
- filters：`Curl_conn_keep_alive`（ad3ad678b547f）
- http：`cf_quiche_query`（a924f34e95c80）
- auth：`netrc_scan_reset`（a0f51941c0168）
- cli：`parse_continue_at`（a459deefc076c）、`save_etag`（ace64bd7936ab）、`add_offt`（a52a0a815ca95）、`ftp_setopts`（adc8e42041c02）

## 用锚点时的变体说明（锚点没换，构建前提选了另一条分支）

- A22 锚点 `Curl_auth_digest_cleanup`：卡指向 lib/vauth/digest_sspi.c（Windows SSPI 版）。题目用非 SSPI 构建，答案以 lib/vauth/digest.c 的同名函数为准；SSPI 版只清 input_token、安全上下文、creds、origin，题面的构建前提已写明“not USE_WINDOWS_SSPI”，答案唯一。
- A21 锚点 `krb5_conn_dtor`（lib/vauth/vauth.c，两种构建共用）：题目选 GSS-API 构建，所以 `Curl_auth_cleanup_gssapi` 以 lib/vauth/krb5_gssapi.c 为准。
- A20 锚点 `Curl_auth_is_gssapi_supported`：按卡用 Windows SSPI 版（lib/vauth/krb5_sspi.c）。

## 子图卡与源码不符处（供主会话参考，出题时都以源码为准）

- 多张卡把 `curlx_free` 解析成 `free — src/tool_xattr.c:150`（例：`Curl_cwriter_free`、`Curl_cwriter_create`、`cl_reset_writer` 的卡），实际是 lib 内的 `curlx_free`，与 src/tool_xattr.c 无关。
- 只经函数指针表调用的函数（`http2_connisalive`、`cf_socket_query`、`Curl_cf_ngtcp2_cmn_*`、`cf_quiche_*` 等）卡上“已解析调用者”为空；真实入口在 `Curl_conn_is_alive`、`Curl_conn_get_*`、`cf_hc_baller_reply_ms` 等经 `cft->is_alive`/`cft->query` 的间接调用点，需回源码追。
