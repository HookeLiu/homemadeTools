"""
所有用到基础库和基础函数以及常量设置
"""

import time
import os
import sys
import win32clipboard as clipboard
from win32con import *
import re
import math
import logging
from geometry import *

# 配置个记录器以便输出和记录相关信息
logging.addLevelName(11, "TIPS")  # 自定义一个级别, 用于充当注释
screenFormat = logging.Formatter('+ [%(levelname)6s] | %(asctime)s @%(relativeCreated)8d +: %(message)s')
fileFormat = logging.Formatter(
    '[%(levelname)8s] | %(asctime)s @%(relativeCreated)8d | "%(filename)15s" line%(lineno)4d, in `%(threadName)10s` : %(message)s',
    '%d %b %Y %H:%M:%S')
consoleHandle = logging.StreamHandler()
consoleHandle.setFormatter(screenFormat)
consoleHandle.setLevel(logging.NOTSET)
logFile = "./debug.log"
fileHandle = logging.FileHandler(logFile, encoding="UTF-8")
fileHandle.setFormatter(fileFormat)
fileHandle.setLevel(logging.NOTSET)

logRoot = logging.getLogger("root")
logRoot.addHandler(fileHandle)
logConsole = logging.getLogger("root.screen")
logConsole.addHandler(consoleHandle)


def setClip(d2c):
    try:
        clipboard.OpenClipboard()
        time.sleep(0.05)  # 如果不加这些延时, 偶尔会出现不能写入剪贴板的情况. 还未找到原因
        clipboard.EmptyClipboard()
        time.sleep(0.05)
        clipboard.SetClipboardData(CF_UNICODETEXT, d2c)
        if clipboard.GetClipboardData() != d2c:
            return "写剪贴板失败"
        else:
            return f"写剪贴板成功({len(d2c)}字符)"
    finally:
        time.sleep(0.1)
        clipboard.CloseClipboard()
        time.sleep(0.1)


def getHexTime(timestamp=time.time()):
    hexTime = str(hex(int(timestamp)))[2:].upper()
    return hexTime


data = {
    'ClipHeader': """(kicad_pcb (version 616471607) (host pcbnew "233")""",
    'Node_header_polygon': "\n  (gr_poly (pts",
    'Node_coord_polygon': " (xy {} {}) ",
    'Node_footer_polygon': ") (layer {layerName}) (width {stroke_width})  (tstamp {hexTime}) )",
    'Node_data_segment': "\n  (gr_line (start {} {}) (end {} {}",
    'Clipfooter': "\n)",
    'Node_header_zone': """\n\t(zone (net -233) (net_name "{0}") (layer {1}) (tstamp {2}) (hatch edge {3}) (min_thickness 0)
        (fill yes (arc_segments {4}) (thermal_gap 0) (thermal_bridge_width 0))""",
    'Node_header_fillPolygon':  "\n\t\t(polygon (pts ",
}

pattern = {
    'svgCode': re.compile(r"[MLHVCSQTAZ]", flags=re.IGNORECASE),
    'value': re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[e][-+]?\d+)?", flags=re.IGNORECASE),
    'unit': re.compile(r"em|ex|px|in|cm|mm|pt|pc|%", flags=re.IGNORECASE),
    'coor_Kicad': re.compile(r"\(xy (?P<x>[-+]?(?:\d+(?:\.\d*)?|\.\d+)) (?P<y>[-+]?(?:\d+(?:\.\d*)?|\.\d+))\)", flags=re.IGNORECASE),
    'coor_geome': re.compile(r"\((?P<x>[-+]?(?:\d+(?:\.\d*)?|\.\d+)),(?P<y>[-+]?(?:\d+(?:\.\d*)?|\.\d+))\)", flags=re.IGNORECASE),
}


