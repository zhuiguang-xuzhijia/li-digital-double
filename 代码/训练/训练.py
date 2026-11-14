# -*- coding: utf-8 -*-
"""训练.py —— 在真实 if-then 语料上训练「情境→行为」的配对评分（v0.1.0，2026-11-14）

## 要回答的那个判死刑的问题
```
  情境特征到底能不能预测反应？
  如果能，L0（共享层）就有信号，整条路成立；
  如果配对判别和瞎猜差不多，那就说明"情境"这个输入里没有可用信息。
```

## 模型（零依赖，手写梯度）
```
  情境 s  →  词袋哈希  →  x ∈ R^d
  行为 b  →  可学习向量  →  e_b ∈ R^d
  分数     f(s,b) = x · e_b + 偏置_b

  训练：真实配对当正样本，打乱行为当负样本，逻辑损失
        L = −[ y·log σ(f) + (1−y)·log(1−σ(f)) ]
        ∂L/∂e_b = −(y − σ(f)) · x
        ∂L/∂x   = −(y − σ(f)) · e_b        （x 不改，只用来算梯度）
  评测：AUC（真实配对分数 > 负样本的概率）+ hit@1（最高分是不是真行为）
```

## 三个对照
```
  随机      —— 随便挑一个行为
  多数类    —— 永远猜"worries"（训练集里最多的行为）
  本模型    —— 学出来的
```

用法：
```
  python -X utf8 训练.py            # 训练 + 评测
  python -X utf8 训练.py --自检
"""
import io
import json
import math
import os
import random
import sys
from collections import Counter

本 = os.path.dirname(os.path.abspath(__file__))
D = 64          # 特征维度
EPOCHS = 40
LR = 0.15


def 洗(文):
    出 = []
    for w in str(文 or "").lower().replace(",", " ").replace(".", " ").split():
        w = "".join(ch for ch in w if ch.isalpha())
        if len(w) >= 2:
            出.append(w)
    return 出


def 哈希(词):
    h = 2166136261
    for ch in 词:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h % D


def 向量(文):
    x = [0.0] * D
    for w in 洗(文):
        x[哈希(w)] += 1.0
    n = math.sqrt(sum(v * v for v in x)) or 1.0
    return [v / n for v in x]


def σ(z):
    if z > 30:
        return 1.0
    if z < -30:
        return 0.0
    return 1.0 / (1.0 + math.exp(-z))


def 训练(样本, 负样本, 种子=7, d=D, epochs=EPOCHS, lr=LR, 打印=True):
    随 = random.Random(种子)
    行为们 = sorted({x["行为"] for x in 样本})
    偏 = {b: 0.0 for b in 行为们}
    E = {b: [随.gauss(0, 0.1) for _ in range(d)] for b in 行为们}

    正 = [(x["情境"], x["行为"], 1.0) for x in 样本]
    负 = [(x["情境"], x["行为"], 0.0) for x in 负样本 if x["行为"] in E]
    全 = 正 + 负
    记录 = []
    for 轮 in range(epochs):
        随.shuffle(全)
        损 = 0.0
        for 情, 行, y in 全:
            x = 向量(情)
            e = E[行]
            f = sum(a * b for a, b in zip(x, e)) + 偏[行]
            p = σ(f)
            g = y - p
            损 += -(y * math.log(max(1e-9, p)) + (1 - y) * math.log(max(1e-9, 1 - p)))
            for i in range(d):
                e[i] += lr * g * x[i]
            偏[行] += lr * g * 0.1
        记录.append(损 / max(1, len(全)))
        if 打印 and (轮 % 10 == 0 or 轮 == epochs - 1):
            print("  第 %2d 轮　平均损失 %.4f" % (轮, 记录[-1]))
    return {"E": E, "偏": 偏, "行为们": 行为们, "损失": 记录}


def 打分(模型, 情, 行):
    x = 向量(情)
    return sum(a * b for a, b in zip(x, 模型["E"][行])) + 模型["偏"].get(行, 0.0)


def 评测(模型, 正, 负):
    r"""AUC：真实配对分数高于负样本的比例。"""
    正分 = [打分(模型, x["情境"], x["行为"]) for x in 正]
    负分 = [打分(模型, x["情境"], x["行为"]) for x in 负]
    对 = 0
    总 = 0
    for a in 正分:
        for b in 负分:
            总 += 1
            if a > b:
                对 += 1
            elif a == b:
                对 += 0.5
    auc = 对 / float(总) if 总 else 0.0

    # hit@1：给定情境，全部行为里最高分是不是真行为
    行们 = 模型["行为们"]
    中 = 0
    for x in 正:
        分们 = [(打分(模型, x["情境"], b), b) for b in 行们]
        分们.sort(reverse=True)
        if 分们 and 分们[0][1] == x["行为"]:
            中 += 1
    hit = 中 / float(len(正)) if 正 else 0.0
    return round(auc, 3), round(hit, 3)


