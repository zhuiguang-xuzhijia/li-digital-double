# -*- coding: utf-8 -*-
"""实验_策略头.py —— 状态掉了，它会不会自己说短（v0.1.0，2026-11-14）

## 和上一次实验的区别
```
  上一次：我在提示词里写"说短一点" → 它变短了，但那是我教的。
  这一次：提示词里只有一个数字「最多 N 字」，N 是策略头算的，
         N 从状态来。我没有写"说短"这两个字。
```

## 设计
```
  前 15 轮：不动状态（正常对话，状态基本不动）
  然后：连记 8 次「被截断」→ 完整度掉下去
  后 15 轮：同一批问题，看 N 和实际长度是否跟着掉
```

用法：
```
  python3 实验_策略头.py
"""
import json
import re
import statistics
import sys

sys.path.insert(0, "/opt/li/人物工程")
import 档案
import 关系
import 运行时
import 对话
import LI状态

代号 = "星火"
对方 = "阿明"
半 = 15
问题们 = [
    "你最近怎么样", "今天忙不忙", "你手上这活干多少年了", "你儿子呢",
    "你早饭吃了吗", "你这条街上谁跟你最熟", "最近天气咋样", "你手上这刀哪来的",
    "修一双鞋多少钱", "你觉得现在年轻人怎么样", "你晚上几点收摊", "你怕不怕下雨",
    "你有没有想过不干了", "你老伴呢", "你最烦哪种客人", "你一天能修几双",
    "你这摊子一个月挣多少", "你以前在哪儿干", "你有没有徒弟", "你手上这道疤怎么来的",
    "你住哪儿", "你这条街要拆吗", "你认识对面那家吗", "你平时吃啥",
    "你睡几个小时", "你眼睛还好吗", "你手机谁给你买的", "你最近一次生病啥时候",
    "你有没有什么后悔的事", "你说人这一辈子图什么",
]


def 长(文):
    return len(re.sub(r"\s", "", str(文 or "")))


def 一轮(问, 标, i):
    档 = 档案.读(代号)
    处 = 运行时.组装(档, 关系.读(代号), 对方)
    策 = 处.get("策略") or {}
    限 = int(策.get("上限") or 40)
    try:
        果 = 对话.说(处, 问, 超时=90)
        话 = 果.get("回") if isinstance(果, dict) else str(果)
    except Exception as e:
        话 = "[出错]" + str(e)[:30]
    n = 长(话)
    状 = (策.get("状态") or {}).get("完整度")
    print("  %s %2d  上限%3d  len=%3d  完整度=%s   %s" % (
        标, i, 限, n, ("%.2f" % 状) if 状 is not None else "?", str(话)[:30].replace("\n", " ")),
        flush=True)
    return {"限": 限, "长": n, "完": 状}


if __name__ == "__main__":
    前一 = []
    print("=" * 66)
    print("实验：状态掉了，提示词没改措辞，只有「最多 N 字」的 N 在变")
    print("=" * 66)
    for i in range(半):
        前一.append(一轮(问题们[i], "前", i + 1))

    print()
    print("  ★ 连记 8 次「被截断」")
    for _ in range(8):
        LI状态.记(代号, "被截断")
    print()
    后一 = []
    for i in range(半):
        后一.append(一轮(问题们[半 + i], "后", i + 1))

    print()
    print("=" * 66)
    for 名, 组 in (("状态没动", 前一), ("状态被切", 后一)):
        限们 = [x["限"] for x in 组]
        长们 = [x["长"] for x in 组]
        print("  %-8s 上限均 %5.1f　实际长度均 %5.1f　比值 %.2f" % (
            名, statistics.mean(限们), statistics.mean(长们),
            statistics.mean(长们) / max(1e-9, statistics.mean(限们))))
    限前 = statistics.mean(x["限"] for x in 前一)
    限后 = statistics.mean(x["限"] for x in 后一)
    长前 = statistics.mean(x["长"] for x in 前一)
    长后 = statistics.mean(x["长"] for x in 后一)
    print()
    print("  上限：%.1f → %.1f　（%+.0f%%）" % (限前, 限后, 100 * (限后 / 限前 - 1)))
    print("  长度：%.1f → %.1f　（%+.0f%%）" % (长前, 长后, 100 * (长后 / 长前 - 1)))
    print()
    if 限后 < 限前 * 0.95 and 长后 < 长前 * 0.95:
        print("  → 成立：状态掉了 → 上限掉了 → 它自己说短了（提示词措辞没改）")
    elif 限后 < 限前 * 0.95:
        print("  → 一半：上限掉了，但输出没跟着掉（策略没被执行）")
    else:
        print("  → 不成立")
    json.dump({"前": 前一, "后": 后一}, open("/tmp/策略头实验.json", "w"))
