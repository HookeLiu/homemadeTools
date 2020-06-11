"""
自选ttf字体, 将输入的文本内容转换成一系列基础画笔动作(包括把svg的曲线采样为点)
"""
import time

import common
from common import _round, logConsole

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

from geometry import *

import re
import numpy as np


def getPolyList(actions, precision=50, pointsType=tuple, returnText=False):
    """
    将线段笔画转为多边形顶点并按多边形关系划分.
    :param actions: draw(str) 得到的笔画
    :param precision: 采样粒度. 数值越大采样越少也越简洁, 通常可以设置得很大.
    :param pointsType: 点的形式. 指定输出的点以什么形式表示.
    :param returnText: 以文本形式输出. (仅用于调试)
    :return: 多边形们的顶点们. (二维列表)
    """
    data_geome = ""
    for item in actions:
        if type(item) != MoveTo:
            points = list(item.segments(precision))
            if len(points) == 2:
                if points[0] == points[1]:
                    continue # 去重化简
            for point in points:
                data_geome += str(point)
        else:
            data_geome += f"MoveTo\n"
    data_geomes = data_geome.split("MoveTo\n")
    if returnText:
        return data_geome
    polys = []
    for geome in data_geomes:
        if len(geome) < 2:
            continue
        reGeome = re.findall(common.pattern['coor_geome'], geome)
        coors = []
        prePoint = None
        for i in range(len(reGeome)):
            if reGeome[i] != prePoint:
                if pointsType == tuple:
                    coors.append((float(reGeome[i][0]), float(reGeome[i][1])))
                elif pointsType == list:
                    coors.append([float(reGeome[i][0]), float(reGeome[i][1])])
            prePoint = reGeome[i]
        polys.append(coors)
    return polys


def analyzPolygons(polys, debug=False):
    """
    分析多边形组的包含与被包含("洞")关系.
    (因为svg是分多个多边形画的, 此处使用PNPoly来确定每个多边形的边框关系以确定哪些区域是"空"的)
    :param polys: 多边形组.
    :param debug: 是否输出调试信息
    :return: 列表, 每个多边形的信息. (`[{'closed': True, 'outlines': [0], 'childs': []}]`
    """
    flag_polys = []
    for _ in range(len(polys)):  # 描述polys中每段线性质的表, None表示未知
        isClosed = None
        flag_polys.append({'closed':isClosed,'outlines':[],'childs':[]})
    for i in range(len(polys)):
        if polys[i][0] == polys[i][-1]:
            flag_polys[i]['closed'] = isClosed = True  # 闭合是多边形, 不闭合的话只是线条
    for i in range(len(polys)):
        if i < len(polys)-1:
            # 如果本条段闭合, 看看其他所有的段有无在自己内部的, 如果有, 那么自己可能是outline. 如此迭代下去, 奇数次被包含的不是outline, 偶数次的可能是.
            if flag_polys[i]['closed']:
                for t in range(len(polys)):
                    if t == i:
                        continue
                    if flag_polys[t]['closed']:
                        flag_overflow = False
                        for point in polys[t]:
                            if not common.pnpoly(polys[i], point):
                                flag_overflow = True
                                if debug:
                                    print(polys[i])
                                    print(f"第{t}段的第({polys[t].index(point)})点{point}不在第{i}段线里")
                                if not debug:
                                    break
                        if not flag_overflow and t < len(polys) :
                            flag_polys[i]['childs'].append(t)
                            if i not in flag_polys[t]['outlines']:
                                flag_polys[t]['outlines'].append(i)
        elif i == len(polys) - 1:  #  对于最后一条线来说, 如果它的所有点都不在任何一个outline里的话, 那么它是独立的
            for t in range(len(polys)):
                if t == i:
                    continue
                if flag_polys[t]['closed']:
                    for point in polys[i]:
                        if common.pnpoly(polys[t], point):
                            if t not in flag_polys[i]['outlines'] and i != t:
                                flag_polys[i]['outlines'].append(t)
                                if i not in flag_polys[t]['childs']:
                                    flag_polys[t]['childs'].append(i)
                            break
    return flag_polys


