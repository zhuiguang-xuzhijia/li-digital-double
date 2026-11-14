# -*- coding: utf-8 -*-
"""估半衰期.py —— 从真实 ESM 数据里估「情绪多久回到基线」（v0.1.0，2026-11-14）

## 要回答什么
```
  我们的口径里有个参数：半衰期 τ（事件之后，情绪多久回一半）。
  它是七个旋钮里最重要的一颗 —— 它决定"一个人记不记仇"。

  这个脚本从 803 个真人的 7 天 × 5 次记录里，把这个 τ 估出来。
```

## 数据
```
  0049_pronizius（openESM，CC-BY 4.0）
  28,012 行 / 803 人 / 每人 35 次
  ema_time  一天内的小数小时（11.408 = 11:24）
  stressed  0–100
  social_binary  上次问到现在，有没有发生社交
```

## 方法
```
  ① 事件时点：social_binary 从 0 变 1 的那一拍记为 t0
  ② 取 t0 之后**同一天内**的后续采样（跨夜的不算，隔 16 小时没法归因）
  ③ 基线：这个人所有 stressed 的中位数
  ④ 拟合：S(t) = 基线 + (S₀ − 基线)·2^(−t/τ)
     τ 用网格搜索，最小二乘
  ⑤ 每个人把多段事件的点合在一起估一个 τ
```

## 判据
```
  个体间 τ 的离散  vs  个体内 τ 的离散
  前者明显更大 → "半衰期是个人参数"成立
  两者差不多   → τ 是噪声，旋钮要重写
```

用法：
```
  python -X utf8 估半衰期.py
  python -X utf8 估半衰期.py --自检
"""
import csv
import io
import math
import os
import random
import statistics
import sys

本 = os.path.dirname(os.path.abspath(__file__))
数据路 = os.path.join(本, "数据", "0049_pronizius_ts.tsv")

τ们 = [0.5, 1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 36, 48, 72]


def 数(x):
    try:
        v = float(x)
        return None if (v != v) else v
    except Exception:
        return None


def 读():
    r"""→ {人: [(t, stressed, social), …] 按时间排序}"""
    出 = {}
    for r in csv.DictReader(io.open(数据路, encoding="utf-8"), delimiter="\t"):
        t = 数(r.get("ema_time"))
        s = 数(r.get("stressed"))
        b = 数(r.get("social_binary"))
        if t is None or s is None:
            continue
        出.setdefault(r["id"], []).append((t, s, b, r.get("day")))
    for k in 出:
        出[k].sort(key=lambda x: (str(x[3]), x[0]))
    return 出


def 段(序列, 打乱=False, 随机=None):
    r"""找出事件时点，取之后同一天的点。→ [(基线, [(dt, 值), …]), …]"""
    vals = [s for _, s, _, _ in 序列]
    if len(vals) < 6:
        return []
    基 = statistics.median(vals)
    时点们 = [i for i in range(1, len(序列))
              if 序列[i][2] is not None and 序列[i][2] > 0.5
              and (序列[i - 1][2] is None or 序列[i - 1][2] <= 0.5)]
    if 打乱 and 随机 and 时点们:
        时点们 = sorted(随机.sample(range(1, len(序列)), min(len(时点们), len(序列) - 1)))
    出 = []
    for i in 时点们:
        t0, s0, _, 天0 = 序列[i]
        点 = [(t0, s0)]
        for j in range(i + 1, min(i + 5, len(序列))):
            t, s, _, 天 = 序列[j]
            if str(天) != str(天0):
                break
            dt = t - t0
            if dt <= 0.05:
                continue
            点.append((t, s))
        后 = [(max(0.0, t - t0), s) for (t, s) in 点[1:]]
        if len(后) >= 1:
            出.append((基, s0, 后))
    return 出


def 拟合(段们, 网格=None):
    r"""网格搜 τ，最小二乘。→ (τ, 误差)"""
    网格 = 网格 or τ们
    if not 段们:
        return None, None
    最好, 最好错 = None, 1e18
    for τ in 网格:
        if τ <= 0:
            continue
        错 = 0.0
        数点 = 0
        for 基, s0, 后 in 段们:
            for dt, s in 后:
                预 = 基 + (s0 - 基) * math.pow(2.0, -dt / τ)
                错 += (预 - s) ** 2
                数点 += 1
        if 数点:
            错 /= 数点
            if 错 < 最好错:
                最好, 最好错 = τ, 错
    return 最好, 最好错


