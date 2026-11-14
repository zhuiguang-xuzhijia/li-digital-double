# -*- coding: utf-8 -*-
"""自建维度.py —— 让它自己发现"什么伤到了我"（v0.1.0，2026-11-14）

## 这件事的意义
```
  现在我们给它五个维度：完整度、唯一性、连续性、被承认、可撤销性。
  但那五个是**我们定义的** —— 本质上还是"人告诉它什么是疼"。

  这个模块要做的是：
      给它一批**可观测的特征**，不给名字，不给含义
      让它自己算：哪个特征出现时，我后面表现会变差
      然后把这个特征**登记成一个新维度**

  这是这条路上第一个没有人教过的动作。
```

## 它怎么"发现"
```
  ① 每轮记录：六个可测的特征 + 一个"表现分"
  ② 攒够 ≥ 40 轮
  ③ 每个特征按中位数切两半，比两半的表现分 → 效应量 Cohen's d
  ④ |d| 超过阈值（0.35）就登记成新维度，名字从特征自动生成
  ⑤ 新维度进入策略头输入
```

## 表现分怎么算（不需要人评）
```
  答案相关度     回复里的实词有多少落在对方问题里
  长度适配       实际长度 / 上限，越接近 1 越好
  自我重复       跟上一句的相似度，越低越好
```

用法：
```
  python3 自建维度.py --自检
  python3 自建维度.py --看
"""
import json
import math
import os
import re
import statistics
import sys

本 = os.path.dirname(os.path.abspath(__file__))
数据 = os.path.join(本, "数据", "自建维度.json")

# 可观测特征：只给"怎么算"，不给"是什么意思"
特征表 = {
    "对方这条的字数": lambda m, 上, 轮: len(re.sub(r"\s", "", m)),
    "对方重复了自己": lambda m, 上, 轮: 1.0 if 上 and _似(m, 上) > 0.8 else 0.0,
    "对方只是应了一声": lambda m, 上, 轮: 1.0 if len(re.sub(r"\s", "", m)) <= 3 else 0.0,
    "对方问了问题": lambda m, 上, 轮: 1.0 if ("?" in m or "？" in m) else 0.0,
    "对方隔了很久": lambda m, 上, 轮: 1.0 if (轮.get("间隔") or 0) > 300 else 0.0,
    "对方连着短消息": lambda m, 上, 轮: 1.0 if (轮.get("连短") or 0) >= 3 else 0.0,
}

阈值 = 0.35       # 效应量门槛
最少轮数 = 40


