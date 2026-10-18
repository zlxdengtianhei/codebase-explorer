# ace64bd7936ab

函数／公开声明：`save_etag`
文件：`src/tool_cb_hdr.c:276`
区域：命令行工具 src/（cli）
类型：function；分派锚点：false
建议层：4；可结合邻接单元和源码契约分析改动影响；设计理由须另核注释。

仅来源于指定 Joern 图和源码；条件编译分支并存，不代表某种构建全部启用。
公共声明的图根为同名 lib 实现；分派处不据词法匹配推断真实目标。

## 两跳内已解析调用者

- 1 跳：`tool_header_cb` — `src/tool_cb_hdr.c:425`

## 两跳内已解析被调者

- 1 跳：`fwrite` — `include/curl/stdcheaders.h:30`

## 相关函数指针表（词法引用；同文件或引用锚点／邻接函数）

- 未匹配到相关表。

## 相关间接调用点

table_type_candidate_only 仅表示表类型相容；不是已解析调用关系。

- 未匹配到相关调用点。
