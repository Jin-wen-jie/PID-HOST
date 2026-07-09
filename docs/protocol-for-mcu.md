# PID-HOST 下位机协议手册

版本：v0.1
日期：2026-07-09

本文档面向下位机开发者，说明 PID-HOST 第一版需要 MCU 实现的 UART JSON Lines 协议。

## 物理层

默认串口参数：

- 波特率：`115200`
- 数据位：`8`
- 校验位：`None`
- 停止位：`1`
- 流控：无
- 编码：UTF-8

上位机第一版允许用户修改波特率；其他串口参数固定为默认值。

## 分帧规则

- 每条消息是一行 JSON 文本。
- 发送方必须在每条消息末尾添加 `\n`。
- 接收方应兼容 `\n` 和 `\r\n`。
- 接收方按行解析；解析前去除行尾 `\r` 和 `\n`。
- 空行应忽略。

示例：

```text
{"type":"hello","seq":1}\n
{"type":"tel","ch":0,"t":123456,"sp":50.0,"pv":48.7,"out":32.1}\n
```

## 命令模型

第一版使用逐一应答模型：

- 上位机同一时间只发送一个待确认命令。
- 下位机收到命令后必须返回相同 `seq` 的 `ack` 或 `err`。
- 遥测 `tel` 不需要 `seq`，可以在命令等待期间继续周期发送。
- 上位机默认 `ack_timeout_ms = 1000`。下位机应尽量在 1 秒内响应命令。

## 消息类型

### hello

上位机请求：

```json
{"type":"hello","seq":1}
```

下位机响应：

```json
{"type":"hello","seq":1,"device":"pid-mcu","fw":"1.0.0","proto":1}
```

字段：

- `device`：设备名称。
- `fw`：固件版本。
- `proto`：协议版本，第一版为 `1`。

### set_pid

上位机请求：

```json
{"type":"set_pid","seq":2,"ch":0,"kp":1.2,"ki":0.05,"kd":0.01}
```

下位机成功响应：

```json
{"type":"ack","seq":2}
```

要求：

- 第一版 `ch` 必须为 `0`。
- `kp`、`ki`、`kd` 必须是有限数字。
- 下位机应根据设备能力检查实际上下限。

### set_sp

上位机请求：

```json
{"type":"set_sp","seq":3,"ch":0,"sp":50.0}
```

下位机成功响应：

```json
{"type":"ack","seq":3}
```

要求：

- 第一版 `ch` 必须为 `0`。
- `sp` 必须是有限数字。
- 下位机应根据设备能力检查目标值范围。

### stream

上位机请求：

```json
{"type":"stream","seq":4,"enabled":true,"rate_hz":20}
```

下位机成功响应：

```json
{"type":"ack","seq":4}
```

要求：

- `enabled=true` 时开始周期发送 `tel`。
- `enabled=false` 时停止发送 `tel`。
- 第一版 `rate_hz` 支持 `10` 到 `20`。

### tel

下位机周期上报：

```json
{"type":"tel","ch":0,"t":123456,"sp":50.0,"pv":48.7,"out":32.1}
```

字段：

- `ch`：通道号，第一版固定为 `0`。
- `t`：下位机毫秒时间戳，建议为上电后毫秒数，单调递增。
- `sp`：目标值。
- `pv`：反馈值。
- `out`：控制输出。

### ack

命令成功响应：

```json
{"type":"ack","seq":2}
```

### err

命令失败响应：

```json
{"type":"err","seq":3,"code":"bad_value","message":"sp out of range"}
```

字段：

- `seq`：对应失败命令的序号。若 JSON 无法解析导致无法取得 `seq`，可省略。
- `code`：错误码。
- `message`：面向开发者的简短说明。

## 错误码

| code | 说明 |
| --- | --- |
| `bad_json` | JSON 解析失败 |
| `bad_type` | 未知或不支持的消息类型 |
| `missing_field` | 缺少必填字段 |
| `bad_value` | 字段值非法或超出下位机允许范围 |
| `unsupported` | 功能或协议版本不支持 |
| `busy` | 下位机暂时不能处理该命令 |

## 典型时序

```text
上位机                         下位机
  | ---- hello(seq=1) ----------> |
  | <--- hello(seq=1, info) ----- |
  | ---- set_pid(seq=2) --------> |
  | <--- ack(seq=2) ------------- |
  | ---- set_sp(seq=3) ---------> |
  | <--- ack(seq=3) ------------- |
  | ---- stream(seq=4,on,20Hz) -> |
  | <--- ack(seq=4) ------------- |
  | <--- tel -------------------- |
  | <--- tel -------------------- |
  | <--- tel -------------------- |
```

## C 语言伪代码

```c
while (uart_read_line(line, sizeof(line))) {
    Json msg;
    if (!json_parse(line, &msg)) {
        send_err_without_seq("bad_json", "invalid json");
        continue;
    }

    const char *type = json_get_string(&msg, "type");
    int seq = json_get_int_default(&msg, "seq", -1);

    if (streq(type, "hello")) {
        send_hello(seq);
    } else if (streq(type, "set_pid")) {
        if (!validate_pid(&msg)) {
            send_err(seq, "bad_value", "invalid pid");
        } else {
            apply_pid(&msg);
            send_ack(seq);
        }
    } else if (streq(type, "set_sp")) {
        if (!validate_sp(&msg)) {
            send_err(seq, "bad_value", "invalid sp");
        } else {
            apply_sp(&msg);
            send_ack(seq);
        }
    } else if (streq(type, "stream")) {
        if (!validate_stream(&msg)) {
            send_err(seq, "bad_value", "invalid stream config");
        } else {
            apply_stream(&msg);
            send_ack(seq);
        }
    } else {
        send_err(seq, "bad_type", "unknown type");
    }
}
```

## 联调检查清单

- 串口参数一致：`115200 8N1`，无流控。
- TX/RX 连接正确，设备共地。
- `hello` 能返回设备名、固件版本和协议版本。
- `set_pid` 成功后返回同 `seq` 的 `ack`。
- `set_sp` 成功后返回同 `seq` 的 `ack`。
- `stream enabled=true` 后按 10-20 Hz 返回 `tel`。
- `stream enabled=false` 后停止返回 `tel`。
- 非法参数返回 `err`，错误码在表内。
- `tel.t` 单调递增。
- `tel` 中 `sp/pv/out` 数值合理。