def getPloysPoints(polys, scale=(1, 1)):
    """
    从多边形组里取出每个多边形的所有顶点并以numpy ndarray的形式存储.
    :param polys: getPolyList函数输出的多边形组.
    :param scale: 点级别整体缩放系数.
    :return: 所有点的numpy array数组形式. ( [点,所属多边形的编号] )
    """
    points = []
    for poly in polys:
        if scale != (1, 1):
            t = [(_round(point[0]*scale[0]), _round(point[1]*scale[1])) for point in poly]
        else:
            t = [(point[0], point[1]) for point in poly]
        for l in t:
            points.append(np.array([np.array(l),polys.index(poly)]))
    points = np.array(points)
    return points


def getPointsSubsection(points, polys_con):
    """
    获取多边形组中每个多边形的信息.
    :param points: getPloysPoints函数输出的数组.
    :param polys_con: analyzPolygons函数给出的包含层次关系.
    :return: 字典. 多边形的: 起/止点的点序号/是否闭合/上层边框们的序号们/包含的多边形们的序号们.
    """
    gro = 0
    p = []
    subsection = {}
    t = m = 0
    for i in range(len(points)):
        if i == len(points)-1:
            p.append(points[i])
            t += (len(p)+1)
            subsection[gro] = [m, t-2, polys_con[gro]['closed'], polys_con[gro]['outlines'], polys_con[gro]['childs']]
            m = t - 1
        if i < len(points):
            if points[i][1] == gro:
                p.append(points[i])
            else:
                t += (len(p)+1)
                subsection[gro] = [m, t-2, polys_con[gro]['closed'], polys_con[gro]['outlines'], polys_con[gro]['childs']]
                m = t - 1
                p = []
            gro = points[i][1]
    return subsection


