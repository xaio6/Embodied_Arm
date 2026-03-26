#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FK→IK 一致性自检脚本（用于判定“当前 DH/偏转/限位 是否与解析 IK 算法自洽”）

用法：
  python example/debug_ik_consistency.py

说明：
- 该脚本不需要连接真实电机；
- 它会在关节限位内随机采样关节角 q，计算 FK 得到 T；
- 再对 T 做 IK，挑选最接近 q 的解 q2，并比较 FK(T2) 与 T 的误差；
- 若失败率很高/误差很大，通常意味着：这套解析 IK 并不适配当前 Mark 机械臂的几何模型，
  单纯替换 DH 数值无法保证基座/工具模式可用（它们依赖 IK）。
"""

from __future__ import annotations

import os
import sys
import math
import random
from typing import List, Tuple

import numpy as np

# 确保能导入项目模块
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from Embodied_SDK import create_configured_kinematics


def _rotation_error_deg(R1: np.ndarray, R2: np.ndarray) -> float:
    """返回两个旋转矩阵的角度误差（deg）。"""
    try:
        R = R1.T @ R2
        tr = float(np.trace(R))
        # 数值保护
        c = (tr - 1.0) / 2.0
        c = float(np.clip(c, -1.0, 1.0))
        return float(np.rad2deg(math.acos(c)))
    except Exception:
        return float("nan")


def _sample_within(lim: Tuple[float, float], margin: float = 2.0) -> float:
    mn, mx = float(lim[0]), float(lim[1])
    if mx - mn < 2 * margin:
        return float((mn + mx) / 2.0)
    return random.uniform(mn + margin, mx - margin)


def main():
    kin = create_configured_kinematics()
    limits = getattr(kin, "joint_limits", [(-180, 180)] * 6)

    n = 200
    ok = 0
    fail = 0
    pos_errs: List[float] = []
    rot_errs: List[float] = []
    sample_fail_examples: List[str] = []

    for i in range(n):
        q = [_sample_within(limits[j], margin=5.0) for j in range(6)]

        try:
            T = kin.forward_kinematics(q)
        except Exception as e:
            fail += 1
            if len(sample_fail_examples) < 5:
                sample_fail_examples.append(f"[FK失败] q={q} err={e}")
            continue

        try:
            sols = kin.inverse_kinematics(T, return_all=True)
            sel = kin.select_closest_solution(sols, q)
            q2 = sel["normalized"] if isinstance(sel, dict) and "normalized" in sel else sel
            T2 = kin.forward_kinematics(list(map(float, q2)))
        except Exception as e:
            fail += 1
            if len(sample_fail_examples) < 5:
                sample_fail_examples.append(f"[IK失败] q={q} err={e}")
            continue

        try:
            p1 = np.array(T[:3, 3], dtype=float)
            p2 = np.array(T2[:3, 3], dtype=float)
            pos_err = float(np.linalg.norm(p1 - p2))  # mm
            rot_err = _rotation_error_deg(np.array(T[:3, :3], dtype=float), np.array(T2[:3, :3], dtype=float))
        except Exception:
            pos_err = float("nan")
            rot_err = float("nan")

        if not (math.isfinite(pos_err) and math.isfinite(rot_err)):
            fail += 1
            if len(sample_fail_examples) < 5:
                sample_fail_examples.append(f"[误差NaN] q={q} pos_err={pos_err} rot_err={rot_err}")
            continue

        ok += 1
        pos_errs.append(pos_err)
        rot_errs.append(rot_err)

    def _pctl(xs: List[float], p: float) -> float:
        if not xs:
            return float("nan")
        ys = sorted(xs)
        k = int(round((len(ys) - 1) * p))
        return float(ys[max(0, min(len(ys) - 1, k))])

    print("\n=== FK→IK 一致性自检 ===")
    print(f"采样次数: {n}")
    print(f"成功: {ok}")
    print(f"失败: {fail}")
    if ok > 0:
        print(f"位置误差(mm): mean={np.mean(pos_errs):.3f}  p95={_pctl(pos_errs, 0.95):.3f}  max={max(pos_errs):.3f}")
        print(f"姿态误差(deg): mean={np.mean(rot_errs):.3f}  p95={_pctl(rot_errs, 0.95):.3f}  max={max(rot_errs):.3f}")

    if sample_fail_examples:
        print("\n失败样例(最多5条):")
        for s in sample_fail_examples:
            print(" -", s)

    print("\n判读建议：")
    print("- 若失败率接近 0 且误差很小：DH/偏转 与当前解析IK自洽，示教器问题多半是轨迹参数/限位/控制逻辑。")
    print("- 若失败率很高 或误差很大：说明“仅换 DH 数值”不足以支持 Mark；需要改 IK 算法或校正几何/零位定义。")


if __name__ == "__main__":
    random.seed(0)
    np.random.seed(0)
    main()

