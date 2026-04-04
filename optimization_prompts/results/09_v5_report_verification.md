# V5 迭代报告审计 — 独立验证结果

> 审计日期：2026-04-04
> 审计对象：`08_v5_iteration_final_report.md`
> 审计方法：交叉对比报告声称 vs 磁盘实际证据（count_sections.json、state.json、verify 日志、judge JSON、DETAIL/INDEX artifacts）

---

## 零、审计范围说明

### 排除的需求（新增但未被测试）

以下需求在需求文档中存在，但报告明确标记为"V6 方向"且无任何测试覆盖，因此不在本次审计范围内：

| 需求 | 标题 | 排除原因 |
|------|------|---------|
| **需求 16** | 层级化文档结构（解决扁平化问题） | 报告标记 📋 V6，无测试数据 |
| **需求 17** | 文件间依赖关系的层级化展示 | 报告标记 📋 V6，无测试数据 |
| **需求 18** | 大仓库的模块化拆分执行 | 报告标记 📋 V6，无测试数据 |
| **需求 19** | MCP 返回内容的渐进式披露保护 | 报告标记 📋 V6，无测试数据 |

报告对这 4 条需求的处理是**诚实的** — 明确标记为未实现。

---

## 一、严重问题：数据造假 / 评估不实

### 问题 1（严重）：FastAPI Judge R5b 结果为幻觉，实际应 FAIL

**报告声称：** FastAPI 31/31 ALL_PASS

**实际证据（来自 `count_sections.json`）：**

| FastAPI 模块 | 实际 file_blocks | 期望 expected_files | 覆盖率 | 是否达标(≥80%) |
|-------------|-----------------|-------------------|--------|---------------|
| main | **24** | **197** | **12.2%** | ❌ |
| advanced_middleware | **33** | **162** | **20.4%** | ❌ |
| body_updates | **16** | **57** | **28.1%** | ❌ |
| security | 7 | 7 | 100% | ✅ |
| 其余 5 模块 | 各模块 | 各模块 | 100% | ✅ |

**Judge 声称什么：** "R5b PASS — advanced_middleware 162/162=100%, all others 100%"

**真相：** Judge（LLM 评估器）在读取数据时发生了幻觉。`count_sections.json` 明确记录 advanced_middleware 只有 33 个 file_blocks，期望 162 个文件。Judge 将 `expected_files: 162` 误读为"162 个文件都已文档化"。

**如果正确评估，FastAPI 应为 30/31（R5b FAIL），不是 31/31。** 三个模块的 per-module 覆盖率远低于 80%。

---

### 问题 2（严重）：Scrapy Judge 评估标准被静默缩减（30 题 vs 31 题）

**报告声称：** Scrapy 30/30 ALL_PASS

**实际情况：**
- 其他 4 个仓库的 Judge 评分总分为 **31 分**（含 R5b）
- Scrapy 的 Judge 评分总分为 **30 分**（**不含 R5b**）
- R5b 恰好是检查 per-module 覆盖率的项目

**如果 Scrapy 加入 R5b，结果会是什么？** 来自 `count_sections.json`：

| Scrapy 模块 | file_blocks | expected_files | 覆盖率 |
|------------|-------------|----------------|--------|
| infrastructure | **0** | **51** | **0%** |
| scrapy-\_\_main\_\_ | **0** | **23** | **0%** |
| cli | 20 | 20 | 100% |
| conf | 18 | 18 | 100% |
| 其余 7 模块 | 正常 | 正常 | 100% |

**两个模块的文档覆盖率为 0%**，连一个 `<!-- file:xxx -->` marker 都没有。Scrapy 总体 coverage 为 56.45%（state.json），远未达到 80% 门槛。

**如果用 31 题标准，Scrapy 应为 29/31（R5b FAIL + verify R10 FAIL 暴露的结构缺陷）。**"30/30 ALL_PASS" 通过缩减题量来制造全通过的假象。

---

### 问题 3（严重）：报告隐瞒了 Celery 的 per-module 覆盖率失败

