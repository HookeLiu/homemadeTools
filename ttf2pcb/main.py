from ttfaction import TTFaction
from dataprinter import DataPrinter
from common import _round

import time

text = """\t\t\t~~~~~~~
雷水大佬是萌新~
喵呜汪嗷喵喵喵~
\t\t\t\t~~~~"""

if __name__ == '__main__':
    time_start = time.perf_counter()
    好康的字体 = TTFaction("sarasa-monoT-sc-regular.ttf")
    好康的字体.draw(text, scale=0.015, precision=10, space=0.1, ignoreLimit=True)
    渲染数据 = 好康的字体.generateData()
    KiCAD数据 = DataPrinter(渲染数据, layers=["F.SilkS"])
    KiCAD数据.render()
    time_end = time.perf_counter()
    KiCAD数据.writeClip()
    print(f"处理了{len(text)}个符号, 耗时{_round((time_end-time_start)*1e3)}毫秒")
