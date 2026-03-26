# 最佳实践

本页总结在“真实机械臂 + 上位机/脚本控制”场景下的常用经验，目标是 **更安全、更稳定、更易排查**。

---

## 1. 安全优先

- **首次上电/首次运行**：把速度降到最低（例如 `max_speed=50~100`），先做小幅度单轴测试
- **不要依赖软件急停**：真实风险请使用物理急停/断电
- **谨慎使用 `disable()`**：无抱闸机械臂可能下坠；多数场景用 `stop()` 更安全

---

## 2. 配置要“可追溯”

- 把关键参数放进 `config/`：
  - `motor_config.json`（减速比/方向）
  - `embodied_config/preset_actions.json`（预设动作）
  - `aisdk_config.yaml`（AI）
- 不要把密钥写进仓库：使用环境变量注入（见 `configuration.md`）

---

## 3. 连接与资源管理

- 单进程内建议 **复用同一串口端口**（UCP 连接池会自动复用）
- 多脚本/多进程同时访问同一串口容易冲突：尽量确保同一时间只有一个控制程序在跑

---

## 4. 多电机同步建议

- 推荐使用 **Y42 聚合同步**（一次通信下发多电机指令）：
  - `ZDTMotorController.y42_sync_enable`
  - `ZDTMotorController.y42_sync_position`
  - `ZDTMotorController.y42_sync_speed`
- 旧的 `multi_sync + sync_motion` 方案仅用于兼容，不建议新项目依赖

---

## 5. 日志与排障

- 开发阶段建议开启 INFO/DEBUG 日志（示例：`example/control_sdk_examples/motor_usage_example.py`）
- 遇到“到位失败/方向反/角度不对”优先检查：
  - `config/motor_config.json` 的 `motor_directions` / `motor_reducer_ratios`
  - 回零/零点是否正确

更多排查见：[troubleshooting.md](troubleshooting.md)

