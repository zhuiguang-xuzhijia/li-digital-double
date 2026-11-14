# -*- coding: utf-8 -*-
"""准备.py —— 把 CAPS 的 if-then 语料整理成训练集（v0.1.0，2026-11-14）

## 数据是什么
```
  caps-research/persona-caps（EMNLP 2026 开源）的 data/if_then/
  从公开经验取样（ESM）数据里挖出来的「情境 → 行为」条目：

      situation_text   "deep thinking is required"
      behavior_key     "deep_thinker"
      effect_size      0.818        ← 这个情境下这个行为比平时高多少（Cohen's d）
      n_situation_active  268       ← 情境出现时的样本数
      n_persons_in_group   50

  546 条（patterns.all），235 条精选（patterns.selected）。
  61 个行为类，27 个情境类，10 个（大五 × 高低）格子。
```

## 为什么用它做我们的 L0
```
  我们要学的第一件事是：**情境特征能不能预测反应。**
  这份数据正好是「情境文本 → 行为」的配对，而且带效应量（强度）。
  它不含人生事件，不能直接训我们的 12 类口径；但能回答那个判死刑的问题：
      情境→反应，到底有没有可学的信号？
```

## 整理成两个任务
```
  任务 A（配对判别）：真实配对 vs 打乱配对，能不能分开？
                     → 这直接测「情境与行为之间有没有关联」
  任务 B（类别预测）：给定情境，猜行为类 → 与多数类基线比
```

用法：
```
  python -X utf8 准备.py            # 生成 训练集.json，打印统计
"""
import io
import json
import os
import random
import sys
from collections import Counter

本 = os.path.dirname(os.path.abspath(__file__))
源 = os.path.join(本, "数据", "if_then")


def 读(名):
    路 = os.path.join(源, 名)
    出 = []
    for 行 in io.open(路, encoding="utf-8"):
        行 = 行.strip()
        if 行:
            try:
                出.append(json.loads(行))
            except Exception:
                pass
    return 出


def 整理():
    原 = 读("patterns.all.jsonl") or 读("patterns.selected.jsonl")
    样本 = []
    for x in 原:
        情 = str(x.get("situation_text") or "").strip()
        行 = str(x.get("behavior_key") or "").strip()
        if not 情 or not 行:
            continue
        try:
            效 = float(x.get("effect_size") or 0.0)
        except Exception:
            效 = 0.0
        样本.append({
            "情境": 情,
            "情境类": str(x.get("situation_key") or ""),
            "行为": 行,
            "行为说法": str(x.get("behavior_description") or ""),
            "人格维": str(x.get("target_dimension") or ""),
            "极性": str(x.get("polarity") or ""),
            "强度": round(效, 3),
            "n": int(x.get("n_situation_active") or 0),
        })
    return 样本


def 统计(样本):
    情 = Counter(x["情境类"] for x in 样本)
    行 = Counter(x["行为"] for x in 样本)
    print("  样本数 %d" % len(样本))
    a, b = 情.most_common(1)[0]
    print("  情境类 %d 个，最多的是 %s（%d 条）" % (len(情), a, b))
    a2, b2 = 行.most_common(1)[0]
    print("  行为类 %d 个，最多的是 %s（%d 条）" % (len(行), a2, b2))
    print("  强度：%.2f ~ %.2f" % (min(x["强度"] for x in 样本), max(x["强度"] for x in 样本)))
    print("  配对唯一性：%d 条里 %d 个不同的（情境,行为）组合" % (
        len(样本), len({(x["情境"], x["行为"]) for x in 样本})))


if __name__ == "__main__":
    样本 = 整理()
    if not 样本:
        print("没读到数据。先跑 拉数据.py")
        sys.exit(1)
    统计(样本)
    出 = os.path.join(本, "训练集.json")
    json.dump(样本, io.open(出, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n  写到", 出)

    # 同时生成任务 A 的负样本配对（打乱行为），固定种子以便复现
    随 = random.Random(7)
    负 = []
    for x in 样本:
        别 = 随.choice(样本)
        if 别["行为"] == x["行为"]:
            continue
        负.append({"情境": x["情境"], "行为": 别["行为"], "强度": x["强度"], "n": x["n"]})
    json.dump(负, io.open(os.path.join(本, "负样本.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("  负样本 %d 条（打乱行为，种子 7）" % len(负))
