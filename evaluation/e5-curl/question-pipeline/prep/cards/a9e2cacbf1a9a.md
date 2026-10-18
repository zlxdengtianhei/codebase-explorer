# a9e2cacbf1a9a

函数／公开声明：`curl_version`
文件：`lib/version.c:140`
区域：传输与 multi 状态机（transport）
类型：function；分派锚点：false
建议层：3；可结合图中的邻接单元或公开声明对应实现追踪流程。

仅来源于指定 Joern 图和源码；条件编译分支并存，不代表某种构建全部启用。
公共声明的图根为同名 lib 实现；分派处不据词法匹配推断真实目标。

## 两跳内已解析调用者

- 1 跳：`ourWriteOutJSON` — `src/tool_writeout_json.c:97`
- 2 跳：`ourWriteOut` — `src/tool_writeout.c:732`

## 两跳内已解析被调者

- 1 跳：`Curl_ldap_version` — `lib/ldap.c:946`
- 2 跳：`curl_msnprintf` — `lib/mprintf.c:1272`

## 相关函数指针表（词法引用；同文件或引用锚点／邻接函数）

- 未匹配到相关表。

## 相关间接调用点

table_type_candidate_only 仅表示表类型相容；不是已解析调用关系。

- 未匹配到相关调用点。
