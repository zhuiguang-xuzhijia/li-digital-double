# -*- coding: utf-8 -*-
"""学话.py —— 从真人自己说的话里，学出他的语言指纹（v0.1.0，2026-11-13）

## 干什么
```
  他每说一句，就往样本里记一句；
  聊够一些之后，从样本里提炼出"他说话的样子"，写进他自己档案的「语言指纹」栏。
  档案是分身的底稿 —— 所以：他说得越多，他的分身就越像他。
```

## 提炼哪几样（都是能数出来的，不猜）
```
口头禅    2–4 字的片段，出现在 ≥3 条不同消息、总共 ≥4 次
语气词    吧/呢/啊/嘛/哦/呗/咯 —— 出现得多就记下来
句长      平均 ≤8 字是"句子短"，≥26 字是"话多"
标点      爱用感叹号 / 句末不加句号 / 爱用省略号 / 爱用波浪号
称呼      对人爱用"您"还是"你"
表情      爱不爱带 emoji
```

## 两个坑（写在代码里省得再踩）
```
① 档案的「语言指纹」在提示词里只取**前 2 条**（运行时._前几条(档案, "语言指纹", 2)）
   → 学到的东西必须**插到最前面**，不然写了也白写。
② 档案.加() 的来源只认 问/旁人/导入/观察/不知道/生成
   → 学出来的用 "观察"（本来就是观察来的），问 记成 "学话" 便于回滚。
```

用法：
```
  python -X utf8 学话.py --自检
  python -X utf8 学话.py --回填        # 把历史会话里"人说的话"全喂一遍
"""
import json
import os
import re
import sys
import time

本 = os.path.dirname(os.path.abspath(__file__))
if 本 not in sys.path:
    sys.path.insert(0, 本)
数据 = os.path.join(本, "数据", "学话")

最多样本 = 800
下次同步条数 = 10

# 不像"口头禅"的碎片
停用 = set("""我们 你们 他们 她们 什么 怎么 这个 那个 就是 还是 但是 因为 所以
不是 没有 可以 自己 知道 时候 现在 已经 一个 一下 觉得 然后 如果 真的 东西
这样 那样 这么 那么 时候 这里 那里 应该 可能 需要 问题 事情 感觉 就是 还是
其实 反正 一直 之前 之后 今天 明天 昨天""".split())

语气词表 = ["吧", "呢", "啊", "嘛", "哦", "呗", "咯", "呀"]


def _路(账号):
    return os.path.join(数据, re.sub(r'[\\/:*?"<>|\s]+', "_", str(账号 or "")) + ".json")


def _读(账号):
    p = _路(账号)
    if not os.path.isfile(p):
        return {"样": [], "上次同步": 0}
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {"样": [], "上次同步": 0}


