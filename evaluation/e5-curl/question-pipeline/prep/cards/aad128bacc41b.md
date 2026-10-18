# aad128bacc41b

函数／公开声明：`Curl_ipv4_resolve_r`
文件：`lib/vdns/hostip4.c:100`
区域：DNS（dns）
类型：function；分派锚点：false
建议层：4；可结合邻接单元和源码契约分析改动影响；设计理由须另核注释。

仅来源于指定 Joern 图和源码；条件编译分支并存，不代表某种构建全部启用。
公共声明的图根为同名 lib 实现；分派处不据词法匹配推断真实目标。

## 两跳内已解析调用者

- 图中无可列出的已解析邻接函数。

## 两跳内已解析被调者

- 1 跳：`Curl_he2ai` — `lib/curl_addrinfo.c:258`
- 1 跳：`free` — `src/tool_xattr.c:150`
- 2 跳：`Curl_freeaddrinfo` — `lib/curl_addrinfo.c:71`

## 相关函数指针表（词法引用；同文件或引用锚点／邻接函数）

- 未匹配到相关表。

## 相关间接调用点

table_type_candidate_only 仅表示表类型相容；不是已解析调用关系。

- 未匹配到相关调用点。
