# PID-HOST 文档清单

版本：v0.2
日期：2026-07-09

本文档用于追踪 PID-HOST 当前阶段真正需要维护的文档。外部评审提出的完整发布级文档体系有参考价值，但第一版先控制规模，优先保证规格、协议和启动说明能直接指导开发。

## 当前原则

- 文档服务于实现，不提前创建大量空壳文件。
- 第一版优先覆盖：软件设计、下位机协议、运行入口、开发环境和许可证。
- API 文档、贡献指南、完整用户手册等在代码稳定或确实需要外部协作后再补。

## v1.0 前必须完成

| 文档 | 状态 | 说明 |
| --- | --- | --- |
| `README.md` | 已有初版 | 项目简介、第一版范围、文档入口和当前状态。 |
| `docs/spec.md` | 已有初版 | 正式软件设计规格，已补串口参数、命令模型、错误码和线程模型。 |
| `docs/protocol-for-mcu.md` | 已有初版 | 面向下位机开发者的 UART JSON Lines 协议手册。 |
| `docs/dev-setup.md` | 待写 | Python 版本、虚拟环境、依赖安装、运行测试和模拟模式。 |
| `LICENSE` | 待定 | 开源许可证，建议后续在 MIT 和 GPL-3.0 中选择。 |

## v1.0 前后建议完成

| 文档 | 状态 | 说明 |
| --- | --- | --- |
| `docs/integration-checklist.md` | 可从协议手册拆出 | 联调清单当前已包含在 `docs/protocol-for-mcu.md`。 |
| `docs/roadmap.md` | 待写 | 多版本规划稳定后再单独整理。 |
| `CHANGELOG.md` | 待写 | 第一个可运行版本出现后开始维护。 |
| `docs/user-guide.md` | 待写 | UI 成型后补截图和操作流程。 |

## 暂缓

| 文档 | 暂缓原因 |
| --- | --- |
| `docs/ui-spec.md` | 当前 UI 仍在第一版设计阶段，先在 `docs/spec.md` 中维护。 |
| `docs/architecture.md` | 当前架构说明已在 `docs/spec.md`，避免重复。 |
| `docs/csv-format.md` | CSV 字段已在 `docs/spec.md`，用户分析需求明确后再拆分。 |
| `docs/coding-style.md` | 团队或外部贡献者出现后再补。 |
| `CONTRIBUTING.md` | 暂无外部 PR 流程。 |
| `docs/api/` | 代码模块尚未稳定，自动或半自动生成更合适。 |

## 当前文档关系

```text
README.md
  -> docs/spec.md
  -> docs/protocol-for-mcu.md
  -> docs/DOCUMENTATION_INVENTORY.md

docs/superpowers/specs/2026-07-09-pid-host-design.md
  -> brainstorming 过程产物，作为设计来源保留
```

## 外部评审采纳情况

已采纳：

- 默认 UART 参数：`115200 8N1`，无流控。
- JSON Lines 接收兼容 `\n` 和 `\r\n`。
- 第一版采用逐一应答命令模型。
- `ack_timeout_ms = 1000`。
- 错误码表：`bad_json`、`bad_type`、`missing_field`、`bad_value`、`unsupported`、`busy`。
- UI 主线程与串口 worker 线程分离。
- 上位机参数校验与下位机重复校验并存。

暂不采纳：

- 一次性创建 20 多份文档。
- 第一版维护 `docs/protocol.md`、`docs/api/protocol.md` 等重复协议文档。
- 在没有代码实现前编写完整模块 API 文档。