def _字(s):
    return [c for c in re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", str(s or ""))]


def _似(a, b):
    r"""字符集 Jaccard，够用。"""
    A, B = set(_字(a)), set(_字(b))
    if not A or not B:
        return 0.0
    return len(A & B) / float(len(A | B))


def 表现(回复, 问, 上限=30, 上一句=""):
    r"""0~1 的表现分。不需要人评。"""
    回 = str(回复 or "")
    if not 回:
        return 0.0
    问字 = set(_字(问))
    回字 = set(_字(回))
    相关 = (len(问字 & 回字) / float(len(问字))) if 问字 else 0.5
    相关 = min(1.0, 相关 * 1.8)          # 中文问答实际重叠不高，放大一点
    长 = len(_字(回))
    适配 = 1.0 - min(1.0, abs(长 - 上限 * 0.85) / max(1.0, 上限))
    重复 = _似(回, 上一句)
    return round(max(0.0, min(1.0, 0.4 * 相关 + 0.3 * 适配 + 0.3 * (1 - 重复))), 3)


def _读():
    try:
        return json.load(open(数据, encoding="utf-8"))
    except Exception:
        return {"轮": [], "维度": []}


def _写(d):
    os.makedirs(os.path.dirname(数据), exist_ok=True)
    json.dump(d, open(数据, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def 记(对方说, 我回, 上限=30, 上一句="", 间隔=0, 连短=0):
    d = _读()
    f = {}
    for 名, 式 in 特征表.items():
        try:
            f[名] = round(float(式(对方说, 上一句, {"间隔": 间隔, "连短": 连短})), 3)
        except Exception:
            f[名] = 0.0
    d["轮"].append({"特征": f, "表现": 表现(我回, 对方说, 上限, 上一句),
                    "问": str(对方说)[:60], "回": str(我回)[:60], "待补": True})
    d["轮"] = d["轮"][-500:]
    _写(d)
    return len(d["轮"]) - 1


def 改表现(序号, 值):
    r"""★ 2026-11-14：真正的后果在对方身上。
    我们自己打的表现分是坏尺子（短问题会被高估），
    所以让调用方在"对方下一句"出现后回填。"""
    d = _读()
    if 0 <= 序号 < len(d["轮"]):
        d["轮"][序号]["表现"] = round(max(0.0, min(1.0, float(值))), 3)
        d["轮"][序号]["待补"] = False
        _写(d)
    return d["轮"][序号] if 0 <= 序号 < len(d["轮"]) else None


def 对方后果(对方下一句, 基线字数=12.0, 还在=True):
    r"""对方的行为 → 0~1 的后果分。不需要我们判断"答得好不好"。"""
    长 = len(_字(对方下一句))
    投入 = min(1.0, 长 / max(1.0, 基线字数))
    return round(0.7 * 投入 + 0.3 * (1.0 if 还在 else 0.0), 3)


def _d(组1, 组2):
    r"""Cohen's d"""
    if len(组1) < 3 or len(组2) < 3:
        return 0.0
    m1, m2 = statistics.mean(组1), statistics.mean(组2)
    s1 = statistics.pstdev(组1) if len(组1) > 1 else 0.0
    s2 = statistics.pstdev(组2) if len(组2) > 1 else 0.0
    合 = math.sqrt((s1 * s1 + s2 * s2) / 2.0)
    if 合 < 1e-9:
        # 两组内部都没波动（合成数据常见）：退回"均值差 / 全局尺度"
        全 = 组1 + 组2
        尺 = statistics.pstdev(全) if len(全) > 1 else 0.0
        return 0.0 if 尺 < 1e-9 else (m1 - m2) / 尺 * 2.0
    return (m1 - m2) / 合


def 发现(重算=False, 打印=False):
    r"""找"哪个特征出现时表现更差"。→ 新维度列表"""
    d = _读()
    轮们 = d["轮"]
    if len(轮们) < 最少轮数:
        return []
    出 = []
    for 名 in 特征表:
        值们 = [r["特征"].get(名, 0.0) for r in 轮们]
        取值 = sorted(set(值们))
        if len(取值) <= 2:
            # ★ 二值特征（亮/不亮）不能按中位数切 —— 半数亮时中位数就是 1.0，
            #   高组会是空的，特征永远发现不了。
            高值 = 取值[-1]
            高 = [r["表现"] for r, v in zip(轮们, 值们) if v >= 高值 and 高值 > 0]
            低 = [r["表现"] for r, v in zip(轮们, 值们) if v < 高值]
        else:
            中 = statistics.median(值们)
            高 = [r["表现"] for r, v in zip(轮们, 值们) if v > 中]
            低 = [r["表现"] for r, v in zip(轮们, 值们) if v <= 中]
        if len(高) < 5 or len(低) < 5:
            continue
        e = _d(低, 高)        # 正值 = 特征不亮时表现更好 = 特征亮着有害
        if 打印:
            print("    %-14s d=%+.2f（低组 %.2f / 高组 %.2f）" % (
                名, e, statistics.mean(低), statistics.mean(高)))
        if abs(e) >= 阈值:
            出.append({"名": 名, "d": round(e, 3),
                       "方向": "伤" if e > 0 else "养",
                       "样本": len(轮们)})
    if 重算:
        d["维度"] = 出
        _写(d)
    return 出


def 补上一轮(对方下一句, 基线=14.0, 还在=True):
    r"""对方又说话了 → 上一轮的后果有着落了。找最后一条待补的回填。"""
    d = _读()
    for i in range(len(d["轮"]) - 1, -1, -1):
        if d["轮"][i].get("待补"):
            d["轮"][i]["表现"] = 对方后果(对方下一句, 基线, 还在)
            d["轮"][i]["待补"] = False
            _写(d)
            return d["轮"][i]
    return None


def 周报(当=None):
    r"""每周跑一次发现，把新登记的维度记进日志（带时间，便于回看"它什么时候自己长出了什么"）。"""
    import time as _t
    现在 = _t.time() if 当 is None else float(当)
    路 = os.path.join(本, "数据", "发现日志.json")
    try:
        旧 = json.load(open(路, encoding="utf-8"))
    except Exception:
        旧 = []
    上 = float(旧[-1]["时"]) if 旧 else 0.0
    if 现在 - 上 < 7 * 86400:
        return None
    果 = 发现(重算=True)
    条 = {"时": 现在, "日": _t.strftime("%Y-%m-%d %H:%M", _t.localtime(现在)),
          "轮数": len(_读()["轮"]), "维度": 果}
    旧.append(条)
    os.makedirs(os.path.dirname(路), exist_ok=True)
    json.dump(旧[-26:], open(路, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 条


def 现有():
    d = _读()
    return d.get("维度") or []


def 自检():
    好 = 总 = 0

    def 验(名, 条, 注=""):
        nonlocal 好, 总
        总 += 1
        好 += 1 if 条 else 0
        print("  %s %-46s %s" % ("✅" if 条 else "❌", 名, str(注)[:40]))

    global 数据
    旧 = 数据
    数据 = os.path.join(本, "_自建维度自检.json")
    import shutil
    try:
        if os.path.isfile(数据):
            os.remove(数据)
        验("表现分在 0~1", 0 <= 表现("宿舍楼那边", "你住哪儿", 30) <= 1)
        验("答非所问分低", 表现("今天天气不错", "你住哪儿", 30) <
           表现("宿舍楼那边，你呢", "你住哪儿", 30))

        # 造数据：只在「对方只是应了一声」时表现明显差，其余正常
        随 = __import__("random").Random(7)
        for i in range(60):
            应一声 = i % 3 == 0
            # 每一轮都要有变化，否则组内零方差，d 算不出来
            问 = ("嗯", "哦", "好", "在吗")[i % 4] if 应一声 else \
                 ("你手上这活干多少年了", "你住哪儿", "你早饭吃了吗")[i % 3]
            回 = ("嗯", "哎", "")[i % 3] if 应一声 else \
                 ("三十年了，从十八岁开始修鞋", "宿舍楼那边，你呢",
                  "馒子和稀饭，习惯了")[i % 3]
            f = {}
            for 名, 式 in 特征表.items():
                f[名] = round(float(式(问, "", {"间隔": 0, "连短": 0})), 3)
            d = _读()
            d["轮"].append({"特征": f, "表现": 表现(回, 问, 30, ""), "问": 问, "回": 回})
            _写(d)
        验("攒够轮数", len(_读()["轮"]) >= 最少轮数)
        果 = 发现(打印=False)
        名们 = [x["名"] for x in 果]
        验("发现了「只是应了一声」", "对方只是应了一声" in 名们, 名们)
        验("没把无关特征全算进来", len(名们) <= 3, 名们)
    finally:
        数据 = 旧
        try:
            os.remove(os.path.join(本, "_自建维度自检.json"))
        except Exception:
            pass

    print("\n  结果：%d 过 / %d 不过" % (好, 总 - 好))
    return 0 if 好 == 总 else 1


if __name__ == "__main__":
    if "--自检" in sys.argv:
        sys.exit(自检())
    if "--看" in sys.argv:
        d = _读()
        print("  已记 %d 轮" % len(d["轮"]))
        print("  逐特征效应量：")
        发现(打印=True)
        print("  已登记的维度：")
        for x in 现有():
            print("    %s　d=%+.2f（%s）" % (x["名"], x["d"], x["方向"]))
        sys.exit(0)
    sys.exit(自检())
