# -*- coding: utf-8 -*-
r"""修评测泄漏：负样本拆成训练/测试两份，配对严格不重叠。"""
import io
import json
import os
import random

本 = os.path.dirname(os.path.abspath(__file__))
样本 = json.load(io.open(os.path.join(本, "训练集.json"), encoding="utf-8"))

随 = random.Random(7)
序 = list(range(len(样本)))
随.shuffle(序)
切 = int(len(序) * 0.8)
训序, 测序 = 序[:切], 序[切:]


def 造负(序们, 种子, 排除, 名):
    r"""给每个样本配一个错的行为。排除：已有的（情境,行为）对，绝不重复。"""
    随 = random.Random(种子)
    出, 用过 = [], set(排除)
    for i in 序们:
        for _ in range(30):
            别 = 随.choice(样本)
            if 别["行为"] == 样本[i]["行为"]:
                continue
            k = (样本[i]["情境"], 别["行为"])
            if k in 用过:
                continue
            用过.add(k)
            出.append({"情境": 样本[i]["情境"], "行为": 别["行为"],
                       "强度": 样本[i]["强度"], "n": 样本[i]["n"]})
            break
    json.dump(出, io.open(os.path.join(本, 名), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 出, 用过


# 先把正样本自己的配对全排除，免得负样本撞上真配对
正对 = {(x["情境"], x["行为"]) for x in 样本}

训练负, 用过 = 造负(训序, 21, 正对, "负样本_训练.json")
测试负, 用过2 = 造负(测序, 22, 用过, "负样本_测试.json")

ka = {(x["情境"], x["行为"]) for x in 训练负}
kb = {(x["情境"], x["行为"]) for x in 测试负}
print("  训练负样本 %d 条　测试负样本 %d 条" % (len(训练负), len(测试负)))
print("  训练/测试配对重叠：%d　（必须 0）" % len(ka & kb))
print("  负样本撞上真配对：%d　（必须 0）" % len((ka | kb) & 正对))
