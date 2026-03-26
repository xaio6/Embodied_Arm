#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MuJoCo Viewer 滑块控制（底层调试工具）
==================================

用途：
- 直接使用 `mujoco.viewer.launch_passive` 打开查看器窗口；
- 通过 `data.ctrl`（滑块）控制关节角，并把值直接写回 `data.qpos`；
- 适合做“模型/关节映射/显示效果”的底层验证。

注意：
- 这是底层工具脚本，不代表 Embodied_SDK 推荐用法；
- 推荐的 SDK 用法请看：`example/mujoco_control.py`（基于 DigitalTwinSDK）。
"""

from __future__ import annotations

import os
import time
import numpy as np


def main() -> None:
    try:
        import mujoco
        import mujoco.viewer
    except Exception as e:
        print(f"❌ 未能导入 mujoco：{e}")
        print("请先安装：pip install mujoco")
        return

    xml_filename = "config/urdf/mjmodel.xml"
    if not os.path.exists(xml_filename):
        print(f"❌ 错误: 找不到模型文件 '{xml_filename}'。")
        return

    try:
        model = mujoco.MjModel.from_xml_path(xml_filename)
        data = mujoco.MjData(model)
    except Exception as e:
        print(f"❌ 加载 XML 文件时出错: {e}")
        return

    with mujoco.viewer.launch_passive(model, data) as viewer:
        # 初始化滑块，使其与关节初始角度匹配（qpos 为弧度）
        data.ctrl[:] = np.rad2deg(data.qpos[:])

        while viewer.is_running():
            step_start = time.time()

            # ctrl(度) -> qpos(弧度)
            data.qpos[:] = np.deg2rad(data.ctrl)

            # 只用于更新正向运动学（不加控制力）
            mujoco.mj_step(model, data)
            viewer.sync()

            # 控制仿真速度（可选）
            time_until_next_step = model.opt.timestep - (time.time() - step_start)
            if time_until_next_step > 0:
                time.sleep(time_until_next_step)


if __name__ == "__main__":
    main()

