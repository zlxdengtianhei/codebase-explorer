# A 半淘汰题

A03 — 题面隐含创建时机不成立，且构建前提不能保证唯一。

不成立：构建前提未关闭 headers API，默认启用时 Curl_connect 在 lib/url.c:2520 先调用 Curl_headers_init，经 Curl_cwriter_add 建初始栈，发生在非阻塞 CONNECT 交换前。题面要求解释“during the CONNECT exchange”创建与参考答案的首头惰性创建不符；禁用 headers API 又是另一条路径。不能不改题面或构建前提而保证唯一创建时机，故 drop。

关键路径：Curl_connect（lib/url.c:2518–2520）→ Curl_headers_init（lib/headers.c:442）→ Curl_cwriter_add（lib/sendf.c:481）→ do_init_writer_stack。连接完成隧道后 Curl_client_reset 清掉这些 writer，而 Curl_http（lib/http.c:3111）在发送真实请求前再次安装 headers collector 并重建 writer 栈。

不能只改参考答案而保留“during the CONNECT exchange”的创建前提。若主会话日后另出一题，应明确询问 setup/CONNECT/real request 三阶段，或明确禁用 headers API；本次不修改题面。
