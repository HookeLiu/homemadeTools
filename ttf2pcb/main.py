"""
主入口. 基础功能调用的demo和GUI
"""
import json
import re
import time

from common import _round, logConsole, setClip, logRoot
from dataprinter import DataPrinter
from ttfaction import TTFaction

DEMO = False  # 如果想查看示例的话就把它改成True


text_demo1 = \
    """⚡雷水聚聚TQL
awsl\tQωQ\t太√⑥了
\t\tWSL012³³↲"""

text_demo2 = "口口口\n口"

if DEMO:
    time_start = time.perf_counter()
    好康的字体 = TTFaction("sarasa-monoT-sc-regular.ttf")
    好康的字体.draw(text_demo1, scale=0.015, precision=10, space=0.01, ignoreLimit=True)
    渲染数据 = 好康的字体.generateData()
    KiCAD数据 = DataPrinter(渲染数据,
                          图层名称=["F.SilkS", "F.Mask", "F.Cu", "F.SilkS"],
                          绘制模式=["描边", "填充", "描边+填充", "描边", "填充"],
                          描边厚度=[0.2, 0.8, 0.5]
                          )
    KiCAD数据.render_KiCAD()
    time_end = time.perf_counter()
    KiCAD数据.writeClip()
    print(f"处理了{len(text_demo2)}个符号, 耗时{_round((time_end-time_start)*1e3)}毫秒")

