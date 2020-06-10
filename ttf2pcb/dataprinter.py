"""
渲染多边形到KiCAD的PCBnew
"""
import time

import common
from common import _round, logConsole, logALL, data
from ttfaction import TTFaction

from geometry import *

data_demo = TTFaction("sarasa-monoT-sc-regular.ttf")
data_demo.draw("喵唔汪?")
data_demo.generateData()


class DataPrinter:

    def __init__(self, obj=data_demo, name="demo233", method="填充", layers=None, stage=12):
        if layers is None:
            layers = ["F.SilkS"] * len(data)
        if len(layers) < len(obj):
            layers += [layers][-1] * (len(obj)-len(layers))
        self.name = name
        self.method = method
        self.layers = layers
        self.dataText = ""
        self.chars        = [datum["符号"] for datum in obj]
        self.points_subs  = [datum["分段信息"] for datum in obj]
        self.points_coor  = [datum["所有顶点"] for datum in obj]
        self.charPosition = [datum["原点位置"] for datum in obj]
        self.stage = stage
        # TODO: 还需考虑做上格式检查及转换

    def clean(self):
        self.dataText = ""

    def load(self, obj, name="demo233", method="填充", layers=None, stage=12):
        self.clean()
        self.__init__(self, obj, name, method, layers, stage)

    def render(self):
        self.clean()
        self.dataText += data['ClipHeader']
        for i in range(len(self.points_subs)):
            # 每一个符号分别处理
            points_subs = self.points_subs[i]
            points = self.points_coor[i]
            xyOffset = self.charPosition[i][0], -1*self.charPosition[i][1]
            layer = self.layers[i]
            char = self.chars[i]

            for grpNum, subs in points_subs.items():
                if subs[2] and len(subs[3]) % 2 == 0:  # 只处理闭合的多边形(如果是线就不管)
                    if len(subs[4]) == 0:  # 不含"洞"的多边形直接填上输出
                        self.dataText += data['Node_header_polygon']
                        for point in points[subs[0]:subs[1] + 1, 0]:
                            self.dataText += data['Node_coord_polygon'].format(point[0]+xyOffset[0], -1 * (point[1]+xyOffset[1]))
                        self.dataText += data['Node_footer_polygon'].format(layerName=layer, stroke_width="0", hexTime=common.getHexTime())
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
                                self.dataText += data['Node_coord_polygon'].format(point[0]+xyOffset[0], -1 * (point[1]+xyOffset[1]))
                            self.dataText += data['Node_footer_polygon'].format(layerName=layer, stroke_width="0", hexTime=common.getHexTime())

                        else:  # 当前版本(0.0.1_alpha)为了方便就直接用KiCad的zone了
                            outlinePoints = [Point(point[0], point[1]) for point in points[subs[0]:subs[1] + 1, 0]]
                            innerLines = {}
                            for groupNum in subs[4]:
                                innerLines[groupNum] = points[points_subs[groupNum][0]:points_subs[groupNum][1], 0]
                            self.dataText += data['Node_header_zone'].format(0, layer, common.getHexTime(), 0.233, self.stage)
                            self.dataText += data['Node_header_fillPolygon']
                            for point in outlinePoints:
                                self.dataText += "(xy {} {}) ".format(point.x+xyOffset[0], -1 * (point.y+xyOffset[1]))
                            self.dataText += ")\n\t\t)"

                            for grpunm, subPoints in innerLines.items():
                                self.dataText += data['Node_header_fillPolygon']
                                for point in subPoints:
                                    self.dataText += "(xy {} {}) ".format(point[0]+xyOffset[0], -1 * (point[1]+xyOffset[1]))
                                self.dataText += ") )"
                            self.dataText += "\n\t)"
        self.dataText += data['Clipfooter']

    def writeClip(self):
        common.setClip(self.dataText)
