# -*- coding: utf-8 -*-
"""实验_真实语料.py —— 在真实对话上训练检索，与手工权重对比（零依赖）

## 数据
```
  从线上系统导出 23 条真实对话（6 个角色、147 条真实历史），见 数据_示例.json
  每条：{我, 他, 话（我说的）, 回（他说的）, 史（他的历史条目）}
```

## 监督信号从哪来（关键，必须说清）
```
  我们没有"他当时想的是哪段"的人工标注。
  于是用**回话**当弱标签：与被抽中的历史若真影响了回话，回话里应当带上那段历史的词。
  标签 = 与"话 + 回"标签重合最多的那条历史；若所有重合都为 0，这条样本丢弃。
  这显然是有噪声的（回话也可能不引用任何历史），所以结果只能看**相对**差异。
```

## 三个对照
```
  A 随机      —— 从历史里随便挑一条
  B 手工权重  —— 我们现在线上用的：标签重合 × (0.5+需求) × (1+情绪) × (1+皮质醇×威胁)
  C 训练向量  —— 历史嵌入为标签 one-hot（10 维），场景查询同空间，
                 学一个 W，score = (Wq)·k/√d，softmax，交叉熵，SGD 手写反传
  评测：留一角色（leave-one-character-out），在没见过的角色上测 hit@1
```

用法：
```
  python3 实验_真实语料.py            # 跑实验
  python3 实验_真实语料.py --自检
"""
import json
import math
import os
import random
import sys

本 = os.path.dirname(os.path.abspath(__file__))
上 = os.path.dirname(本)
# ★ 把自己的目录也放进去 —— 发布版里 激活.py 跟本脚本同目录，没有 人物工程/
for p in (本, 上, os.path.join(上, "人物工程")):
    if p not in sys.path:
        sys.path.insert(0, p)

数据路 = os.path.join(本, "数据_示例.json")   # ★ 真实数据不可公开，仓库提供同格式示例

try:
    import 激活
except Exception:
    激活 = None

标签类 = list(激活.标签词.keys()) if 激活 else [
    "灾难", "失去", "家人", "他人", "钱", "活路", "病", "面子", "感情", "冲突"]


def 向量(文):
    r"""一句话 → 标签 one-hot（10 维），按出现与否取 1。"""
    t = str(文 or "")
    出 = [0.0] * len(标签类)
    if 激活:
        标 = 激活.标签(t)
        for i, k in enumerate(标签类):
            if k in 标:
                出[i] = 1.0
    return 出


def 余弦(a, b):
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(x * x for x in b)) or 1e-9
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def 打标签(样本):
    r"""弱标签：与"话+回"标签重合最多的那条历史。返回下标或 None。"""
    线索 = 向量(样本["话"]) 
    回应 = 向量(样本["回"])
    合 = [max(a, b) for a, b in zip(线索, 回应)]
    最佳, 最佳分 = None, 0.0
    for i, 文 in enumerate(样本["史"]):
        分 = sum(x * y for x, y in zip(向量(文), 合))
        if 分 > 最佳分:
            最佳, 最佳分 = i, 分
    return 最佳


# ────────────────────────── 手工权重 ──────────────────────────
def 手工排序(样本):
    r"""直接调线上那套：激活.打分。"""
    if not 激活:
        return list(range(len(样本["史"])))
    场 = {"名": "闲时", "标签": set(), "强度": 0.7}
    场们 = 激活.叠(场, 样本["话"], 0.0)
    需求 = {"安全": 0.5, "生存": 0.5, "归属": 0.5, "尊重": 0.5, "掌控": 0.5}
    分们 = []
    for 文 in 样本["史"]:
        段 = 激活.记段(文)
        分们.append(激活.打分(段, 场们, 需求, 0.0, 0.4))
    return sorted(range(len(分们)), key=lambda i: -分们[i])


# ────────────────────────── 训练模型 ──────────────────────────
def 训练模型(样本们, d=None, 轮=60, 学习率=0.5, β=3.0, 种子=7):
    r"""在 10 维标签空间上学一个 W（10×10）。→ W"""
    d = d or len(标签类)
    随机 = random.Random(种子)
    W = [[随机.gauss(0, 0.3) for _ in range(d)] for _ in range(d)]
    有效 = [(s, 打标签(s)) for s in 样本们]
    有效 = [(s, y) for s, y in 有效 if y is not None]
    if not 有效:
        return W

    for _ in range(轮):
        随机.shuffle(有效)
        for s, y in 有效:
            q原始 = 向量(s["话"])
            q = [sum(W[r][c] * q原始[c] for c in range(d)) for r in range(d)]
            K = [向量(m) for m in s["史"]]
            分 = [sum(x * z for x, z in zip(q, k)) / math.sqrt(d) for k in K]
            m = max(分)
            e = [math.exp(β * (x - m)) for x in 分]
            总 = sum(e)
            p = [x / 总 for x in e]
            # dL/dscore
            d分 = [(p[i] - (1.0 if i == y else 0.0)) * β for i in range(len(K))]
            # g = Σ d分_i · k_i / √d
            g = [0.0] * d
            for i, k in enumerate(K):
                if abs(d分[i]) < 1e-12:
                    continue
                for r in range(d):
                    g[r] += d分[i] * k[r] / math.sqrt(d)
            # dW = g ⊗ q原始
            for r in range(d):
                for c in range(d):
                    W[r][c] -= 学习率 * g[r] * q原始[c]
    return W


