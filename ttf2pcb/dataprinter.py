"""
渲染多边形到KiCAD的PCBnew
"""

import numpy as np

import common
from common import _round, logConsole, data
from geometry import *


# data_demo = TTFaction("sarasa-monoT-sc-regular.ttf")
# data_demo.draw("喵唔汪?")
# data_demo.generateData()


class DataPrinter:

    def __init__(self, obj=None, name="demo233", stage=12, **settings):
        self.name = name
        self.method = settings.get("绘制模式")
        self.layers = settings.get("图层名称")

        if self.layers is None:
            self.layers = ["F.SilkS"] * len(obj)
        if len(self.layers) < len(obj):
            self.layers += [str(self.layers[-1])] * (len(obj) - len(self.layers))

        if self.method is None:
            self.method = ["填充"] * len(obj)
        if len(self.method) < len(obj):
            self.method += [str(self.method[-1])] * (len(obj) - len(self.method))

        self.dataText = ""
        self.chars = [datum["符号"] for datum in obj]
        self.points_subs = [datum["分段信息"] for datum in obj]
        self.points_coor = [datum["所有顶点"] for datum in obj]
        self.charPosition = [datum["原点位置"] for datum in obj]
        self.stage = stage
        self.traceWidth = settings.get("描边厚度")
        # TODO: 还需考虑做上格式检查及转换

    def clean(self):
        self.dataText = ""

    def load(self, obj, name="demo233", stage=12, **settings):
        self.clean()
        self.__init__(obj, name, stage, **settings)

    def render_KiCAD(self):
        self.clean()
        self.dataText += data['ClipHeader']
        time_gen = common.getHexTime()
        traceCount = 0

        for i in range(len(self.points_subs)):
            # 每一个符号分别处理
            points_subs = self.points_subs[i]
            points = self.points_coor[i]
            xyOffset = self.charPosition[i][0], -1 * self.charPosition[i][1]
            layer = self.layers[i]
            char = self.chars[i]
            meth = self.method[i]

            if meth.find("描边") > -1:  # 需要描边的话看看有没有指定描边粗细, 没指定的话用字宽度自动计算一个默认值.
                if self.traceWidth is None:
                    self.traceWidth = [_round(0.001 *
                                  ((self.charPosition[i][0] - self.charPosition[i - 1][0]) if i > 0 else self.charPosition[0][0])
                                  * 55)]
                traceCount += 1

            for grpNum, subs in points_subs.items():  # points_subs:: 分段序号:[分段起点序号,分段终点序号,是否闭合,外围框序号们/内包框序号们]
                if subs[2] and len(subs[3]) % 2 == 0 and meth.find("填充") > -1:  # 只处理闭合的多边形(如果是线就不管). 如果不需要填充那就直接跳过.
                    if len(subs[4]) == 0:  # 不含"洞"的多边形直接填上输出
                        self.dataText += data['Node_header_polygon']
                        for point in points[subs[0]:subs[1] + 1, 0]:
                            self.dataText += data['Node_coord_polygon'].format(point[0] + xyOffset[0], -1 * (point[1] + xyOffset[1]))
                        self.dataText += data['Node_footer_polygon'].format(layerName=layer, stroke_width="0", hexTime=time_gen)
                    else:  # 对于含洞的, 只含一个洞的通过调整点序的方法实现"去洞"; 含有多个洞的暂时直接用KiCAD的Zone来挖洞(这样不优, 已经想到了"一笔画"的方法但还没来得及做)
                        # 先数数包含洞的次数以确定是不是真的含有多个洞(如"回"这样有两个框和两个"洞"的图形实际上能拆成两组只含有一个"洞"的)
                        flag_isOutline = False
                        tmp_count_innerOutlines = 0
                        tmp_count_trueChilds = 0
                        for groupNum in subs[4]:
                            if groupNum == grpNum:
                                continue
                            if points_subs[groupNum][2] and len(points_subs[groupNum][3]) % 2 == 0 and grpNum in points_subs[groupNum][3]:
                                tmp_count_innerOutlines += 1
                            if points_subs[groupNum][3] == [grpNum]:
                                tmp_count_trueChilds += 1

                        if tmp_count_innerOutlines > 0 and tmp_count_trueChilds == 1:
                            flag_isOutline = True

                        if len(subs[4]) == 1 or flag_isOutline:  # 只含有一个"实际洞"的
                            tmp_innerlineInfo = points_subs[subs[4][0]]

                            # 外框起点→内框顺序闭合→外框的起点→外框顺序闭合
                            points_comb = [points[subs[0], 0]] + list(points[tmp_innerlineInfo[0]:tmp_innerlineInfo[1], 0]) + [points[tmp_innerlineInfo[0]][0]] + [points[subs[0], 0]] + list(
                                points[subs[0] + 1:subs[1], 0])

                            self.dataText += data['Node_header_polygon']
                            for point in points_comb:
                                self.dataText += data['Node_coord_polygon'].format(point[0] + xyOffset[0], -1 * (point[1] + xyOffset[1]))
                            self.dataText += data['Node_footer_polygon'].format(layerName=layer, stroke_width="0", hexTime=time_gen)

                        else:  # 当前版本(0.0.1_alpha)为了方便就直接用KiCad的zone了
                            # TODO: 待改成"一笔画"的算法. (已经想出了一种递归方法, 但还没做出来... 实际上无论有几个"洞", 通过增加顶点并调整顺序的方法都能得到**看起来**有"洞"的无洞封闭多边形.)
                            outlinePoints = [Point(point[0], point[1]) for point in points[subs[0]:subs[1] + 1, 0]]
                            innerLines = {}
                            for groupNum in subs[4]:
                                innerLines[groupNum] = points[points_subs[groupNum][0]:points_subs[groupNum][1], 0]
                            self.dataText += data['Node_header_zone'].format(0, layer, time_gen, 0.233, self.stage)
                            self.dataText += data['Node_header_fillPolygon']
                            for point in outlinePoints:
                                self.dataText += "(xy {} {}) ".format(point.x + xyOffset[0], -1 * (point.y + xyOffset[1]))
                            self.dataText += ")\n\t\t)"

                            for grpunm, subPoints in innerLines.items():
                                self.dataText += data['Node_header_fillPolygon']
                                for point in subPoints:
                                    self.dataText += "(xy {} {}) ".format(point[0] + xyOffset[0], -1 * (point[1] + xyOffset[1]))
                                self.dataText += ") )"
                            self.dataText += "\n\t)"

                if meth.find("描边") > -1:  # 描边实际上就是把这一个多边形的所有点用线连起来.
                    points_thisPoly = points[subs[0]:subs[1], 0]
                    np.append(points_thisPoly, np.array(points_thisPoly[0]))  # 连线要回到起点
                    for j in range(len(points_thisPoly)):
                        self.dataText += data['Node_data_segment'].format(points_thisPoly[j-1][0] + xyOffset[0],
                                                                          -1 * (points_thisPoly[j-1][1] + xyOffset[1]),
                                                                          points_thisPoly[j][0] + xyOffset[0],
                                                                          -1 * (points_thisPoly[j][1] + xyOffset[1])
                                                                          )
                        self.dataText += data['Node_footer_polygon'].format(layerName=layer,
                                                                            stroke_width=self.traceWidth[(traceCount-1) % len(self.traceWidth)],
                                                                            hexTime=time_gen
                                                                            )

        self.dataText += data['Clipfooter']

    def writeClip(self):
        if len(self.dataText) > 55:
            common.setClip(self.dataText)
        else:
            if len(self.chars) > 0:
                logConsole.warning(f"输入了数据但没有生成内容:\n{self.chars}\n{self.points_subs}\n{self.method}")
                print("QwQ...这里出了点问题? 如有疑问可联系QQ2139223150解决")
            else:
                print( ResourceWarning("摸鱼~ (没有生成任何数据, 输入或设置出了问题?)") )

    def toText(self):
        return self.dataText