else:
    from MainWnd import Ui_ttf2pcb

    import sys
    from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QLabel
    from PyQt5.QtGui import *
    from PyQt5.QtCore import Qt, QObject, pyqtSignal


    def printc(self, style='color:#40ef3f;'):
        if type(self) == str:
            self.replace(" ", "&nbsp;")
        print(f"<span style={style}><em style='color:yellow'>⚡{time.strftime('%X', time.localtime())}⚡</em> {self}</span><br />")

    class SysOutRedirect(QObject):  # 重定向标准输出到textWidget, 以便输出到图形界面
        newText = pyqtSignal(str)

        def write(self, text):
            self.newText.emit(str(text))

        def flush(self):
            sys.__stdout__.flush()
            sys.__stderr__.flush()

    class MainWindow(QMainWindow, Ui_ttf2pcb):
        def __init__(self):
            super().__init__()
            self.setupUi(self)
            sys.stdout = SysOutRedirect(newText=self.onUpdateText)
            sys.stderr = SysOutRedirect(newText=self.onUpdateText)
            self.show()
            self.outputBuff = ""
            self.userFont = None

            self.initUI()

        def initUI(self):
            self.action_cfmFontFile.clicked.connect(lambda: self.checkFontFile(None))
            self.action_startDraw.clicked.connect(self.draw)
            self.action_setClipboard.clicked.connect(self.copyData)
            self.action_cleanConsole.clicked.connect(self.clearConsole)
            self.menu_exit.triggered.connect(lambda: sys.exit(0))
            self.menu_loadstatus.triggered.connect(lambda: QMessageBox.information(self,"咕咕咕...","再等等吧...",QMessageBox.Yes,QMessageBox.Yes))
            self.setStatusBar(self.statusBar)
            self.statusBarLable = QLabel()
            self.statusBar.addPermanentWidget(self.statusBarLable)
            self.menu_demo.triggered.connect(self.setDemo)

            try:
                self.checkFontFile(r"C:\Windows\Fonts\simkai.ttf")
            except Exception as e:
                logRoot.error("尝试打开系统字体`simkai.ttf`失败: " + str(e))
                self.userFont = None
                self.statusBar.showMessage("尝试打开系统字体`simkai.ttf`失败: " + str(e), 5000)

        def clean(self):
            self.outputBuff = ""

        def setDemo(self):
            self.i_fontfileName.setText('sarasa-monoT-sc-regular.ttf')
            self.checkFontFile()
            self.i_externSettings.setText(
                '{"图层名称":["F.Cu","F.SilkS"],"绘制模式":["描边","填充","描边+填充"],"描边厚度":[0.2, 0.8, 0.5]}'
            )
            self.setting_method.setCurrentIndex(0)
            self.setting_scale.setValue(2.2)
            self.setting_precision.setValue(16)
            self.setting_space.setValue(1.2)
            self.i_sourceText.setPlainText(re.sub(r"([^ ^\n\S])", r"  ", text_demo1))

        def onUpdateText(self, text):
            """Write console output to text widget."""
            if len(text) < 1:
                ntext = "<br />"
            else:
                ntext = text

            if text.find("background-color:#f0e05e") > 0:  # logger的输出里有空格, 为了显示原始格式需要HTML空格转义
                ntext = ""
                tlen = len(text)
                for item in range(tlen):
                    if item < 54 or item > tlen - 13 or text[item] != " ":
                        ntext += text[item]
                    else:
                        ntext += "&nbsp;"
            cursor = self.o_Console.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.insertHtml(ntext)
            # 自动滚屏
            self.o_Console.setTextCursor(cursor)
            self.o_Console.ensureCursorVisible()

        def closeEvent(self, event):
            """Shuts down application on close."""
            # Return stdout to defaults.
            logConsole.info("*****窗口被关闭, 开始退出流程...*****")
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            if self.userFont is not None:
                self.userFont.fontObject.close()
            super().closeEvent(event)

        def copyData(self):
            if len(self.outputBuff) < 55:
                printc("还没有任何可写入的内容. ")
                res = setClip("喵喵喵~")
                if res.find("成功") > -1:
                    printc("清空剪贴板成功")
            else:
                res = setClip(str(self.outputBuff))
                if res.find("成功") > -1:
                    printc(res + " -- 请尽快到KiCAD5的pcbnew窗口中粘贴.")

        def clearConsole(self):
            self.o_Console.clear()
            printc("-" * 5 + f"于{time.strftime('%H:%m:%d', time.localtime(time.time()))}清屏" + "-" * 5,
                   style="color:#655366")

        def checkFontFile(self, fileName=None):
            if fileName is None:
                file = self.i_fontfileName.text()
                if file == "":
                    file = 'sarasa-monoT-sc-regular.ttf'
            else:
                file = fileName
            if self.userFont is not None:
                self.userFont.fontObject.close()
                self.userFont = None
            try:
                self.userFont = TTFaction(file)
            except Exception as e:
                logConsole.error( ValueError(f"指定的字体文件无法打开. ({e})") )
                self.statusBar.showMessage(f"指定的字体文件无法打开. ({e})", 5000)
                printc("未能打开字体, 请检查并重试.")
                self.userFont = None

            if self.userFont is not None:
                hintText = self.userFont.fontObject.reader.file.name
                self.o_fftFileName_current.setText(hintText)
                try:
                    hintText = "当前字体字符尺寸: 空格" + str(TTFaction.getCharSize(self.userFont, " "))
                    hintText += "|小写英文" + str(TTFaction.getCharSize(self.userFont, "a"))
                    hintText += "|大写英文" + str(TTFaction.getCharSize(self.userFont, "A"))
                    hintText += "|中文" + str(TTFaction.getCharSize(self.userFont, "口"))
                    hintText += "|数字" + str(TTFaction.getCharSize(self.userFont, "1"))
                except Exception as e:
                    logRoot.error(f"字体信息测试失败: {e} . 请尝试规范的字体文件.")
                    self.o_fftFileName_current.setText(self.o_fftFileName_current.text()+"(异常)")
                    self.statusBar.showMessage("字体文件异常", 10000)
                self.statusBarLable.setText(hintText)

        def draw(self):
            self.clean()
            if self.userFont is None:
                logRoot.warning("未选择字体")
                self.checkFontFile()
                if self.userFont is None:  # 再尝试一次, 如果还没有能用的字体就取消操作.
                    # TODO: 增加备选字体
                    printc( ResourceWarning("没有选择字体文件, 请选择一个常规的ttf字体. 本次操作取消...") )
                    return -233
            time_start = time.perf_counter()
            self.userFont.draw(self.i_sourceText.toPlainText(),
                               self.setting_scale.value()*1e-2,
                               self.setting_precision.value(),
                               self.setting_space.value()*1e-2)
            renderData = self.userFont.generateData()
            externSetting_text = self.i_externSettings.text()
            if len(externSetting_text) > 8:
                try:
                    externSettings = json.loads(externSetting_text)
                    if type(externSettings) != dict:
                        raise ValueError(f"`{str(externSettings)}`不是json")
                    printc(f"图层名称: {externSettings.get('图层名称')}", style="color:#656565")
                    printc(f"绘制模式: {externSettings.get('绘制模式')}", style="color:#656565")
                    printc(f"描边厚度: {externSettings.get('描边厚度')}", style="color:#656565")

                except Exception as e:
                    logConsole.warning(ValueError(f"输入不符合规范({e}). 替换为默认参数..."))
                    externSettings = {}
            else:
                externSettings = {}

            绘制模式 = externSettings.get("绘制模式")
            if 绘制模式 is None:
                method = self.setting_method.currentText()
                if method == "默认":
                    externSettings["绘制模式"] = ["填充"]
            图层名称 = externSettings.get("图层名称")
            if 图层名称 is None:
                externSettings["图层名称"] = ["F.SilkS"]
            描边厚度 = externSettings.get("描边厚度")
            if 描边厚度 is None:
                externSettings["描边厚度"] = None

            data_KiCAD = DataPrinter(renderData, **externSettings)
            data_KiCAD.render_KiCAD()
            self.outputBuff = data_KiCAD.toText()
            time_end = time.perf_counter()
            self.copyData()
            print(f"处理了{len(renderData)}个符号, 耗时{_round((time_end - time_start) * 1e3)}毫秒<br />")
            self.statusBar.showMessage(f"处理了{len(renderData)}个符号, 耗时{_round((time_end - time_start) * 1e3)}毫秒", 3000)


    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    MWnd = MainWindow()

    MWnd.show()

    rc = app.exec_()
    sys.exit(rc)