def 基线(正, 负):
    r"""随机和多数类的 AUC / hit@1，给个对照。"""
    随 = random.Random(11)
    # 随机打分：AUC 应该 ≈ 0.5
    对 = 总 = 0
    for x in 正:
        for y in 负:
            总 += 1
            if 随.random() > 0.5:
                对 += 1
    auc = 对 / float(总) if 总 else 0.5
    多数 = Counter(x["行为"] for x in 正).most_common(1)[0][0]
    hit = sum(1 for x in 正 if x["行为"] == 多数) / float(len(正))
    return round(auc, 3), round(hit, 3), 多数


def 主(打印=True):
    样本 = json.load(io.open(os.path.join(本, "训练集.json"), encoding="utf-8"))
    负 = json.load(io.open(os.path.join(本, "负样本_训练.json"), encoding="utf-8"))

    # 按（情境,行为）切分：测试集里的配对训练时没见过
    随 = random.Random(3)
    序 = list(range(len(样本)))
    随.shuffle(序)
    切 = int(len(序) * 0.8)
    训 = [样本[i] for i in 序[:切]]
    测 = [样本[i] for i in 序[切:]]

    if 打印:
        print("=" * 58)
        print("真实 if-then 语料上训练「情境→行为」")
        print("  训练 %d 条 / 测试 %d 条 / 行为类 %d 个" % (
            len(训), len(测), len({x["行为"] for x in 样本})))
        print("=" * 58)

    负测 = json.load(io.open(os.path.join(本, "负样本_测试.json"), encoding="utf-8"))
    模型 = 训练(训, 负, 打印=打印)
    auc, hit = 评测(模型, 测, 负测)          # ★ 评测用没训过的负样本
    基auc, 基hit, 多数 = 基线(测, 负测)
    return {"auc": auc, "hit": hit, "基auc": 基auc, "基hit": 基hit,
            "多数": 多数, "模型": 模型}


def 自检():
    好 = 总 = 0

    def 验(名, 条, 注=""):
        nonlocal 好, 总
        总 += 1
        好 += 1 if 条 else 0
        print("  %s %-40s %s" % ("✅" if 条 else "❌", 名, str(注)[:44]))

    验("数据文件在", os.path.isfile(os.path.join(本, "训练集.json")))
    v = 向量("deep thinking is required")
    验("向量是 64 维", len(v) == D, len(v))
    验("向量已归一", abs(math.sqrt(sum(a * a for a in v)) - 1) < 1e-9)
    验("同一句向量相同", 向量("a b c") == 向量("a b c"))
    验("σ(0)=0.5", abs(σ(0) - 0.5) < 1e-9)

    假 = [{"情境": "deep thinking is required", "行为": "deep_thinker"},
          {"情境": "I am alone and lonely", "行为": "worries"},
          {"情境": "a party with friends", "行为": "sociable"}]
    假负 = [{"情境": "deep thinking is required", "行为": "sociable"},
            {"情境": "I am alone and lonely", "行为": "deep_thinker"}]
    模 = 训练(假, 假负, epochs=30, 打印=False)
    验("训练不报错", "E" in 模)
    验("损失下降", 模["损失"][-1] < 模["损失"][0], (模["损失"][0], 模["损失"][-1]))
    a, h = 评测(模, 假, 假负)
    验("小样本上 AUC 尚可", a >= 0.5, a)

    print("\n  结果：%d 过 / %d 不过" % (好, 总 - 好))
    return 0 if 好 == 总 else 1


if __name__ == "__main__":
    if "--自检" in sys.argv:
        sys.exit(自检())
    果 = 主()
    print()
    print("  %-10s %8s %8s" % ("", "AUC", "hit@1"))
    print("  %-10s %8.3f %8.3f" % ("随机", 果["基auc"], 果["基hit"]))
    print("  %-10s %8.3f %8.3f" % ("多数类(" + 果["多数"] + ")", 0.5, 果["基hit"]))
    print("  %-10s %8.3f %8.3f" % ("本模型", 果["auc"], 果["hit"]))
    # ★ 置换对照：把行为随机打乱再训一遍。如果 AUC 还这么高，说明信号是假的
    print()
    print("  置换对照（打乱行为配对，重训 3 次）")
    样本 = json.load(io.open(os.path.join(本, "训练集.json"), encoding="utf-8"))
    负 = json.load(io.open(os.path.join(本, "负样本_训练.json"), encoding="utf-8"))
    负测 = json.load(io.open(os.path.join(本, "负样本_测试.json"), encoding="utf-8"))
    随 = random.Random(3)
    序 = list(range(len(样本)))
    随.shuffle(序)
    切 = int(len(序) * 0.8)
    训 = [样本[i] for i in 序[:切]]
    测 = [样本[i] for i in 序[切:]]
    假AUC = []
    for 轮 in range(3):
        随2 = random.Random(100 + 轮)
        行们 = [x["行为"] for x in 训]
        随2.shuffle(行们)
        训假 = [{"情境": x["情境"], "行为": 行们[i]} for i, x in enumerate(训)]
        模假 = 训练(训假, 负, 打印=False)
        a假, _ = 评测(模假, 测, 负测)
        假AUC.append(a假)
        print("    第 %d 次　AUC %.3f" % (轮 + 1, a假))
    print("    打乱后均值 %.3f　← 应接近 0.5" % (sum(假AUC) / len(假AUC)))
    print()
    print("  判据：AUC 明显 > 0.5 且 hit@1 > 多数类 → 情境里确实有信号")
