<h1 align="center"><img src="docs/media/logo.svg" width="40" height="40" alt="" align="absmiddle">&nbsp;Codebase Explorer</h1>
<p align="center">Codebase Explorer 把一个源码仓变成一页模块地图和逐模块的讲解：人能读，编码 agent 能查。</p>
<p align="center"><a href="README.md">English</a> | <b>简体中文</b></p>
<p align="center">
<a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
<a href="pyproject.toml"><img alt="Python 3.12 与 3.13" src="https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg"></a>
<a href="https://github.com/zlxdengtianhei/codebase-explorer/actions/workflows/wheel-install.yml"><img alt="CI" src="https://github.com/zlxdengtianhei/codebase-explorer/actions/workflows/wheel-install.yml/badge.svg"></a>
</p>

<p align="center"><img src="https://github.com/zlxdengtianhei/codebase-explorer/releases/download/walkthrough-v2.2.0.dev0/hero-2.gif" alt="35 秒动图：代码单元连线、聚成模块、显示系统地图；打开一个模块页，再用 cbe source 打印原始代码行" width="100%"></p>

<p align="center">35 秒：代码单元、连线、模块、地图、打开一个模块页、查看源码。<a href="docs/videos.md">带旁白的讲解视频</a>。</p>

文件树只告诉你文件在哪，不告诉你每一块是干什么的。CBE（Codebase Explorer）读一个仓库，写出文件树缺的那部分：一页列出整棵模块树（module tree），每个模块一行，说明它负责什么；再给每个模块一页，讲清其中每个函数和类，并链接到准确的源码行。你可以直接读。编码 agent 用三条命令就能在里面查。

