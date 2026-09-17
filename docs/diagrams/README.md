# 架构图双轨约定

README 使用 [Archify](https://github.com/tt-a1i/archify) 导出的双主题 SVG。`docs/` 规格、设计文档和 `ARCHITECTURE.md` 继续使用 Mermaid 源文件。两套图表达同一产品事实，视觉实现分开。

## 目录

| 轨道 | 路径 | 用途 |
| --- | --- | --- |
| Docs / Mermaid | `docs/diagrams/*.mmd` | 规格与设计文档的拓扑源。保持完整关系，不删节点去迁就排版。 |
| README / Archify IR | `docs/diagrams/archify/*.json` | Archify 校验用的 JSON IR。showcase 质量，主路径清晰，大约 8–12 个节点。 |
| README / SVG | `docs/assets/archify/*.svg` | 写入中英文 README 的双主题静态预览。GitHub Markdown 不能运行查看器。 |
| Interactive HTML | `docs/assets/archify/*.html` | 自包含 Archify 查看器：点选节点、章节、关系追踪、主题、导出。GitHub Pages：[全部架构图](https://untiljing-git.github.io/lumiagent/assets/archify/index.html)。 |
| Docs / 既有 SVG | `docs/assets/*.svg` | 由 Mermaid 导出、已被 `docs/` 引用的图。不要为了 README 而删除。 |

不要把 Archify 仓库 vendoring 进本项目。交付快照和 `visual-check` 截图被 `.gitignore` 忽略。交互 HTML 与 SVG 需要提交。

## 何时需要两套

新增或修改**产品架构 / 采集流 / 证据层 / 运行时分层**图时，必须同时更新：

1. `docs/diagrams/<name>.mmd`（完整拓扑，给 docs）
2. `docs/diagrams/archify/<name>.json`（README 用，可在节点过多时合并旁路，但标识符与分层关系必须与 mmd 一致）
3. `docs/assets/archify/<name>.svg`（README 静态预览）
4. `docs/assets/archify/<name>.html`（浏览器交互查看器）

纯文档示意、一次性讨论稿、或尚未进入 README 的草图可以先只写 mmd。一旦该图出现在 README，补齐 Archify 轨道。

## README 可简化、docs 不删细节

Archify showcase 不适合 20+ 节点的密图。遇到 `trace-core-visualization-intent`、`mcp-tool-chain-evidence-layer` 这类图：

- mmd 保留完整分层与旁路
- Archify 只画主路径和边界，细节写进卡片，不从 mmd 里删节点

## 当前对照

| 主题 | Archify JSON | README SVG | 交互 HTML | Docs Mermaid |
| --- | --- | --- | --- | --- |
| 运行时分层 | [`archify/runtime-architecture.json`](archify/runtime-architecture.json) | [`../assets/archify/runtime-architecture.svg`](../assets/archify/runtime-architecture.svg) | [Pages](https://untiljing-git.github.io/lumiagent/assets/archify/runtime-architecture.html) | [`runtime-architecture.mmd`](runtime-architecture.mmd) |
| Trace Core 模型 | [`archify/trace-core-model.json`](archify/trace-core-model.json) | [`../assets/archify/trace-core-model.svg`](../assets/archify/trace-core-model.svg) | [Pages](https://untiljing-git.github.io/lumiagent/assets/archify/trace-core-model.html) | [`trace-core-model.mmd`](trace-core-model.mmd) |
| 可视化意图 | [`archify/visualization-intent.json`](archify/visualization-intent.json) | [`../assets/archify/visualization-intent.svg`](../assets/archify/visualization-intent.svg) | [Pages](https://untiljing-git.github.io/lumiagent/assets/archify/visualization-intent.html) | [`trace-core-visualization-intent.mmd`](trace-core-visualization-intent.mmd) |
| MCP 证据层 | [`archify/mcp-evidence-layer.json`](archify/mcp-evidence-layer.json) | [`../assets/archify/mcp-evidence-layer.svg`](../assets/archify/mcp-evidence-layer.svg) | [Pages](https://untiljing-git.github.io/lumiagent/assets/archify/mcp-evidence-layer.html) | [`mcp-tool-chain-evidence-layer.mmd`](mcp-tool-chain-evidence-layer.mmd) |
| MCP 采集 + 展示 | [`archify/mcp-capture-display.json`](archify/mcp-capture-display.json) | [`../assets/archify/mcp-capture-display.svg`](../assets/archify/mcp-capture-display.svg) | [Pages](https://untiljing-git.github.io/lumiagent/assets/archify/mcp-capture-display.html) | [`mcp-capture-display-chain.mmd`](mcp-capture-display-chain.mmd) |
| Coding Agent 采集 | [`archify/coding-agent-capture.json`](archify/coding-agent-capture.json) | [`../assets/archify/coding-agent-capture.svg`](../assets/archify/coding-agent-capture.svg) | [Pages](https://untiljing-git.github.io/lumiagent/assets/archify/coding-agent-capture.html) | [`coding-agent-capture-flow.mmd`](coding-agent-capture-flow.mmd) |

## 重新导出 README 图

需要 Node.js 18+、Chrome，以及本机 clone 的 Archify（含 `bin/archify.mjs` 的 `archify/archify` 目录）：

```powershell
git clone --depth 1 https://github.com/tt-a1i/archify "$env:TEMP\archify"
$env:ARCHIFY_ROOT = "$env:TEMP\archify\archify"
node scripts/render-archify.mjs
```

脚本会对 `docs/diagrams/archify/*.json` 做 showcase 校验、交付 HTML，并用 Chrome 导出双主题 SVG。校验失败时只改被诊断的字段，不要顺手改拓扑。

本地打开交互图：

```powershell
start docs/assets/archify/index.html
```

GitHub 上的 README 图片仍是静态的。交互查看器由 GitHub Pages 托管：https://untiljing-git.github.io/lumiagent/assets/archify/index.html

新增一张 README 架构图时：先写 mmd，再写 Archify JSON，把 stem 加入 `scripts/render-archify.mjs` 的 `diagrams` 列表，然后跑导出，最后把 SVG 链进 `README.md` / `README.zh-CN.md`。
