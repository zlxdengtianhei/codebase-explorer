更新时间：Sun Oct 18 02:22:31 CEST 2026
A01–A28 全部完成（28/28）。
最终：keep 15、fix 12、drop 1（A03）；原始 rubric 共253条：成立236、部分16、不成立1、源码判不了0。
已生成 verdicts.jsonl（28题）、questions_verified.jsonl（27题）、dropped.md。
结果说明：$HOME/context-infra-lab-1/adhoc_jobs/codebase_explorer_20261016/scratch/opt_e5/v13a_result.md。
validation.json：cid/条目覆盖、字段/证据完整、题面/构建前提/权重/kind不变、keep原样、保留题>=6正向且>=2core，全部PASS。
核验仅为源码静态核验；未运行 curl/cbe 或正式闭卷过滤。没有修改候选与curl源码，没有读取禁读材料，没有派agent或调用模型API。
A03关键反例：url.c:2520在CONNECT交换前安装headers writer；http.c:3111又在真实请求前重建，首响应创建叙事不成立。
A20关键缺跳：SASL EXTERNAL优先；A18关键修订：bits.close先于零并发分支。
辅助 source_extract.py/build_review.py 保存只读取证和人工结论序列化逻辑，不参与正式题库输入。