unit_convert = {
        None: 1,           # Default unit (same as pixel)
        'px': 1,           # px: pixel. Default SVG unit
        'em': 10,          # 1 em = 10 px FIXME
        'ex': 5,           # 1 ex =  5 px FIXME
        'in': 96,          # 1 in = 96 px
        'cm': 96 / 2.54,   # 1 cm = 1/2.54 in
        'mm': 96 / 25.4,   # 1 mm = 1/25.4 in
        'pt': 96 / 72.0,   # 1 pt = 1/72 in
        'pc': 96 / 6.0,    # 1 pc = 1/6 in
        '%' :  1 / 100.0   # 1 percent
        }


def getCode(cmd):
    res = re.match(pattern['svgCode'], cmd)
    if res is not None:
        return res.group(0)
    else:
        return ""


def getVert(cmd):
    res = [float(val) for val in re.findall(pattern['value'], cmd)]
    return res


def pnpoly(vertPoints_org, testPoint, show=False):
    """
    PNPoly算法的打包. 判断指定点是否在指定点群围成的多边形内部(不含边).
    :param vertPoints_org: 多边形的顶点们.
    :param testPoint: 待测试的点.
    :param show: 是否绘制图形. (使用matplotlib, 主要用于调试)
    :return: True ==> 在内部, False ==> 不在内部或者正好落在边框上
    """
    import numpy as np, math
    vertPoints = []
    if type(vertPoints_org[0]) in (list, tuple, np.ndarray):
        if type(vertPoints_org[0][0]) is not float:
            for point in vertPoints_org:
                vertPoints.append((float(point[0]), float(point[1])))
        if len(vertPoints) != len(vertPoints_org):
            if type(vertPoints_org) == list:
                vertPoints = np.array(vertPoints_org)
    elif type(vertPoints_org) == list and type(vertPoints_org[0]) == Point:
        vertPoints = np.array([(point.x, point.y) for point in vertPoints_org])
    else:
        raise TypeError("输入的类型不支持")
    if str(vertPoints[0]) != str(vertPoints[-1]):
        if show:
            print("###注意: 指定了未闭合的多边形(绘图需要). 自动闭合...")
        t = list(vertPoints); t.append(t[0])
        vertPoints = np.array(t)
    epoch = len(vertPoints) - 1
    contain = False
    for i in range(epoch):
        j = epoch - 1 if i == 0 else i - 1
        if ( (vertPoints[i][1] > testPoint[1]) != (vertPoints[j][1]> testPoint[1]) and
           (testPoint[0] < (vertPoints[j][0] - vertPoints[i][0]) * (testPoint[1] - vertPoints[i][1]) / (vertPoints[j][1] - vertPoints[i][1]) + vertPoints[i][0]) ):
            contain = not contain
    if show:
        import matplotlib, matplotlib.pyplot as plt
        max_x, max_y = max([v[0] for v in vertPoints]), max([v[1] for v in vertPoints]);
        min_x, min_y = min([v[0] for v in vertPoints]), min([v[1] for v in vertPoints]);
        plt.figure(dpi=96, figsize = (5, 5)); plt.grid(True)
        flg_width, flg_height = abs(max_x-min_x), abs(max_y-min_y)
        plt.xlim(min_x - 0.1*flg_width, max_x + 0.1*flg_width); plt.ylim(min_y - 0.1*flg_height, max_y + 0.1*flg_height)
        markSize = math.tanh(min(flg_width,flg_height)) + 1
        plt.scatter(vertPoints[:,0], vertPoints[:,1], s=markSize+10, marker='s')
        plt.plot(vertPoints[:,0], vertPoints[:,1], color="0.92", linewidth=markSize); plt.plot(testPoint[0], testPoint[1], 'oc' if contain else 'or')
        hint = " 在" if contain else " 不在"
        return("测试点" + str(testPoint) + hint + f" 指定的 {epoch}边形 内部")
    return contain


def _round(value, bits=3):     # 实际上就是包装了一下四舍五入的方法, 为了后面可以少打点字
    if type(value) == str:
        try:
            value = float(value)
        except:
            raise TypeError("输入的数据不支持")
    else:
        value = float(value)
    value = round(value, bits)
    if str(value).split(".")[1] == "0":
        value = int(value)
    return value