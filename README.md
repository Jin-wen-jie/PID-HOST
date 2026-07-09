# PID-HOST

PID-HOST 是一个面向 Windows 桌面的 PID 上位机项目，用于通过 UART/USB 转串口连接下位机，完成单路 PID 参数设置、实时曲线监控、日志查看和 CSV 数据记录。

当前已经具备第一版可运行软件骨架：协议、数据缓存、CSV 录制、配置保存、模拟数据模式和 PySide6 桌面界面。第一版目标是做一个稳定可用的“调参 + 监控 + 记录”工具，而不是把上位机放进实时控制闭环。

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
- [开发环境搭建](docs/dev-setup.md)
- [文档清单](docs/DOCUMENTATION_INVENTORY.md)
- [原始 brainstorming 设计稿](docs/superpowers/specs/2026-07-09-pid-host-design.md)

## 快速开始

双击启动：

- 桌面 `PID-HOST` 快捷方式：真实串口模式
- `Start-PID-HOST.bat`：真实串口模式
- `Start-PID-HOST-Demo.bat`：模拟数据模式

首次运行前建议先安装依赖：

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
pid-host --demo
```

也可以在源码目录直接运行：

```powershell
$env:PYTHONPATH='src'
python -m pid_host --demo
```

运行测试：

```powershell
python -m pytest
```
