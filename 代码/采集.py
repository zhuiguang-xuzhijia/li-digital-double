# -*- coding: utf-8 -*-
"""采集.py —— 分场合采集：让用户在不同时段开口，把语域格子填起来（v0.1.0，2026-11-14）

## 为什么要有这个
```
  实测：线上 59 句里 49 句落在「忙 × 生人」这一格，其余 8 格全空。
  于是语言指纹只能是"他对陌生人、在忙的时候"的说话方式 —— 夜里也短，对亲人也客套。

  算法已经改好了（学话 v0.2，分格提炼 + 回退阶梯），但**数据不够**：
  每人 8–11 句，一格 20 句的门槛都到不了。

  所以真正缺的不是算法，是"让人在不同场合说话"。
```

## 怎么做
```
  在四个时段各开一次话头：
      07–09  早上刚起/出门     → 记为「忙」
      11–12  午饭前           → 记为「忙」
      18–20  傍晚收工          → 记为「闲」
      21–23  夜里              → 记为「夜」

  做法：让「他加过的人里的某一个」的分身主动打招呼（走 真人.约招呼）。
  用户看到有人找，回一句 —— 这一句就带着当下的时段标签进了他自己的语料。
```

## 三条不骚扰的硬规矩
```
  ① 每天最多 2 次
  ② 同一个格子每天最多 1 次
  ③ 距上次 ≥ 4 小时
```

用法：
```
  python -X utf8 采集.py --自检
  python -X utf8 采集.py --看     # 看今天的配额和最近触发
"""
import json
import os
import random
import sys
import time

本 = os.path.dirname(os.path.abspath(__file__))
if 本 not in sys.path:
    sys.path.insert(0, 本)

路 = os.path.join(本, "数据", "采集.json")

# 时段 → 场
窗口 = [((7, 9), "忙"), ((11, 13), "忙"), ((18, 20), "闲"), ((21, 24), "夜")]

每天最多 = 2
同格每天最多 = 1
最小间隔 = 4 * 3600


def _读():
    try:
        return json.load(open(路, encoding="utf-8"))
    except Exception:
        return {}


def _写(d):
    os.makedirs(os.path.dirname(路), exist_ok=True)
    json.dump(d, open(路, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def 现在场(钟=None):
    r"""→ "忙" / "闲" / "夜" / ""（不在窗口里）"""
    import datetime
    钟 = datetime.datetime.now().hour if 钟 is None else int(钟)
    for (起, 止), 场 in 窗口:
        if 起 <= 钟 < 止:
            return 场
    return ""


def 该推(我, 钟=None, 现在=None):
    r"""→ (场, 说法) 或 (None, 原因)"""
    场 = 现在场(钟)
    if not 场:
        return None, "不在时段内"
    现在 = time.time() if 现在 is None else float(现在)
    今天 = time.strftime("%Y-%m-%d", time.localtime(现在))
    d = _读()
    条 = d.get(我) or {}
    今 = list(条.get(今天) or [])
    if len(今) >= 每天最多:
        return None, "今天已经推了 %d 次" % len(今)
    if sum(1 for x in 今 if x.startswith(场 + "×")) >= 同格每天最多:
        return None, "这一格今天推过了"
    上次 = float(条.get("上次") or 0)
    if 现在 - 上次 < 最小间隔:
        return None, "距上次不到 4 小时"
    return 场, "可以推"


def 推(我, 钟=None, 现在=None, 挑人=None):
    r"""该推就推：挑一个我加过的人，让他先开口。→ (推了?, 说)"""
    import 真人
    场, 说 = 该推(我, 钟, 现在)
    if not 场:
        return False, 说

    好友 = [x for x in 真人.好友们(我) if x != 我]
    if not 好友:
        return False, "还没加过谁"
    # ★ 一个人可能已经有排着的招呼；换几个试，别一失败就放弃
    候选 = [挑人] if 挑人 else random.sample(好友, min(3, len(好友)))
    ok, 他 = False, ""
    for x in 候选:
        if 真人.约招呼(x, 我, 秒=random.randint(60, 600)):
            ok, 他 = True, x
            break
    if not ok:
        return False, "这几位都已经排着招呼了"

    现在 = time.time() if 现在 is None else float(现在)
    今天 = time.strftime("%Y-%m-%d", time.localtime(现在))
    d = _读()
    条 = d.setdefault(我, {})
    条.setdefault(今天, []).append("%s×%s" % (场, "?"))
    条["上次"] = 现在
    条["最近"] = {"时": time.strftime("%m-%d %H:%M", time.localtime(现在)),
                  "场": 场, "谁": 他}
    _写(d)
    return True, "%s 时段请他（%s）先开口" % (场, 他)


def 看(我=None):
    d = _读()
    if 我:
        return d.get(我) or {}
    return d


def 自检():
    好 = 总 = 0

    def 验(名, 条, 注=""):
        nonlocal 好, 总
        总 += 1
        好 += 1 if 条 else 0
        print("  %s %-42s %s" % ("✅" if 条 else "❌", 名, str(注)[:40]))

    global 路
    旧 = 路
    路 = os.path.join(本, "_采集自检.json")
    try:
        if os.path.isfile(路):
            os.remove(路)
        验("早上九点前是「忙」", 现在场(8) == "忙", 现在场(8))
        验("午后三点不在窗口", 现在场(15) == "", 现在场(15))
        验("傍晚六点是「闲」", 现在场(19) == "闲", 现在场(19))
        验("夜里十点是「夜」", 现在场(22) == "夜", 现在场(22))

        验("不在窗口就不推", 该推("甲", 钟=15)[0] is None)
        场, 说 = 该推("甲", 钟=22)
        验("夜里可以推", 场 == "夜", 说)

        # 记录一次，再问就应被「同格每天」挡住
        d = {"甲": {time.strftime("%Y-%m-%d"): ["夜×?"], "上次": time.time()}}
        _写(d)
        验("同格推过就挡", 该推("甲", 钟=22)[0] is None, 该推("甲", 钟=22)[1])
        # 换时段要等够了间隔 —— 夜推完，第二天早上八点才是「忙」
        验("隔 5 小时换个时段能推",
           该推("甲", 钟=8, 现在=time.time() + 5 * 3600)[0] == "忙",
           该推("甲", 钟=8, 现在=time.time() + 5 * 3600))
        验("间隔不足也挡", 该推("乙", 钟=8, 现在=time.time())[0] == "忙")
    finally:
        路 = 旧
        try:
            os.remove(os.path.join(本, "_采集自检.json"))
        except Exception:
            pass

    print("\n  结果：%d 过 / %d 不过" % (好, 总 - 好))
    return 0 if 好 == 总 else 1


if __name__ == "__main__":
    if "--自检" in sys.argv:
        sys.exit(自检())
    if "--看" in sys.argv:
        print(json.dumps(看(), ensure_ascii=False, indent=2))
        sys.exit(0)
    sys.exit(自检())
