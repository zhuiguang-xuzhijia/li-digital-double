# 许可证

本仓库包含三类东西，授权与来源不同。

## 论文文本

`论文/` 下的全部 Markdown 文件：

**CC BY 4.0**（知识共享 署名 4.0 国际）

你可以自由复制、传播、改编，包括商业用途，只需保留署名。

<https://creativecommons.org/licenses/by/4.0/deed.zh>

## 代码

`代码/` 下的全部 Python 文件与示例数据：

**MIT License**

```
MIT License

Copyright (c) 2026 LI Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 来源说明

### 原创

```
论文/数字分身架构.md        系统篇：四层架构
论文/场景历史叠加.md        机制篇：叠加 = 概率检索
论文/证据_场景历史叠加.md    机制篇的证据档
论文/三层可训练架构.md      路线篇：L0/L1/L2 + 七个标量
论文/设计_三模块训练流程.md  训练管线设计
论文/战略_数字生命.md       战略版（决策用）

代码/此刻.py                七种场景 + 叠加
代码/激活.py                概率记忆激活
代码/内分泌.py              三旋钮慢变量
代码/学话.py                语言指纹学习
代码/记事.py                重要事件判据
代码/模拟链.py              态度分布沙盘
代码/原型_可训练检索.py      零依赖手写反传
代码/实验_真实语料.py        检索实验 + 置换检验
代码/数据_示例.json          4 个虚构角色、15 条合成对话
```

### 第三人称引用（无代码复制）

| 项目 | 用在哪 | 说明 |
|---|---|---|
| [Persona-CAPS](https://aclanthology.org/2026.emnlp-main.1495/)（EMNLP 2026） | 论文相关工作、L0 的可行性依据 | 只引用观点，未使用其代码或数据 |
| [lucia-trend/de-ai-flavor](https://github.com/lucia-trend/de-ai-flavor) | 论文写作的体检工具 | **未打包**——上游未声明许可证，默认保留所有权利 |
| [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh) | 同上，仅推荐 | 未打包 |

### 第三方代码

**无。** 本仓库不含任何外部项目的源代码。

### 数据

全部为**合成数据**（4 个虚构角色：修锁的老陶、开花店的阿棠、开出租的老麦、送快递的小禾）。
真实用户对话不在本仓库，也不在任何公开位置。

## 注意

论文中的示例人物、对话与经历均为虚构，不对应任何真实用户。
仓库中不包含任何真实用户的档案、对话记录或个人信息。