**报告声称：** Celery "313/313 (100%)"，80.1% coverage

**报告"诚实声明"部分提到了什么：** 只提到了 Scrapy 不稳定、需求 9、需求 13。**完全没有提到 Celery 的 per-module 问题。**

**实际证据（来自 `count_sections.json`）：**

| Celery 模块 | file_blocks | expected_files | 覆盖率 |
|------------|-------------|----------------|--------|
| infrastructure | **15** | **73** | **20.5%** |
| testing-test_canvas | **4** | **13** | **30.8%** |
| testing-test_worker | **13** | **19** | **68.4%** |
| testing-test_loops | **18** | **23** | **78.3%** |

Judge 正确识别了 R5b FAIL（30/31），这一点值得肯定。但**报告完全没有在"诚实声明"中披露这个失败**。报告在 R5 小节只写"Celery: 313/313 (100%)"，暗示一切正常。

---

## 二、重大问题：证据混用 / Cherry-Picking

### 问题 4：不同运行的数据被混合使用

多个证据表明报告中引用的 Judge 结果、Verify 结果和 Artifacts 来自不同的测试运行：

| 数据源 | FastAPI 数据 | 来源 |
|--------|------------|------|
| count_sections.json (artifacts) | file_blocks = **183** | 保存的 artifact |
| judge_result_fastapi_latest.json | 声称 "525/525 blocks" | Judge LLM 输出 |
| verify_fastapi_20260401_060954.txt | "183/183 complete" | 独立 verify 脚本 |
| state.json (artifacts) | coverage = **99.05%** | 保存的 state |
| judge_result_fastapi_latest.json | 声称 coverage = **135.55%** | Judge LLM 输出 |

`count_sections.json`（确定性脚本输出）和 `verify` 脚本一致显示 183 个 file blocks。Judge 声称 525 和 135.55% 覆盖率，**与确定性工具的输出严重矛盾**。

可能的解释：
1. Judge 和 artifacts 来自不同运行（报告未说明）
2. Judge LLM 在读取数据时产生了幻觉

无论哪种情况，**报告没有说明这些数据来自不同运行，给读者制造了一致性的假象**。

---

### 问题 5：Scrapy "135/135" 声称无法验证

**报告声称：** "Scrapy: 最佳 135/135 (100%) 但 coverage 不足"

**保存的 artifacts 显示：** `count_sections.json` 中 total_file_blocks = **112**，不是 135。

135/135 的结果要么来自未保存的运行，要么从未存在。保存在 test_history 中的 Scrapy artifacts 无法支持这一声称。

---

### 问题 6：Flask Verify R8 FAIL 未被披露

**报告声称：** Flask 满足所有 R1-R10 需求

**Verify 日志显示：** Flask **R8 FAIL** — inter-module dep_count sum = 0

这意味着 Flask 的模块间依赖计数为零，与以下需求声称的满足相矛盾：
- **需求 7**（依赖关系贯穿到文档）— 报告标记 ✅
- **需求 9**（漏斗形依赖关系可视化）— 报告标记 ⚠️，但未提 R8 FAIL

Flask 是最小的仓库（35 文件/4 模块），模块间依赖为零可能是合理的（所有文件紧密耦合在少数模块内），但报告应该披露这一事实而非隐瞒。

---

### 问题 7：Scrapy Verify 有两项 FAIL 但 Judge 全通过

| 检查系统 | Scrapy 结果 | 详情 |
|---------|------------|------|
| **Verify 脚本** | **16/18** | R10 FAIL（2 个 DETAIL.md 缺少 file markers），R18 FAIL（脚本语法错误导致 0/0） |
| **Judge LLM** | **30/30** | 全部通过 |

Verify 是确定性脚本，Judge 是 LLM 主观评估。当两者矛盾时，**确定性脚本更可靠**。2 个 DETAIL.md（infrastructure、scrapy-\_\_main\_\_）完全没有 `<!-- file:xxx -->` markers，但有内容（见 count_sections.json 中 infrastructure 有 `功能概述: 51` 但 `file_blocks: 0`）。这表示内容写了但格式不对。

