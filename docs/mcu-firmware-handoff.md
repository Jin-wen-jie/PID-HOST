# PID-HOST 下位机固件对接说明

下面这段可以直接发给负责下位机/单片机项目的对话或开发者。

---

我这边已经有一个 Windows 桌面 PID 上位机，名字是 `PID-HOST`。现在需要你帮我写下位机固件，让单片机通过 UART 和上位机通信，实现两个电机的独立 PID 控制。

## 目标

请写一个下位机程序，完成：

- 通过串口接收上位机发来的 JSON Lines 命令。
- 支持两个电机 PID 通道：
  - `ch=0`：电机1
  - `ch=1`：电机2
- 每个电机独立保存 `Kp / Ki / Kd / SP`。
- 下位机本地运行 PID 闭环，上位机只负责调参、显示曲线和记录数据。
- 周期性向上位机回传 `SP / PV / OUT`，用于实时曲线显示。

## 串口参数

默认串口参数：

```text
baudrate: 115200
data bits: 8
parity: none
stop bits: 1
flow control: none
encoding: UTF-8
```

每条消息是一行 JSON，必须以 `\n` 结尾。接收时兼容 `\n` 和 `\r\n`。

## 必须实现的消息

### 1. hello

上位机发送：

```json
{"type":"hello","seq":1}
```

下位机必须回复：

```json
{"type":"hello","seq":1,"device":"pid-mcu","fw":"1.0.0","proto":1}
```

`seq` 必须原样带回。

### 2. set_pid

上位机发送：

```json
{"type":"set_pid","seq":2,"ch":0,"kp":1.2,"ki":0.05,"kd":0.01}
```

下位机要做：

- 检查 `ch` 是否为 `0` 或 `1`。
- 检查 `kp / ki / kd` 是否为有限数字。
- 保存到对应电机的 PID 参数。
- 成功后回复：

```json
{"type":"ack","seq":2}
```

如果参数非法，回复：

```json
{"type":"err","seq":2,"code":"bad_value","message":"invalid pid"}
```

### 3. set_sp

上位机发送：

```json
{"type":"set_sp","seq":3,"ch":1,"sp":80.0}
```

下位机要做：

- 检查 `ch` 是否为 `0` 或 `1`。
- 检查 `sp` 是否为有限数字，并按实际设备限制做范围检查。
- 保存到对应电机的目标值。
- 成功后回复：

```json
{"type":"ack","seq":3}
```

### 4. stream

上位机发送：

```json
{"type":"stream","seq":4,"enabled":true,"rate_hz":20}
```

下位机要做：

- `enabled=true`：开始周期发送遥测。
- `enabled=false`：停止发送遥测。
- `rate_hz` 支持 `10` 到 `20`。
- 成功后回复：

```json
{"type":"ack","seq":4}
```

## 遥测回传 tel

下位机开启 stream 后，按 `10-20Hz` 回传两个电机的数据。

示例：

```json
{"type":"tel","ch":0,"t":123456,"sp":50.0,"pv":48.7,"out":32.1}
{"type":"tel","ch":1,"t":123456,"sp":80.0,"pv":78.2,"out":41.5}
```

字段说明：

- `ch`：电机通道，`0` 或 `1`。
- `t`：下位机毫秒时间戳，建议使用上电后的毫秒数，单调递增。
- `sp`：目标值。
- `pv`：反馈值，比如编码器速度、编码器位置或传感器反馈值。
- `out`：PID 输出，比如 PWM 占空比、电流指令或速度指令。

## 推荐代码结构

建议下位机程序按这个结构写：

```c
typedef struct {
    float kp;
    float ki;
    float kd;
    float sp;
    float pv;
    float out;
    float integral;
    float last_error;
} MotorPid;

MotorPid motor[2] = {
    {.kp = 1.0f, .ki = 0.0f, .kd = 0.0f, .sp = 0.0f},
    {.kp = 1.0f, .ki = 0.0f, .kd = 0.0f, .sp = 0.0f},
};
```

主循环建议：

```c
while (1) {
    read_uart_line_and_handle_json();
    update_motor_feedback();
    run_pid_loop_fixed_period();
    send_telemetry_if_needed();
}
```

PID 计算示例：

```c
void pid_update(int ch, float dt) {
    MotorPid *m = &motor[ch];

    float error = m->sp - m->pv;
    m->integral += error * dt;

    float derivative = 0.0f;
    if (dt > 0.0f) {
        derivative = (error - m->last_error) / dt;
    }

    m->out = m->kp * error + m->ki * m->integral + m->kd * derivative;

    if (m->out > 100.0f) {
        m->out = 100.0f;
    }
    if (m->out < -100.0f) {
        m->out = -100.0f;
    }

    m->last_error = error;

    set_motor_output(ch, m->out);
}
```

注意：`pv` 必须来自真实反馈，比如编码器测速/位置。不要用假数据代替，除非是在做调试桩。

## JSON 处理建议

如果是 Arduino/ESP32，可以用 `ArduinoJson`。

如果是 STM32：

- 可以用 `cJSON`。
- 或者先实现轻量解析，只解析 `type / seq / ch / kp / ki / kd / sp / enabled / rate_hz` 这些字段。

必须做到：

- 每次收到完整一行再解析。
- JSON 解析失败时回复 `err`：

```json
{"type":"err","code":"bad_json","message":"invalid json"}
```

- 未知命令回复：

```json
{"type":"err","seq":5,"code":"bad_type","message":"unknown type"}
```

## 上位机超时规则

上位机发出命令后，会等待同一个 `seq` 的 `ack` 或 `err`。

如果 1 秒内没有收到，界面会显示“命令超时”。

所以这些命令必须及时回复：

- `hello`
- `set_pid`
- `set_sp`
- `stream`

`tel` 遥测不需要 `seq`，也不需要 `ack`。

## 联调验收清单

请按下面顺序验证：

1. 串口参数为 `115200 8N1`。
2. 上位机连接后发送 `hello`，下位机能返回 `hello`。
3. 上位机发送 `set_pid ch=0`，下位机返回同 `seq` 的 `ack`。
4. 上位机发送 `set_pid ch=1`，下位机返回同 `seq` 的 `ack`。
5. 上位机发送 `set_sp ch=0`，电机1目标值改变。
6. 上位机发送 `set_sp ch=1`，电机2目标值改变。
7. 上位机发送 `stream enabled=true` 后，下位机开始回传 `tel`。
8. 两个电机都能回传：

```json
{"type":"tel","ch":0,"t":...,"sp":...,"pv":...,"out":...}
{"type":"tel","ch":1,"t":...,"sp":...,"pv":...,"out":...}
```

9. `t` 单调递增。
10. `pv` 是真实反馈值。
11. `out` 是实际控制输出。
12. 非法 `ch=2` 或非法参数时返回 `err`。

## 需要你根据硬件补充的部分

请根据实际下位机项目补齐：

- 使用的芯片型号。
- 使用哪个 UART。
- 电机驱动方式，比如 PWM、方向引脚、H 桥、FOC 驱动器等。
- 编码器或传感器读取方式。
- `pv` 的单位：速度、位置、角度还是其他量。
- `sp` 的单位：目标速度、目标位置还是目标角度。
- PID 控制周期，比如 `1ms`、`5ms` 或 `10ms`。
- 输出限幅范围，比如 `-100~100`、`0~100` 或 PWM 计数值。

上位机当前只要求协议字段正确，不强制具体单位；但同一个通道的 `SP / PV / OUT` 必须单位自洽。