**想试一下：** `uv tool install git+https://github.com/zlxdengtianhei/codebase-explorer`（需要 Python 3.12 或 3.13）。然后二选一：在 Claude Code 里用你自己的订阅生成；或在命令行接任意 OpenAI 兼容的端点生成（模型用 `--model` 指定）。步骤见[快速上手](#快速上手)。

## 能得到什么

- **一页地图。** `docs/INDEX.md` 列出整棵模块树，每个模块一行。页面大小的上限，取 2,000 token 与源码 token 数的 3% 中较大的那个。
- **一棵完整、每次都一样的树。** 树由程序建：互相调用或导入、位置相近、用词相近的代码单元（code unit）聚在一起。同样的输入得到同一棵树，没有空节点，也没有重复的模块。
- **每个模块一页。** 每个单元有签名、源码链接和模型写的讲解。讲解主要写给人读。
- **确定的事实靠命令查，不靠模型。** 签名、调用和源码行，用 `cbe find`、`cbe query` 和 `cbe source` 现查。`cbe source` 打印的是冻结快照里的源码；打印之前先核对每个文件的 SHA-256 与冻结时记下的值。

下面是为 flask 生成的真实 `docs/INDEX.md` 开头（未改动，原文为英文）：

```markdown
## Modules

- [**Request Serving Application Runtime**](nodes/request-serving-application-runtime.md) — Combines the concrete WSGI Flask application with request and response wrappers, templating, context lifecycle, and view-facing helpers needed to serve live requests. (136 units; `flask/app.py`, `helpers.py`, `wrappers.py`)
  - [**Request Helper Utilities and Tests**](nodes/request-helper-utilities-and-tests.md) — Provides view-facing helpers for files, flashing, redirects, streaming, and URL building, plus proxy globals and signal definitions, with focused behavioral tests. (42 units; `helpers.py`, `test_helpers.py`, `flask/blueprints.py`)
    - [**Helpers, globals, and signals**](nodes/helpers-globals-and-signals.md) — Provides view-facing helpers for sending files, flashing messages, redirecting, streaming, and URL building, plus proxy globals and Flask's blinker signal definitions. (26 units; `helpers.py`, `flask/blueprints.py`, `globals.py`)
    - [**Helper behavior tests**](nodes/helper-behavior-tests.md) — Verifies aborter selection and dispatch, app redirect delegation, open_resource read modes and encoding, and context-free redirect fallback behavior. (11 units; `test_helpers.py`)
    - [**File and URL tests**](nodes/file-and-url-tests.md) — Tests custom URL converters, send_file family behavior with path-like objects, stream_with_context lifetime, and url_for inside request contexts. (5 units; `test_helpers.py`, `test_converters.py`)
  - [**WSGI Request Dispatch Core**](nodes/wsgi-request-dispatch-core.md) — Implements the WSGI-callable Flask class and its pipeline: request entry, URL-to-view matching, response finalization, error handler resolution, and test and async wiring. (35 units; `flask/app.py`, `test_async.py`, `sansio/app.py`)
```

完整示例：[flask](examples/flask/docs/INDEX.md)。其余见[示例与文档](#示例与文档)。

## 快速上手

CBE 没有发布到 PyPI，需要 Python 3.12 或 3.13。有两种用法，最后都得到同一个 `docs/` 目录。

**A. 在 Claude Code 里用，花你自己的订阅额度。** 装上 Skill 后，由 Claude Code 的子代理（subagent）写讲解。

1. 安装 CBE：`uv tool install git+https://github.com/zlxdengtianhei/codebase-explorer`（或 `pipx install git+https://github.com/zlxdengtianhei/codebase-explorer`）。
2. 可选，要调用图（call graph）时：`cbe graph setup` 会把 Joern 和 Java 运行时下载到你的用户缓存目录（约 1.9 GB；支持 Linux x86_64 和 macOS）。
3. 在你的项目里装 Skill：`cbe-install install --host claude-code`。
4. 在那里启动 Claude Code，对它说：“Use the codebase-explorer skill to generate documentation for this repository.”
5. agent 会先报出计划的文件数、token 数、模块数和任务数，再跑子代理，最后校验结果。
6. 打开 `<run_dir>/docs/INDEX.md`，`run_dir` 由 agent 告诉你。

Claude Code 这条路径已经完整跑通过（见[成本](#成本)）。`cbe-install install --host` 还支持 `codex`、`opencode` 和 `dsh`：它们会装上 Skill，但我们没有完整跑过。详见 [docs/running.md](docs/running.md#generate-through-a-host-agent)。

**B. 在命令行里用，接任何兼容 OpenAI 的端点。** 没有缺省模型，必须给 `--model`。

1. 按上面的第 1 步安装 CBE。
2. 把密钥放进环境变量：`export CBE_API_KEY=...`
3. 可选：建调用图（`cbe graph setup`，再 `cbe graph build /abs/repo --output /abs/graph.json`）。
4. 生成。路径要写绝对路径：

   ```sh
   cbe generate /abs/repo --model MODEL --base-url https://your-endpoint.example/v1 \
     --api-key-env CBE_API_KEY --graph /abs/graph.json --run-dir /abs/run
   ```

5. 打开 `/abs/run/docs/INDEX.md`。不要调用图时，去掉 `--graph`。

然后查东西。`RUN` 是运行目录的绝对路径，ID 取 `find` 输出的第二列：

```sh
cbe find   --run-dir "$RUN" --term url_for
cbe query  --run-dir "$RUN" --id 'src/flask/helpers.py::function::url_for::6511'
cbe source --run-dir "$RUN" --id 'src/flask/helpers.py::function::url_for::6511' --context 2
```

其余命令和参数见 [docs/reference.md](docs/reference.md)。

## 怎样工作

```mermaid
flowchart LR
  A["冻结源码"] --> B["Tree-sitter 按语法边界切块"]
  B --> C["Joern 出调用图与导入图（可选）"]
  C --> D["模型写每个代码单元的讲解"]
  D --> E["程序把单元聚成模块树"]
  E --> F["模型给每个模块起名"]
  F --> G["渲染 INDEX.md、模块页、catalog.json"]
  classDef program fill:#dff7f3,stroke:#0f9b8e,color:#0f1b2d
  classDef model fill:#fff0cc,stroke:#c98a00,color:#0f1b2d
  class A,B,C,E,G program
  class D,F model
```

青色的步骤是普通程序，不调模型；琥珀色的步骤要调模型。

- **冻结。** CBE 留一份带哈希的源码副本，之后每个行号和引用都能核对。
- **切块。** Tree-sitter 按语法边界切每个文件，每个字节都落在某个块里，不调模型。
- **讲解。** 模型分批写讲解。它用清单里的短号指符号，所以编不出 ID；模型漏掉的符号，由程序再问一次。
- **聚合。** 模块树由程序而不是模型来建，依据是调用与导入、位置和用词。同样的输入得到同一棵树。
- **起名。** 模型给每个模块写名字、一句“负责什么”和两三句读法，不能增删或移动节点。
- **渲染。** 程序写出 `docs/INDEX.md`、每个模块一页、`DEPENDENCIES.md` 和 `RUN.md`，以及 `find`、`query`、`source` 读的 `catalog.json`。

## 调用图

没有图，CBE 照样能用。有图时，讲解任务和依赖视图还会得到静态的导入、调用和控制流证据。图由 [Joern](https://joern.io/) 生成，它需要 Java 21 或更高版本。`cbe graph setup` 会下载所钉版本的 Joern；机器上找不到合适的 Java 时，也会下载一个 Java 运行时，都放进你的用户缓存目录（合计约 1.9 GB）。`cbe graph setup --check` 不下载，只报告装了什么。之后 `cbe graph build` 写出 `--graph` 要用的图文件。它默认不导出数据流，要导出就加 `--with-dataflow`：生成过程不读数据流，而它在 flask 上占了图文件的一半以上（41 MB 里的 23 MB）。要手动装 Joern，见 [docs/reference.md](docs/reference.md#optional-graph-analyzers)。

| 状态 | 语言 | 条件 |
|---|---|---|
| 在真实仓库上能出图 | C、C++、Python、JavaScript、TypeScript、Java、Go、Ruby | Python 的导入用 Grimp（装 `graphs` 额外依赖）；JavaScript 和 TypeScript 的导入用 dependency-cruiser（要 Node.js）。Go 跨包的调用可能停在未解析。Ruby 的动态分派可能把调用绑到别的类里同名的方法上：CBE 把这类调用标成歧义，仍有一些错绑。 |
| 要额外工具 | Rust、PHP | Rust 要有 `cargo` 和 Cargo 工程布局。PHP 要有 `php`（7 或更高版本）。 |
| 在真实仓库上失败 | C#、Kotlin | Joern 4.0.654 在一个 55 个文件的 C# 仓库和一个 146 个文件的 Kotlin 仓库上建图失败。两个文件的小例子能跑，所以小输入可能成功。 |
| 未测试 | Swift、TSX | |

`cbe languages` 对每种语言打印同样的状态，字段名是 `call_graph`。不管调用图一栏写什么，表里每种语言的源码解析和切块都能用。CBE 的默认安装和两个额外依赖带有 13 种语言的 Tree-sitter 语法。分析器与建图选项见 [docs/reference.md](docs/reference.md#optional-graph-analyzers)。

## 成本

在 flask（含测试）上量得：65 个文件，125k token。模型是 GLM-5.3-Flash，用 `cbe generate` 调用，一次跑完。

| 指标 | 读数 |
|---|---|
| 提示 token | 源码 token 的 3.2–3.4 倍 |
| 输出 token | 约为源码 token 的 0.9 倍 |
| 模型写的讲解正文 | 约为源码 token 的 30% |
| 答案被拒后重问所占的提示 token | 约 22%（改答案格式之前是 43%；那次还因上游限流中途停下） |

这些读数是经一个兼容 OpenAI 的网关调用 GLM-5.3-Flash 量的。CBE 只对它认识的模型名自带缺省设置（例如 `reasoning_effort: low`）。换成别的模型名时，要用 `--config` 给出需要的设置；全部的键见 [docs/running.md](docs/running.md#api-configuration-keys)（英文）。

宿主 agent 这条路，在 flask 的 `src/`（24 个文件，约 7.5 万 token）上量过一次，用无界面的 Claude Code（`claude -p`）和 Sonnet 子代理：

| 指标 | 读数 |
|---|---|
| 子代理任务 | 8 个：4 个讲解批、1 个抽样复核、2 个树命名、1 个总览。全部第一次回答就被收下 |
| 墙钟 | 293 秒 |
| `cbe host verify` | 15 项检查全部通过 |
| token | 这次运行没有收集 |

每张表都只是一个仓库、一次运行。用宿主 agent 跑时花的是你的订阅额度，不用 API 密钥。建图不调模型。更早的成本表覆盖到 170 万 token 的仓库，放在 [docs/running.md](docs/running.md#what-a-run-costs-the-earlier-table)；它是在改答案格式之前量的，不要和上表直接比。

## 效果怎样

我们量了什么，量出了什么。每条都有前提；表格在 [`evaluation/tree/results/`](evaluation/tree/results/)。

最先读的那一页变小了。下表是这一页的大小（`o200k_base` token），在三个完整运行上量得；“之前”一列是上一版的树：

| 仓库 | 之前 | 现在 | 空节点 之前 / 现在 |
|---|---:|---:|---:|
| flask | 16,076 | 3,078 | 22 / 0 |
| ruby_llm | 15,938 | 2,074 | 8 / 0 |
| gson | 12,643 | 2,514 | 16 / 0 |

- **树的结构。** 在上面三个仓库里，新树没有空节点，也没有重复的模块。之前的树分别有 22、8、16 个空节点。
- **调用的标签。** 在七个仓库里，每种状态各抽 10 条边，回源码核对。例如 cJSON 的 307 条“未解析”调用全是宏，现在不再算调用；fmt 里标成“仓外”的调用从 2,748 条降到 22 条。
- **树能不能帮你找到该读的代码？** 我们从五个仓库各取 30 条真实提交，请三种模型回答“这次改动该看哪三个模块”。新树和旧树分不出好坏。与只给目录列表相比，目录本来就有层次的仓库里，模块树没有明显差别；只有目录很平的仓库（flask、fmt）里它才缩小了要读的范围：选出的三个模块约占源码的 40%，覆盖了约 0.75–0.8 的改动行。
- **这把尺子有多可信。** 它自己也吵：同一个问题再问一遍，模型的答案完全一致的只有 30 次里的 9 到 23 次。
- **更早的问答评测**（那时的 CBE 还没有程序建的树）。在 flask 和 pytest 上（各 48 题），带 CBE 文档和命令的 agent 与只读源码的 agent 得分没有差别，而且很少去跑那些命令。在 curl 上有一次探索性读数，带 CBE 的一方得分更高（+5.60 分，区间 [+0.90, +10.82]），它附带的限制写在 [evaluation/README.md](evaluation/README.md) 里。

我们不声称：按功能聚合能让 agent 比用目录树定位得更准，也不声称 CBE 能提高 agent 的回答质量。上面的测量没有证明这两件事。

## 已知限制

- 调用图依赖 Joern 和 Java 21 或更高版本。`cbe graph setup` 会把两者都下载下来（约 1.9 GB）。
- C# 和 Kotlin 在真实仓库上用所钉的 Joern 版本建图失败。两个文件的小例子能跑。
- Ruby 的动态分派可能把调用绑到错误的类的同名方法上。CBE 把其中许多标成歧义，仍有一些错绑。
- C 和 C++ 文件不跑预处理。宏多的头文件会被切得很粗，宏可能被当成函数名。
- 讲解由模型写。`cbe host verify` 通过，只说明结构和引用自洽，不说明讲解是对的。请用 `cbe source` 对照源码核实。
- 没有增量更新：源码变了，要重新生成。
- CBE 还没有发布到 PyPI。

## 示例与文档

- 生成好的文档：[flask](examples/flask/docs/INDEX.md)、[cJSON](examples/cjson/)、[fmt](examples/fmt/)、[gson](examples/gson/)、[ruby_llm](examples/ruby_llm/)、[tsdown](examples/tsdown/)、[polyglot](examples/polyglot/)。每个示例的 README 写明了生成它的 CBE 提交；多数由较早的版本生成。
- [docs/reference.md](docs/reference.md)：安装选项、语言、图分析器、`find`、`query`、`source`、命名声明覆盖（英文）。
- [docs/running.md](docs/running.md)：宿主 agent 与 API 两种运行方式、运行目录、续跑与校验、成本细账、排错（英文）。
- [docs/videos.md](docs/videos.md)：讲解视频（英文）。
- [evaluation/README.md](evaluation/README.md) 与 [CHANGELOG.md](CHANGELOG.md)（英文）。

## 开发与许可

```sh
uv sync --python 3.13 --group dev
uv run pytest -q
```

需要真实分析器的测试，要先配好那个分析器。本产品的许可证是 [MIT](LICENSE)；外部分析器和语法包保留各自的许可证。