def _写(账号, d):
    os.makedirs(数据, exist_ok=True)
    json.dump(d, open(_路(账号), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


def 记(账号, 话):
    r"""他说的这一句进样本。太短的不要（"嗯""好"学不出东西）。"""
    话 = str(话 or "").strip()
    if not 账号 or len(话) < 2:
        return False
    d = _读(账号)
    样 = list(d.get("样") or [])
    样.append({"话": 话[:120], "时": int(time.time())})
    d["样"] = 样[-最多样本:]
    _写(账号, d)
    return True


def 看(账号):
    return list((_读(账号) or {}).get("样") or [])


def _口头禅(样们):
    """2–4 字片段，跨 ≥3 条消息、总次数 ≥4。"""
    import collections
    计 = collections.Counter()
    分布 = collections.defaultdict(set)
    for i, s in enumerate(样们):
        文 = re.sub(r"[^\u4e00-\u9fa5]", "", s["话"])
        for n in (2, 3, 4):
            for k in range(0, max(0, len(文) - n + 1)):
                段 = 文[k:k + n]
                if 段 in 停用:
                    continue
                计[段] += 1
                分布[段].add(i)
    好 = [(段, c) for 段, c in 计.items() if c >= 4 and len(分布[段]) >= 3]
    # 长片段优先（"真服了" 比 "真服" 更像口头禅），再按次数
    好.sort(key=lambda x: (-len(x[0]), -x[1]))
    出, 用过的 = [], []
    for 段, c in 好:
        if any(段 in u or u in 段 for u in 用过的):
            continue
        出.append(段)
        用过的.append(段)
        if len(出) >= 3:
            break
    return 出


def 提炼(账号):
    r"""→ ["口头禅：…", "说话习惯：…", …]（样本 < 12 句就当还没看懂，返回空）"""
    样们 = 看(账号)
    if len(样们) < 12:
        return []
    话们 = [s["话"] for s in 样们]
    全 = "".join(话们)
    条数 = len(话们)
    出 = []

    禅 = _口头禅(样们)
    if 禅:
        出.append("口头禅：「%s」" % "」「".join(禅))

    习惯 = []
    平均 = sum(len(t) for t in 话们) / 条数
    if 平均 <= 8:
        习惯.append("句子短，常一句话就完")
    elif 平均 >= 26:
        习惯.append("话多，喜欢一长串说完")

    语气 = [w for w in 语气词表 if 全.count(w) >= max(3, 条数 * 0.25)]
    if 语气:
        习惯.append("爱带" + "、".join("「%s」" % w for w in 语气[:3]))

    if 全.count("！") + 全.count("!") >= max(3, 条数 * 0.2):
        习惯.append("爱用感叹号")
    if 全.count("…") >= max(2, 条数 * 0.15):
        习惯.append("爱用省略号")
    if 全.count("~") + 全.count("～") >= max(2, 条数 * 0.15):
        习惯.append("爱用波浪号")
    有句号 = sum(1 for t in 话们 if t.endswith("。"))
    if 条数 >= 12 and 有句号 / 条数 < 0.15:
        习惯.append("句末常常不加句号")

    您 = 全.count("您")
    你 = 全.count("你")
    if 您 >= 3 and 您 > 你:
        习惯.append("对人用「您」")
    elif 你 >= 5:
        习惯.append("直接叫「你」")

    emoji = len(re.findall(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", 全))
    if emoji >= max(2, 条数 * 0.1):
        习惯.append("爱带表情")

    if 习惯:
        出.append("说话习惯：" + "；".join(习惯))
    return 出


def 同步(账号):
    r"""把提炼结果写进档案「语言指纹」**最前面**。→ (写了几条, 说)"""
    import 档案 as D
    条们 = 提炼(账号)
    if not 条们:
        return 0, "还没学出什么（样本不够）"
    档 = D.读(账号)
    if not (档.get("对象") or {}).get("代号"):
        return 0, "这个人还没有档案"
    栏 = ((档.get("栏") or {}).get("语言指纹") or {}).get("条目")
    if 栏 is None:
        return 0, "档案里没有语言指纹这一栏"

    # 先摘掉旧的"学话"条目（免得越堆越多）
    旧 = [x for x in 栏 if str(x.get("问") or "") == "学话"]
    栏[:] = [x for x in 栏 if str(x.get("问") or "") != "学话"]

    新条 = [{"文": t, "来源": "观察", "问": "学话", "于": time.strftime("%Y-%m-%d %H:%M:%S")}
            for t in 条们]
    栏[:0] = 新条                      # 插最前面：提示词只取前 2 条
    D.写(档)
    d = _读(账号)
    d["上次同步"] = int(time.time())
    _写(账号, d)
    return len(新条), "写进去 %d 条（替掉旧的 %d 条）" % (len(新条), len(旧))


def 够了吗(账号):
    r"""样本攒够下一次同步了吗。"""
    d = _读(账号)
    return len(d.get("样") or []) - int(d.get("上次同步") or 0) >= 下次同步条数


def 回填():
    r"""把历史会话里"真人自己说的话"全喂一遍。→ (记了, 同步了几个)"""
    本目录 = os.path.dirname(os.path.abspath(__file__))
    会路 = os.path.join(本目录, "数据", "真人", "会话.json")
    if not os.path.isfile(会路):
        return 0, 0
    会们 = json.load(open(会路, encoding="utf-8"))
    个人 = {}
    for 会 in 会们.values():
        甲, 乙 = str(会.get("甲") or ""), str(会.get("乙") or "")
        for m in (会.get("消息") or []):
            谁 = str(m.get("谁") or "")
            if 谁 not in (甲, 乙):
                continue
            话 = str(m.get("话") or "").strip()
            if len(话) >= 2:
                个人.setdefault(谁, []).append(话)
    共记 = 0
    for 谁, 话们 in 个人.items():
        for t in 话们:
            if 记(谁, t):
                共记 += 1
    同步了 = 0
    for 谁 in 个人:
        n, _ = 同步(谁)
        if n:
            同步了 += 1
    return 共记, 同步了


def 自检():
    好 = 总 = 0

    def 验(名, 条, 注=""):
        nonlocal 好, 总
        总 += 1
        好 += 1 if 条 else 0
        print("  %s %-44s %s" % ("✅" if 条 else "❌", 名, str(注)[:36]))

    global 数据
    旧 = 数据
    import tempfile
    临时 = os.path.join(tempfile.gettempdir(), "学话自检_%d" % os.getpid())
    数据 = 临时
    try:
        # 一个爱说"真服了"、句子长、爱用感叹号的人
        # ★ 至少 12 条 —— 提炼的门槛是 12，样本不够会返回空，自检会假失败
        样 = ["我跟你说这个真服了", "真服了，又是我", "你别催，我这不是在弄吗",
              "真服了，行吧行吧", "我这人就这样你又不是不知道！", "行吧，随你便",
              "真服了今天这个天气", "你懂我意思吧", "行吧行吧我都听你的",
              "行吧，那就这样", "真服了，你也一样", "我知道了，别催"]
        for t in 样:
            验("记样本", 记("测", t))
        出 = 提炼("测")
        print("  提炼结果：", 出)
        验("句数够才学", 提炼("空号") == [])
        验("学到口头禅", any("口头禅" in x for x in 出), 出)
        验("口头禅里有「真服了」或「行吧」",
           any(("真服了" in x or "行吧" in x) for x in 出 if "口头禅" in x), 出)
        验("学到说话习惯", any("说话习惯" in x for x in 出), 出)
    finally:
        import shutil
        数据 = 旧
        shutil.rmtree(临时, ignore_errors=True)

    print("\n  结果：%d 过 / %d 不过" % (好, 总 - 好))
    return 0 if 好 == 总 else 1


if __name__ == "__main__":
    if "--回填" in sys.argv:
        记了, 同了 = 回填()
        print("回填：记了 %d 句，同步了 %d 个人" % (记了, 同了))
    else:
        sys.exit(自检())
