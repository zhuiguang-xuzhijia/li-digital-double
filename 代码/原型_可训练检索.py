# -*- coding: utf-8 -*-
"""原型_可训练检索.py —— 场景—历史叠加作为可微检索（零依赖，手写反传）

## 这个文件要证明什么
```
  论文《场景—历史叠加的可概率化》主张：叠加 = 带温度的概率检索 = 注意力，
  因此**可微、可训练**。但论文里只有主张，没有训练。

  这里给出最小反例的最小正例：
    场景 s  →  查询 q = W·s
    历史 m_i →  键 k_i（固定嵌入）
    分数     =  q·k_i / √d
    概率     =  softmax(β · 分数)
    损失     =  交叉熵（正确的那段记忆该被想起）
    反向传播 =  手写（不依赖 numpy / torch）

  跑完你会看到：loss 从 ln(N) 掉到接近 0，准确率从 1/N 升到 ~100%。
```

## 为什么不用 PyTorch
```
  ① 这个模型只有一层投影 + 一个 softmax，梯度能手推；
  ② 零依赖意味着任何人 clone 下来就能跑，论文里的数字因此可复现；
  ③ 依赖越少，越不容易把"训练"和"环境问题"混为一谈。
```

用法：
```
  python3 原型_可训练检索.py            # 训练并打印曲线
  python3 原型_可训练检索.py --自检      # 只跑断言
"""
import math
import random
import sys

# ────────────────────────── 配置 ──────────────────────────
D = 16          # 向量维度
N = 8           # 记忆条数
K = 5           # 场景种数（每个场景对应一条正确记忆）
步数 = 400
学习率 = 0.35


