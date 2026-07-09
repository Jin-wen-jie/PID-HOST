# PID-HOST 开发环境搭建

日期：2026-07-09

## 环境要求

- Windows 10/11。
- Python 3.11 或更高版本。
- UART/USB 转串口设备。常见 CH340、CP2102、FT232 可能需要安装对应驱动。

当前开发机验证环境：

```text
Python 3.14.6
PySide6 6.11.1
pyqtgraph 0.14.0
pyserial 3.5
pytest 9.1.1
```

## 安装依赖

在项目根目录执行：

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
```

## 启动模拟模式

没有下位机时，先用模拟模式验证界面、曲线和 CSV 录制：

```text
双击 Start-PID-HOST-Demo-Hidden.vbs
```

或在命令行执行：

```powershell
pid-host --demo
```

如果没有安装 editable 包，也可以这样运行：

```powershell
$env:PYTHONPATH='src'
python -m pid_host --demo
```

## 连接真实下位机

桌面上的 `PID-HOST` 快捷方式会通过 `Start-PID-HOST-Hidden.vbs` 启动真实串口模式，不显示终端窗口。图标文件来自 `assets/pid-host.ico`。

双击 `Start-PID-HOST-Hidden.vbs` 可启动真实串口模式；如果需要看启动日志，再双击 `Start-PID-HOST.bat`。

默认串口参数：

- `115200`
- `8N1`
- 无硬件流控
- 无软件流控
- JSON Lines，发送 `\n`，接收兼容 `\n` 和 `\r\n`

操作流程：

1. 插入 USB 转串口设备。
2. 点击“刷新串口”。
3. 选择端口和波特率。
4. 点击“连接”。
5. 上位机会先发送 `hello`，握手成功后启用 `stream`。
6. 输入 `Kp/Ki/Kd/SP` 后发送参数或目标值。

下位机协议实现见 [protocol-for-mcu.md](protocol-for-mcu.md)。

## 运行测试

```powershell
python -m pytest
```

当前测试覆盖：

- JSON Lines 编码、解码、错误处理。
- 单待确认命令模型和超时。
- 遥测滚动缓存。
- CSV 录制。
- 配置保存/加载。
- 模拟数据生成。
- CLI 版本输出和主窗口 offscreen 构造。

## 常见问题

串口列表为空：

- 检查 USB 转串口驱动。
- 检查设备管理器里是否出现 COM 端口。
- 重新插拔后点击“刷新串口”。

串口打不开：

- 确认没有串口助手或其他程序占用该端口。
- 确认选择的 COM 口仍然存在。

曲线不动：

- 先用 `pid-host --demo` 验证界面。
- 真实设备模式下检查下位机是否返回 `tel` 消息。
- 勾选“显示原始帧”查看收发内容。