class TTFaction:
    """
    实例化某种字体
    @:parameter: ttf字体文件路径
    @:draw(): 字符串(当前限制10字符)转为元笔画(把所有svg动作转为了线段笔画, 这里称为action)
    """
    def __init__(self, fontName):
        # 创建针对某个字体的实例, 先获取其属性以及创建其索引. 可能还需要加上对字体可用性的检查

        self.fontObject = TTFont(fontName)
        self.glyphSet = self.fontObject.getGlyphSet()
        self.bestcmap = self.fontObject['cmap'].getBestCmap()
        self.charMap = dict()
        for key in self.bestcmap.keys():
            value = self.bestcmap[key]
            key = hex(key)
            self.charMap[key] = value

        self.source = []  # 记录原始输入
        self.Items = []  # 字的点们
        # TODO: 考虑做成交互式修改位置和大小的方式
        self.charPos = []        # 每个字的位置((x,y) 目前只按字start即基线左侧计算)

    def getCharSize(self, character="?", glyph=None, scale=1.0):
        if glyph is None:
            char = self.bestcmap[ord(character)]
            glyph = self.glyphSet[char]
        h, w = glyph.height, glyph.width
        if scale != 1:
            w, h = _round(w*scale, 6), _round(h*scale, 6)
        return w, h

    def clean(self):
        self.source = []
        self.Items = []
        self.charPos = []

    def draw(self, text, scale=0.1, precision=10, space=0.1, ignoreLimit=False):
        # 使用geometry转换fontTools生成的svg path
        source = "测试demo"
        if type(text) != str:
            text = str(text)
        if len(text) > 0:
            source = text
        source = re.sub(r"[^ ^\n\S]", " ", source)  # 不可见的那些特殊符号当成空格处理
        source = source.replace("\\", "\\\\")
        if not ignoreLimit:
            if len(source) > 45:
                source = source[:45]
                logConsole.warning( FutureWarning("单行模式暂时只支持45字符以内的文本. 内容`%s`被忽略" % text[46:]) )
        elif len(text) == 0:
            logConsole.warning( Warning("输入不能为空. 默认内容为`测试demo`") )

        self.clean()  # 每次draw前清理一下
        self.source = list(source)

        cursor = [0, 0]
        for i, char in enumerate(source):  # 依次绘制每个字符

            if char != "\n":  # 换行符直接跳过
                try:  # 这个版本暂时没做failedback字体的功能
                    # TODO: 加上failedback字体
                    charName = self.bestcmap[ord(char)]
                    glyph = self.glyphSet[charName]
                    charWidth, charHeight = self.getCharSize(glyph=glyph, scale=scale)
                except Exception as e:
                    logConsole.warning(f"取字`{char}`信息失败: {e}")
                    charName = self.bestcmap[ord("口")]
                    glyph = self.glyphSet[charName]
                    charWidth, charHeight = self.getCharSize(glyph=glyph, scale=scale)
                if i == 0:
                    self.charPos.append([0, 0])  # 每个字的起始总是上一个字的起始加上(字宽+间距)
                    cursor = [(charWidth * (1+space)), 0]
                else:
                    self.charPos.append([cursor[0], cursor[1]*charHeight])
                    cursor[0] += (charWidth * (1+space))
            else:
                cursor[0] = 0   # \r
                cursor[1] += 1  # \n
                continue

            pen = SVGPathPen(None)
            glyph.draw(pen)
            penCommandList = pen._commands

            x_previous = y_previous = 0.0  # 上一步操作的结果记录
            x_current = y_current = 0.0    # 当前正在操作的过程
            x_start = y_start = 0.0        # 每个路径的起点

            items = []  # 临时储存字的笔画

            for command in penCommandList:
                cmd = common.getCode(command)
                vec = common.getVert(command)

                flag_absolute = (cmd == cmd.upper())
                cmd = cmd.upper()

                if cmd == 'M':  # MoveTo
                    x_start = x_previous = vec[0]
                    y_start = y_previous = vec[1]
                    if flag_absolute is True:
                        x_current = vec[0]
                        y_current = vec[1]
                    else:
                        x_current = x_previous + vec[0]
                        y_current = y_previous + vec[1]

                    items.append(MoveTo(Point(x_current, y_current)))
                    x_previous, y_previous = x_current, y_current

                elif cmd in 'LHV':  # LineTo, Horizontal 和 Vertical line
                    # H和V需要单独取顶点
                    if flag_absolute is True:
                        x_current, y_current = x_previous, y_previous
                    else:
                        x_current, y_current = [0, 0]

                    if cmd == "H":  # 水平线共用Y, 更新X
                        x_current = vec[0]
                        y_current = y_previous
                    if cmd == "V":  # 垂直线更新Y
                        x_current = x_previous
                        y_current = vec[0]
                    if cmd == "L" and len(vec) == 2:
                        x_current, y_current = vec

                    if flag_absolute is False:
                        x_current += x_previous
                        y_current += y_previous

                    items.append(
                        Segment(
                            Point(x_previous, y_previous),
                            Point(x_current, y_current)
                        )
                    )
                    x_previous, y_previous = x_current, y_current

                elif cmd in 'CQ':
                    dimension = {'Q': 2, 'C': 3}
                    bezier_pts = []
                    bezier_pts.append(Point(x_previous, y_previous))

                    for i in range(dimension[cmd]):
                        x_current = vec[2 * i]
                        y_current = vec[2 * i + 1]
                        if flag_absolute is False:
                            x_current += x_previous
                            y_current += y_previous
                        bezier_pts.append(Point(x_current, y_current))

                    items.append(Bezier(bezier_pts))
                    x_previous, y_previous = x_current, y_current

                elif cmd == 'Z':  # 闭合
                    items.append(
                        Segment(
                            Point(x_previous, y_previous),
                            Point(x_start, y_start)

                        )
                    )

                else:
                    pass  # A暂时不能处理

            for item in items:
                item.scale(scale)
            self.Items.append(items)

    def generateData(self, scale=(1, 1), precision=100, pointsType=list):
        """
        输出可用于后级渲染的点和点间关系.
        :param scale: 缩放倍率, 调整点级别尺寸.
        :param precision: 采样粒度, 数值越大颗粒越大复杂度越小. 用于kicad可考虑用非常大的值.
        :param pointsType: 输出点的类型, 列表或元组.
        :return: 字典 :: 符号/所有顶点/子多边形分段信息/原点位置
            其中, 顶点的形式为numpy :: object, 每一个object为一个array( [x,y], 所属多边形编号 )
        """

        if len(self.Items) < 1:
            logConsole.warning( BytesWarning("尚未绘制内容, 需要先调用draw(str). 用示例内容替换.") )
            self.draw("喵唔汪?")

        time_start = time.perf_counter()

        output = []

        for i, char in enumerate(self.Items):
            polys = getPolyList(char, precision=precision, pointsType=pointsType)
            polys_con = analyzPolygons(polys)
            points = getPloysPoints(polys, scale=scale)
            points_subs = getPointsSubsection(points, polys_con)
            output.append(
                {
                    '符号': self.source[i],
                    '所有顶点': points,
                    '分段信息': points_subs,
                    '原点位置': self.charPos[i]
                }
            )

        time_end = time.perf_counter()
        logConsole.info(f"处理了{len(self.Items)}个符号, 耗时{_round((time_end-time_start)*1e3)}毫秒")

        return output
