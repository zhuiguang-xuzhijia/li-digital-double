# -*- coding: utf-8 -*-
r"""从 GitHub API 拉文件（raw.githubusercontent 被墙时的替代通道）。"""
import base64
import json
import os
import sys
import urllib.request

仓 = "caps-research/persona-caps"
支 = "master"
出 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "数据")


def 拉(路径):
    址 = "https://api.github.com/repos/%s/contents/%s?ref=%s" % (仓, 路径, 支)
    请 = urllib.request.Request(址, headers={"User-Agent": "dsh", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(请, timeout=60) as r:
        j = json.loads(r.read().decode("utf-8"))
    if isinstance(j, list):
        return j
    return base64.b64decode(j["content"])


def 下载(路径, 本地):
    os.makedirs(os.path.dirname(本地), exist_ok=True)
    数 = 拉(路径)
    with open(本地, "wb") as f:
        f.write(数)
    return len(数)


if __name__ == "__main__":
    要 = [
        ("data/if_then/paper/beck_2022_v3/patterns.selected.jsonl", "if_then/patterns.selected.jsonl"),
        ("data/if_then/paper/beck_2022_v3/patterns.all.jsonl", "if_then/patterns.all.jsonl"),
        ("data/if_then/paper/beck_2022_v3/manifest.json", "if_then/manifest.json"),
        ("data/if_then/paper/beck_2022_v3/high_neuroticism.jsonl", "if_then/high_neuroticism.jsonl"),
        ("data/if_then/paper/beck_2022_v3/low_neuroticism.jsonl", "if_then/low_neuroticism.jsonl"),
        ("data/if_then/README.md", "if_then/README.md"),
    ]
    for 远, 近 in 要:
        try:
            n = 下载(远, os.path.join(出, 近))
            print("  ✓ %-46s %6d 字节" % (近, n))
        except Exception as e:
            print("  ✗ %-46s %s" % (近, str(e)[:60]))
