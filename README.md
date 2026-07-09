# PID-HOST

PID-HOST 是一个面向 Windows 桌面的 PID 上位机项目，用于通过 UART/USB 转串口连接下位机，完成单路 PID 参数设置、实时曲线监控、日志查看和 CSV 数据记录。

当前项目处于设计与脚手架准备阶段。第一版目标是做一个稳定可用的“调参 + 监控 + 记录”工具，而不是把上位机放进实时控制闭环。

## 第一版范围

- Python + PySide6 + PyQtGraph 桌面应用。
- UART/USB 转串口通信，默认 `115200 8N1`，无流控。
- JSON Lines 协议，每条消息以换行结束。
- 下位机运行 PID 闭环，上位机负责设置 `Kp/Ki/Kd` 和 `SP`。
- 单路 PID，协议预留 `ch` 字段，第一版固定为 `0`。
- 实时显示 `SP`、`PV`、`OUT` 三条曲线。
- 支持 CSV 录制、参数保存/加载、事件日志和模拟数据模式。

## 文档

- [软件设计规格](docs/spec.md)
- [下位机协议手册](docs/protocol-for-mcu.md)
- [文档清单](docs/DOCUMENTATION_INVENTORY.md)
- [原始 brainstorming 设计稿](docs/superpowers/specs/2026-07-09-pid-host-design.md)

## 当前状态

代码尚未开始实现。下一步会根据 `docs/spec.md` 拆分实现计划，并建立 Python 工程结构、依赖配置和测试框架。