def 训练排序(W, 样本):
    q原始 = 向量(样本["话"])
    d = len(q原始)
    q = [sum(W[r][c] * q原始[c] for c in range(d)) for r in range(d)]
    分们 = [sum(x * z for x, z in zip(q, 向量(m))) for m in 样本["史"]]
    return sorted(range(len(分们)), key=lambda i: -分们[i])


# ────────────────────────── 评测 ──────────────────────────
def 评测(种子=7):
    样本们 = json.load(open(数据路, encoding="utf-8"))
    有效 = [(s, 打标签(s)) for s in 样本们]
    有标 = [(s, y) for s, y in 有效 if y is not None]
    角色 = sorted({s["他"] for s, _ in 有标})

    随机 = random.Random(种子)
    结 = {"随机": 0, "手工": 0, "训练": 0}
    总 = 0
    for 留 in 角色:
        训 = [s for s, _ in 有标 if s["他"] != 留]
        测 = [(s, y) for s, y in 有标 if s["他"] == 留]
        if not 训 or not 测:
            continue
        W = 训练模型(训)
        for s, y in 测:
            总 += 1
            n = len(s["史"])
            if random.randrange(n) == y:
                结["随机"] += 1
            if 手工排序(s)[0] == y:
                结["手工"] += 1
            if 训练排序(W, s)[0] == y:
                结["训练"] += 1
    return 结, 总, len(有标), len(角色)


def 自检():
    好 = 总 = 0

    def 验(名, 条, 注=""):
        nonlocal 好, 总
        总 += 1
        好 += 1 if 条 else 0
        print("  %s %-40s %s" % ("✅" if 条 else "❌", 名, str(注)[:40]))

    验("有激活模块", 激活 is not None)
    验("标签类有 10 个", len(标签类) == 10, len(标签类))

    v = 向量("九八年发大水，屋子冲塌了")
    验("向量能出", len(v) == len(标签类), len(v))
    验("灾难标签被点亮", v[标签类.index("灾难")] == 1.0 if 激活 else True, v)

    假 = {"我": "a", "他": "b", "话": "外面下雨了",
          "回": "那场水把屋子冲塌了",
          "史": ["九八年发大水，屋子冲塌了", "我儿子结婚那年", "跟人吵架进了派出所"]}
    y = 打标签(假)
    验("弱标签能打出来", y is not None, y)
    验("标签指向水灾那条", y == 0, y)

    W = 训练模型([假], 轮=5)
    验("训练不报错", W is not None and len(W) == len(标签类))
    排 = 训练排序(W, 假)
    验("排序长度对", len(排) == 3, 排)

    print("\n  结果：%d 过 / %d 不过" % (好, 总 - 好))
    return 0 if 好 == 总 else 1


if __name__ == "__main__":
    if "--自检" in sys.argv:
        sys.exit(自检())

    if not os.path.isfile(数据路):
        print("缺数据文件：", 数据路)
        sys.exit(1)

    结, 总, 有标, 角色数 = 评测()
    print("=" * 60)
    print("真实语料上的检索实验（留一角色）")
    print("=" * 60)
    print("  有效样本 %d 条（有监督信号），涉及 %d 个角色，评测 %d 次" % (有标, 角色数, 总))
    print()
    print("  %-8s %6s %8s" % ("方法", "hit@1", "相对随机"))
    基 = max(1, 结["随机"])
    for k in ("随机", "手工", "训练"):
        print("  %-8s %5.0f%% %+7.0f%%" % (
            k, 100.0 * 结[k] / max(1, 总), 100.0 * (结[k] - 结["随机"]) / 基))
    # ★ 置换检验：如果检索是瞎猜，命中次数会怎么分布？
    样本们 = json.load(open(数据路, encoding="utf-8"))
    有标 = [(s, 打标签(s)) for s in 样本们]
    有标 = [(s, y) for s, y in 有标 if y is not None]
    随机 = random.Random(99)
    次数 = 2000
    至少 = {"随机": 0, "手工": 0, "训练": 0}
    for _ in range(次数):
        # 把标签随机打乱，模拟"方法没有用"
        打乱 = [(s, 随机.randrange(len(s["史"]))) for s, _ in 有标]
        for 名, 算 in (("随机", lambda s: 随机.randrange(len(s["史"]))),
                      ("手工", lambda s: 手工排序(s)[0])):
            中 = sum(1 for s, y in 打乱 if 算(s) == y)
            if 中 >= 结[名]:
                至少[名] += 1

    print()
    print("  置换检验（打乱标签 2000 次）：")
    for k in ("随机", "手工"):
        p值 = 至少[k] / float(次数)
        print("    %-6s 命中 %2d 次，纯靠蒙也有 %.1f%% 的机会做到 → p≈%.2f" % (
            k, 结[k], 100.0 * p值, p值))
    print("    %-6s 命中 %2d 次（训练）—— 与手工只差 %d 条" % ("训练", 结["训练"], 结["训练"] - 结["手工"]))
    print()
    print("  说明：样本极少（%d 条），标签是弱标签（用回话反推），" % len(有标))
    print("        结果只能看相对差异，不足以支持任何泛化结论。")