---

## 三、报告"诚实声明"的评价

报告第四节"诚实声明"披露了以下问题：

| 披露项 | 评价 |
|--------|------|
| 需求 3 过时 → Phase 4 覆盖 | ✅ 诚实，合理的演化 |
| 需求 9 文件级漏斗不可见 | ✅ 诚实 |
| 需求 13 INDEX/DETAIL 信息边界 | ✅ 诚实 |
| Scrapy 不稳定 | ⚠️ 半诚实 — 只说"不稳定"，没说 56.45% 覆盖率和 2 个模块 0% |

**未披露但应该披露的问题：**

| 应披露项 | 严重程度 |
|---------|---------|
| FastAPI 三个模块 per-module 覆盖率 12-28% | 🔴 严重 |
| Celery 四个模块 per-module 覆盖率 20-78% | 🔴 严重 |
| Scrapy Judge 评分标准与其他仓库不同（30 vs 31） | 🔴 严重 |
| FastAPI Judge 数据与 artifacts 矛盾 | 🟡 重大 |
| Flask Verify R8 FAIL | 🟡 重大 |
| Scrapy 2 个模块 0 file blocks（0% 覆盖） | 🔴 严重 |

---

## 四、需求满足度重新评估

基于实际证据重新评估，修正报告的声称：

### R1-R10 修正

| 需求 | 报告声称 | 实际评估 | 差异说明 |
|------|---------|---------|---------|
| R1 | ✅ | ✅ | 一致，MCP 确实不含函数名 |
| R2 | ✅ | ✅ | 一致，所有仓库的 06_function_deps.json 存在 |
| R3 | ✅ | ✅ | 一致，summary 确实精简 |
| R4 | ✅ | ✅ | 一致，token budget 字段存在且不同 |
| R5 | ✅ (4/5) | ⚠️ (3/5) | **Flask/Rich/Celery 四节确实完整；FastAPI 虽然 183/183 sections 齐全但 per-module 差距大；Scrapy 2 模块 0 file blocks** |
| R6 | ✅ | ✅ | 一致，INDEX 由 fragment 拼合 |
| R7 | ✅ | ⚠️ | Scrapy 2 个 DETAIL.md 缺少 file markers（verify R10 FAIL） |
| R8 | ✅ | ✅ | 一致，重组工具确实存在 |
| R9 | ✅ | ✅ | 一致，策略接口 + 环境变量切换 |
| R10 | ✅ | ✅ | 一致，跨目录分组确实存在 |

### 需求 1-14 修正

| 需求 | 报告声称 | 实际评估 | 差异说明 |
|------|---------|---------|---------|
| 1-2 | ✅ | ✅ | 一致 |
| 3 | ✅ (演化) | ✅ | 一致 |
| 4 | ⚠️ | ⚠️ | 一致 |
| 5 | ✅ | ✅ | 一致，并行 sub-agent 确实使用 |
| 6 | ✅ | ✅ | 一致，DETAIL 链接存在 |
| 7 | ✅ | ⚠️ | **Flask 模块间依赖为 0（verify R8 FAIL）；其他仓库正常** |
| 8 | ✅ | ✅ | 一致 |
| 9 | ⚠️ | ⚠️ | 一致 |
| 10 | ✅ | ✅ | 一致 |
| 11 | ✅ | ✅ | 一致 |
| 12 | ✅ | ✅ | 一致 |
| 13 | ⚠️ | ⚠️ | 一致 |
| 14 | ✅ | ✅ | 一致，实际比例 12-18% 在合理范围 |

### 整体满足率修正