# ────────────────────────── 极小向量库 ──────────────────────────
def 单位(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def 随机向量(随机, d=D):
    return 单位([随机.gauss(0, 1) for _ in range(d)])


def 点(a, b):
    return sum(x * y for x, y in zip(a, b))


def softmax(分, β=1.0):
    m = max(分)
    e = [math.exp(β * (x - m)) for x in 分]
    s = sum(e)
    return [x / s for x in e]


# ────────────────────────── 数据 ──────────────────────────
def 造数据(种子=7):
    r"""每个场景与它对应的那条记忆共享一个隐藏因子 —— 所以"该想起哪段"是有解的。"""
    随机 = random.Random(种子)
    记忆 = [随机向量(随机) for _ in range(N)]
    # 场景 = 对应记忆 + 噪声，再归一化（相似但不相同）
    场景们 = []
    for i in range(K):
        底 = 记忆[i]
        噪 = [x + 随机.gauss(0, 0.55) for x in 底]
        场景们.append(单位(噪))
    正确 = list(range(K))          # 第 i 个场景 → 第 i 条记忆
    return 记忆, 场景们, 正确


# ────────────────────────── 模型 ──────────────────────────
def 初始化W(随机):
    return [[随机.gauss(0, 0.3) for _ in range(D)] for _ in range(D)]


def 乘W(W, s):
    return [sum(W[r][c] * s[c] for c in range(D)) for r in range(D)]


def 前向(W, s, 记忆, β):
    q = 乘W(W, s)
    分 = [点(q, m) / math.sqrt(D) for m in 记忆]
    p = softmax(分, β)
    return q, 分, p


def 一次梯度(W, s, 记忆, 正确条, β):
    r"""交叉熵对 W 的梯度。手推：
        p = softmax(β·q·k/√d)
        dL/dscore_i = p_i − 1[i == 正确]
        由 score_i = (W s)·k_i / √d 得
        dL/dW = (Σ_i dscore_i · k_i) ⊗ s / √d
    """
    q, 分, p = 前向(W, s, 记忆, β)
    损失 = -math.log(max(1e-12, p[正确条]))

    # dL/dscore（注意 β 与 1/√d 的链式）
    d分 = [(p[i] - (1.0 if i == 正确条 else 0.0)) * β for i in range(len(记忆))]

    # g = Σ_i d分_i · k_i   （d 维）
    g = [0.0] * D
    for i, m in enumerate(记忆):
        if abs(d分[i]) < 1e-12:
            continue
        for r in range(D):
            g[r] += d分[i] * m[r]

    # dL/dW = g ⊗ s / √d
    s勾 = 1.0 / math.sqrt(D)
    dW = [[g[r] * s[c] * s勾 for c in range(D)] for r in range(D)]
    return 损失, dW, p


def 训练(记忆, 场景们, 正确, 步数=步数, 学习率=学习率, β=2.5, 种子=11, 打印=True):
    随机 = random.Random(种子)
    W = 初始化W(随机)
    记录 = []
    顺序 = list(range(len(场景们)))
    for 步 in range(步数):
        if 步 % len(顺序) == 0:
            随机.shuffle(顺序)
        i = 顺序[步 % len(顺序)]
        损失, dW, p = 一次梯度(W, 场景们[i], 记忆, 正确[i], β)
        for r in range(D):
            for c in range(D):
                W[r][c] -= 学习率 * dW[r][c]
        记录.append(损失)
        if 打印 and (步 % 40 == 0 or 步 == 步数 - 1):
            print("  第 %3d 步   损失 %.4f   猜中的概率 %.3f" % (步, 损失, p[正确[i]]))
    return W, 记录


def 准确率(W, 场景们, 记忆, 正确, β=2.5):
    对 = 0
    for i, s in enumerate(场景们):
        _, _, p = 前向(W, s, 记忆, β)
        if max(range(len(记忆)), key=lambda j: p[j]) == 正确[i]:
            对 += 1
    return 对 / float(len(场景们))


def 采样(随机, p, k=2):
    r"""按概率无放回抽 k 条 —— 这就是论文里"这次想起这一两段"。"""
    池, 出 = list(range(len(p))), []
    for _ in range(min(k, len(p))):
        总 = sum(p[i] for i in 池)
        针 = 随机.random() * 总
        累 = 0.0
        for j, i in enumerate(池):
            累 += p[i]
            if 针 <= 累:
                出.append(i)
                池.pop(j)
                break
    return 出


# ────────────────────────── 自检 ──────────────────────────
def 自检():
    好 = 总 = 0

    def 验(名, 条, 注=""):
        nonlocal 好, 总
        总 += 1
        好 += 1 if 条 else 0
        print("  %s %-40s %s" % ("✅" if 条 else "❌", 名, str(注)[:40]))

    记忆, 场景们, 正确 = 造数据()
    验("数据造出来了", len(记忆) == N and len(场景们) == K)
    验("场景是单位向量", abs(math.sqrt(点(场景们[0], 场景们[0])) - 1) < 1e-9)

    p = softmax([0.0] * 4)
    验("softmax 归一", abs(sum(p) - 1) < 1e-12, sum(p))
    验("softmax 均匀", all(abs(x - 0.25) < 1e-12 for x in p), p[:2])

    随机 = random.Random(3)
    抽 = 采样(随机, [0.5, 0.3, 0.15, 0.05], k=2)
    验("抽样不重复", len(set(抽)) == len(抽), 抽)
    验("抽样条数对", len(抽) == 2, 抽)

    随机2 = random.Random(5)
    W = 初始化W(随机2)
    前 = 准确率(W, 场景们, 记忆, 正确, β=2.5)
    W2, 记录 = 训练(记忆, 场景们, 正确, 步数=300, 打印=False)
    后 = 准确率(W2, 场景们, 记忆, 正确, β=2.5)
    验("训练让准确率上升", 后 > 前, (前, 后))
    验("训练后能全对", 后 >= 0.99, 后)
    验("损失下降", 记录[-1] < 记录[0] * 0.2, (记录[0], 记录[-1]))
    验("损失单调趋势向下", sum(记录[-50:]) / 50 < sum(记录[:50]) / 50)

    # 温度：β 大 → 更确定；β 小 → 更随机
    _, _, p高 = 前向(W2, 场景们[0], 记忆, 8.0)
    _, _, p低 = 前向(W2, 场景们[0], 记忆, 0.3)
    熵 = lambda q: -sum(x * math.log(max(1e-12, x)) for x in q)
    验("β 大 → 分布更尖", max(p高) > max(p低), (max(p高), max(p低)))
    验("β 小 → 熵更大", 熵(p低) > 熵(p高), (round(熵(p低), 2), round(熵(p高), 2)))

    print("\n  结果：%d 过 / %d 不过" % (好, 总 - 好))
    return 0 if 好 == 总 else 1


# ────────────────────────── 主程序 ──────────────────────────
if __name__ == "__main__":
    if "--自检" in sys.argv:
        sys.exit(自检())

    记忆, 场景们, 正确 = 造数据()
    随机 = random.Random(5)
    W0 = 初始化W(随机)

    print("=" * 64)
    print("场景—历史叠加 = 一层投影 + 一个 softmax；下面手写反传训练它")
    print("  d=%d  记忆=%d 条  场景=%d 种  步数=%d" % (D, N, K, 步数))
    print("=" * 64)

    print("\n训练前：准确率 %.0f%%（瞎猜是 %.0f%%）" % (
        准确率(W0, 场景们, 记忆, 正确) * 100, 100.0 / N))
    print()
    W, 记录 = 训练(记忆, 场景们, 正确)
    print()
    print("训练后：准确率 %.0f%%" % (准确率(W, 场景们, 记忆, 正确) * 100))

    print("\n温度 β 的三种行为（同一个查询）：")
    for β, 说法 in ((0.3, "几乎随机——'这次偏偏想起那件事'"),
                    (2.5, "训练后的默认温度"),
                    (8.0, "几乎确定——'每次都想起最相关那段'")):
        _, _, p = 前向(W, 场景们[0], 记忆, β)
        print("  β=%.1f  %-34s 最大概率 %.2f  熵 %.2f" % (
            β, 说法, max(p), -sum(x * math.log(max(1e-12, x)) for x in p)))

    print("\n按概率抽 2 段（模拟对话里'他想起了哪两件事'）：")
    随机3 = random.Random(2026)
    for i in range(5):
        _, _, p = 前向(W, 场景们[0], 记忆, 2.5)
        抽 = 采样(随机3, p, k=2)
        print("  第%d次：%s" % (i + 1, "、".join("记忆%d(%.2f)" % (j, p[j]) for j in 抽)))