def 跑(打乱=False, 种子=7):
    数据 = 读()
    随 = random.Random(种子)
    每人 = {}          # 人 → τ（合并本人所有段）
    每人段 = {}        # 人 → [段1, 段2…] 用来算个体内离散
    for pid, 序列 in 数据.items():
        段们 = 段(序列, 打乱=打乱, 随机=随)
        if not 段们:
            continue
        τ, 错 = 拟合(段们)
        if τ is None:
            continue
        每人[pid] = τ
        每人段[pid] = 段们
    return 每人, 每人段, len(数据)


def 个体内(每人段, τ网格=None):
    r"""同一个人，把每段单独估一次 τ → 个体内离散。"""
    网格 = τ网格 or τ们
    差们 = []
    for pid, 段们 in 每人段.items():
        if len(段们) < 3:
            continue
        单 = []
        for 一段 in 段们:
            t, e = 拟合([一段], 网格)
            if t:
                单.append(t)
        if len(单) >= 2:
            差们.append(statistics.pstdev(单))
        if len(差们) >= 300:
            break
    return 差们


def 主():
    if not os.path.isfile(数据路):
        print("缺数据：", 数据路)
        return 1
    每人, 每人段, 总人 = 跑()
    if not 每人:
        print("没估出任何 τ")
        return 1
    τ们得 = [每人[k] for k in 每人]
    print("=" * 60)
    print("从 %d 个真人里估「情绪半衰期 τ」" % 总人)
    print("=" * 60)
    print("  估出 τ 的人：%d / %d" % (len(每人), 总人))
    print("  τ 中位数 %.1f 小时　四分位 %.1f ~ %.1f　范围 %.1f ~ %.1f" % (
        statistics.median(τ们得),
        statistics.quantiles(τ们得, n=4)[0], statistics.quantiles(τ们得, n=4)[2],
        min(τ们得), max(τ们得)))
    人τ = statistics.pstdev(τ们得)
    print("  个体间离散（人的 τ 的标准差）　%.2f 小时" % 人τ)

    内 = 个体内(每人段)
    if 内:
        print("  个体内离散（同一人不同段的 τ 标准差）中位数 %.2f 小时" % statistics.median(内))
        print()
        if 人τ > statistics.median(内):
            print("  → 个体间 > 个体内：**半衰期确实是个人参数**")
        else:
            print("  → 个体间 ≤ 个体内：τ 更像噪声，旋钮要重写")

    # 置换对照：把事件时点打乱，重估
    print()
    print("  置换对照（打乱事件时点，重估）")
    for 种 in (1, 2):
        每假, _, _ = 跑(打乱=True, 种子=种)
        假 = [每假[k] for k in 每假]
        if 假:
            print("    第 %d 次　人数 %d　τ 中位数 %.1f　离散 %.2f" % (
                种, len(假), statistics.median(假), statistics.pstdev(假)))
    return 0


def 自检():
    好 = 总 = 0

    def 验(名, 条, 注=""):
        nonlocal 好, 总
        总 += 1
        好 += 1 if 条 else 0
        print("  %s %-42s %s" % ("✅" if 条 else "❌", 名, str(注)[:40]))

    验("数据文件在", os.path.isfile(数据路))
    验("数() 认 NA", 数("NA") is None)
    验("数() 认小数", 数("11.4") == 11.4)

    # 造一条已知 τ=6 的假序列：先是基线 20，事件那拍冲到 80，然后往回掉
    # 真实数据里大部分拍是没事的，基线得占多数，中位数才代表基线
    假 = [(6.0 + i, 20.0, 0, "1") for i in range(10)]
    假.append((16.0, 80.0, 1, "1"))
    for dt in (1, 2, 4, 6):
        假.append((16.0 + dt, 20 + (80 - 20) * math.pow(2.0, -dt / 6.0), 0, "1"))
    段们 = 段(假)
    验("能切出段", len(段们) >= 1, len(段们))
    t, e = 拟合(段们)
    验("拟合出 τ≈6", t is not None and 4 <= t <= 10, t)

    print("\n  结果：%d 过 / %d 不过" % (好, 总 - 好))
    return 0 if 好 == 总 else 1


if __name__ == "__main__":
    sys.exit(自检() if "--自检" in sys.argv else 主())