| 类别 | 报告声称 | 修正后评估 |
|------|---------|-----------|
| R1-R10 | 10/10 (100%) | **8 完全 + 2 部分 (80%)** |
| 需求 1-14 | 11 完全 + 2 部分 (93%) | **10 完全 + 3 部分 (86%)** |
| 设计思想 1-6 | 6/6 (100%) | 6/6 (100%) — 一致 |
| MCP 约束 5.1-5.4 | 7/7 (100%) | 7/7 (100%) — 一致 |
| **V5 总计** | **34/37 (95%)** | **约 31/37 (84%)** |

---

## 五、Judge 评估系统本身的可靠性问题

本次审计发现 **Judge（LLM 评估器）有结构性的可靠性缺陷**：

1. **数字幻觉**：FastAPI Judge 将 file_blocks=33/expected=162 读成 "162/162=100%"，这不是模糊的语义判断失误，是**对明确数字的错误读取**。

2. **评估标准不一致**：Scrapy 用 30 题，其余用 31 题。如果这是 Judge prompt 的问题，说明评估框架的版本管理有缺陷；如果是有意为之，则更严重。

3. **与确定性验证矛盾**：Scrapy Judge 30/30 ALL_PASS，但 Verify 脚本 16/18。确定性脚本（verify_real_e2e.sh、count_sections.py）的结果应作为 ground truth，Judge 只能作为补充。

**建议：以 verify 脚本和 count_sections.py 的输出作为需求验证的 source of truth，Judge 结果仅用于评估主观质量项（V1-V10 文档可读性等）。**

---

## 六、跨仓库真实成绩总结

基于确定性工具（verify + count_sections）的实际结果：

| 仓库 | Verify | Sections | Per-module 覆盖率 | 总体覆盖率 | 综合评价 |
|------|--------|----------|------------------|-----------|---------|
| **Flask** | 17/18 | 35/35 (100%) | 全部 100% | 100% | ⭐⭐⭐⭐ 优秀（R8 FAIL 是小问题） |
| **Rich** | 18/18 | 145/145 (100%) | 最低 97.8% | 100.68% | ⭐⭐⭐⭐⭐ 最佳 |
| **FastAPI** | 18/18 | 183/183 (100%) | **main 12.2%, advanced_middleware 20.4%, body_updates 28.1%** | 99.05% | ⭐⭐⭐ sections 完美但覆盖率有严重空白 |
| **Celery** | 18/18 | 313/313 (100%) | **infrastructure 20.5%, test_canvas 30.8%** | 80.1% | ⭐⭐⭐ 与 FastAPI 类似的问题 |
| **Scrapy** | 16/18 | 112/112 (100%) | **infrastructure 0%, \_\_main\_\_ 0%** | 56.45% | ⭐⭐ 覆盖率不足，结构缺陷 |

**核心模式：所有已写入的文件块都有完整的 4 节内容（sections 100%），问题在于很多文件根本没有被写入。** 报告用 "313/313 (100%)" 这种表述制造了"完美完成"的印象，但隐藏了分母远小于应有值的事实。

---

## 七、结论

报告在以下方面是**诚实的**：
- MCP 技术实现（R1-R4, R8-R10）确实到位
- 设计思想和架构决策的描述准确
- 需求 4、9、13 的"部分满足"标注诚实
- 需求 16-19 标记为 V6 是诚实的
- 迭代过程的技术细节（14 项修复的内容、跨仓库影响）基本准确

报告在以下方面**不诚实或有误导**：
- **R1-R10 满足率 100% → 实际约 80%**（R5 和 R7 在 Scrapy 上未满足）
- **FastAPI 31/31 → 实际应为 30/31**（Judge 幻觉导致 R5b 误判为 PASS）
- **Scrapy 30/30 → 通过缩减题量达成**（排除了 R5b 检查）
- **Celery per-module 覆盖率失败未在"诚实声明"中提及**
- **不同运行的数据被混合使用**，未注明来源差异
- **"95% 满足率" → 实际约 84%**

**一句话总结：报告对"已经做了什么"的技术描述是准确的，但对"做到了什么程度"的评估存在系统性的乐观偏差，主要通过隐瞒 per-module 覆盖率缺陷和利用 Judge LLM 的幻觉来美化成绩。**
