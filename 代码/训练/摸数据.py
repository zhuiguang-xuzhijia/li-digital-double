# -*- coding: utf-8 -*-
"""摸数据.py —— 在 openESM 的 63 个数据集里，筛出能估「情绪半衰期」的（v0.1.0，2026-11-14）

## 要找什么样的数据集
```
  ① 一天多次测量（n_beeps_per_day ≥ 3）—— 采样点不够，衰减曲线拟合不出来
  ② 有情绪/感受类变量            —— 因变量
  ③ 有事件/压力源/社交互动类变量   —— 自变量（"上次问到现在发生了 X"）
  ④ 时间戳可还原                —— 否则拿不到 Δt
  ⑤ 时间跨度 ≥ 7 天             —— 几天内估不出几小时的半衰期
```

## 为什么要这么做
```
  上一轮在 CAPS 的 if-then 数据上失败了（AUC 0.551 ≈ 置换 0.555）。
  失败原因之一是：那份数据已经丢掉了**时间序列**。
  而估半衰期唯一需要的就是时间序列。

  openESM 是原始的时间序列，所以这一轮先摸清：有几个数据集够格。
```

用法：
```
  python -X utf8 摸数据.py
"""
import io
import json
import os
import re

本 = os.path.dirname(os.path.abspath(__file__))
索引 = os.path.join(本, "数据", "datasets-index.json")

# 情绪/感受类：变量名或构念里出现这些词
情词 = ["affect", "mood", "feeling", "emotion", "sad", "anx", "nervous", "stress",
        "worry", "down", "depress", "happy", "content", "tense", "irritab",
        "negative affect", "positive affect", "valence", "arousal"]
# 事件/压力源/社交类：自变量
事词 = ["event", "hassle", "uplift", "stressor", "stressful", "situation",
        "interaction", "social", "conflict", "argu", "disagree", "support",
        "activity", "trigger", "problem", "demand", "workload"]


def 命中们(变量们, 词表):
    r"""→ 命中的变量名列表"""
    出 = []
    for v in 变量们:
        文 = " ".join(str(v.get(k) or "") for k in ("name", "description", "construct")).lower()
        if any(w in 文 for w in 词表):
            出.append("%s(%s)" % (v.get("name"), str(v.get("construct") or "")[:18]))
    return 出


def 数(x, 键, 默认=0):
    try:
        return float(x.get(键) or 默认)
    except Exception:
        return 默认


def 评估(x):
    变 = x.get("variables") or []
    情 = 命中们(变, 情词)
    事 = 命中们(变, 事词)
    拍 = 数(x, "n_beeps_per_day")
    天 = 数(x, "n_days")
    人 = 数(x, "n_participants")
    时 = 数(x, "n_time_points")
    分 = 0
    if 拍 >= 3:
        分 += 2
    elif 拍 >= 2:
        分 += 1
    if 天 >= 7:
        分 += 2
    elif 天 >= 4:
        分 += 1
    if 情:
        分 += 2
    if 事:
        分 += 2
    if 人 >= 50:
        分 += 1
    return {"id": x.get("id"), "作者": x.get("first_author"), "年": x.get("year"),
            "人": int(人), "天": 天, "拍": 拍, "时点": int(时),
            "情变量": 情, "事变量": 事, "分": 分,
            "许可": str(x.get("license") or "")[:16],
            "话题": ", ".join(x.get("topics") or [])[:40]}


if __name__ == "__main__":
    if not os.path.isfile(索引):
        print("缺索引文件：", 索引)
        raise SystemExit(1)
    全 = json.load(io.open(索引, encoding="utf-8"))
    评 = [评估(x) for x in 全]
    评.sort(key=lambda r: (-r["分"], -r["人"]))

    print("=" * 74)
    print("openESM：%d 个数据集，按「能不能估半衰期」打分（满分 9）" % len(全))
    print("=" * 74)
    print("  %-22s %5s %4s %4s %5s %4s  %s" % ("id", "人", "天", "拍", "情变", "事变", "分"))
    有 = [r for r in 评 if r["分"] >= 6]
    for r in 评[:20]:
        print("  %-22s %5d %4.0f %4.0f %5d %4d  %d" % (
            (r["id"] or "")[:22], r["人"], r["天"], r["拍"],
            len(r["情变量"]), len(r["事变量"]), r["分"]))
    print()
    print("  够格（≥6 分）：%d 个" % len(有))
    print("  同时有情绪变量和事件变量：%d 个" % sum(1 for r in 评 if r["情变量"] and r["事变量"]))
    print()
    if 有:
        print("=== 最够格的几个，看看变量长什么样 ===")
        for r in 有[:3]:
            print("  【%s】%s %s　%d 人　%.0f 天 × %.0f 次/天" % (
                r["id"], r["作者"], r["年"], r["人"], r["天"], r["拍"]))
            print("     情绪变量：", "、".join(r["情变量"][:4]) or "（无）")
            print("     事件变量：", "、".join(r["事变量"][:4]) or "（无）")
            print()
