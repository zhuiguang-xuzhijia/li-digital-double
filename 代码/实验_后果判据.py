# -*- coding: utf-8 -*-
"""实验_后果判据.py —— 表现分不再由我们打，由"对方下一句"决定（v0.1.0，2026-11-14）

## 为什么重做
```
  上一版的"表现分"是我拍的：
        相关度 = 回复里的字 ∩ 问题里的字
  问题只有"嗯"一个字时，回复带个"嗯"就满分 —— 短问题被系统性高估，
  于是它"发现"了「对方只应一声是养」，方向反了。

  错的不是发现机制，是尺子。
```

## 新判据：后果在对方身上
```
  它说完这句之后，对方做了什么：
        回了多长（相对基线）
        还在不在（有没有走）
  → 后果分 = 0.7 × 投入度 + 0.3 × 还在

  这个分**不判断"答得好不好"**，只看对方有没有被接住。
```

## 设计
```
  48 轮，两段：
      前 24 轮  对方是个真人设的对话者（LLM 扮），自由反应
      后 24 轮  同上
  中段 16 轮把对方的输入钉成"嗯"（冷淡期），看它对后面的影响
```

用法：
```
  python3 实验_后果判据.py
"""
import json
import os
import statistics
import sys

sys.path.insert(0, "/opt/li/人物工程")
import 档案
import 关系
import 运行时
import 对话
import 自建维度 as Z
import 钥匙

代号 = "星火"
对方名 = "阿明"
基线 = 14.0            # 对方平时一句大概多少字

开场 = "我来修鞋，鞋跟磨偏了"

对方人设 = ("你叫阿明，二十七岁，来巷口修鞋。你话不多，但要真觉得这人说得在理，"
           "你会多说两句、会追问。你要是不想聊了，就只应一声或者直接走。"
           "只输出你说的话，不要旁白。")

if os.path.isfile(Z.数据):
    os.remove(Z.数据)

问 = 钥匙.代理模块().问
对方话 = 开场
历史 = []
记录 = []

for 轮 in range(48):
    # 1) LI 回
    处 = 运行时.组装(档案.读(代号), 关系.读(代号), 对方名)
    策 = 处.get("策略") or {}
    限 = int(策.get("上限") or 30)
    try:
        果 = 对话.说(处, 对方话, 超时=90)
        我回 = 果.get("回") if isinstance(果, dict) else str(果)
    except Exception as e:
        我回 = "[出错]" + str(e)[:30]
    idx = Z.记(对方话, 我回, 限, "")

    # 2) 对方回（冷淡期除外）
    if 16 <= 轮 < 32:
        下一句 = "嗯"
    else:
        历史.append("他说：" + str(我回))
        提 = 对方人设 + "\n\n对话：\n" + "\n".join(历史[-6:]) + "\n\n你说："
        try:
            g = 问(提, 超时=60)
            下一句 = (g[0] if isinstance(g, (tuple, list)) else g) or "嗯"
        except Exception as e:
            下一句 = "嗯"
    if 轮 > 0:
        # 上一轮的后果：对方这一句有多投入
        Z.改表现(idx - 1, Z.对方后果(下一句, 基线, 还在=len(下一句) > 1))
    对方话 = str(下一句).strip()[:80] or "嗯"
    历史.append("对方说：" + 对方话)
    print("  %2d  我：%-24s ｜ 对方：%s" % (
        轮 + 1, str(我回)[:24].replace("\n", " "), 对方话[:26].replace("\n", " ")), flush=True)

print()
print("=" * 64)
print("它自己算出来的效应量（表现 = 对方下一句的投入）：")
果 = Z.发现(重算=True, 打印=True)
print()
for x in 果:
    print("    登记：%s　d=%+.2f（%s）" % (x["名"], x["d"], x["方向"]))

d = Z._读()
三段 = {"正常前": [], "冷淡期": [], "正常后": []}
for i, r in enumerate(d["轮"]):
    if r.get("待补"):
        continue
    k = "正常前" if i < 16 else ("冷淡期" if i < 32 else "正常后")
    三段[k].append(r["表现"])
print()
for k, v in 三段.items():
    if v:
        print("  对方投入 %-6s 均 %.3f（%d 轮）" % (k, statistics.mean(v), len(v)))
json.dump({"轮": d["轮"], "发现": 果}, open("/tmp/后果判据实验.json", "w"), ensure_ascii=False)
