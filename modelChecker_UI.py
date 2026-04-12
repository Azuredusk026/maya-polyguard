import os
import json
import traceback
from functools import partial

try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from shiboken6 import wrapInstance
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
    from shiboken2 import wrapInstance

import maya.cmds as cmds
import maya.OpenMayaUI as omui
import maya.api.OpenMaya as om

import PolyGuard.PolyGuard_commands as mcc
import PolyGuard.PolyGuard_fix_commands as mcf
from PolyGuard.ai_handler import AIHandler
from PolyGuard.__version__ import __version__

class AIThread(QtCore.QThread):
    aiFinished = QtCore.Signal(str)
    def __init__(self, summary, parent=None):
        super(AIThread, self).__init__(parent)
        self.summary = summary
    def run(self):
        try:
            advice = AIHandler.analyze_errors(self.summary)
            self.aiFinished.emit(advice)
        except Exception as e:
            self.aiFinished.emit("AI Error: " + str(e))

class UI(QtWidgets.QMainWindow):
    qmwInstance = None
    
    DEFAULT_RULES = {
        "trailingNumbers": {"label": "数字后缀", "category": "2 - 命名"},
        "duplicatedNames": {"label": "复制的名称", "category": "2 - 命名"},
        "shapeNames": {"label": "Shape名称", "category": "2 - 命名"},
        "namespaces": {"label": "名称空间", "category": "2 - 命名"},
        "layers": {"label": "层", "category": "1 - 常规"},
        "history": {"label": "历史", "category": "1 - 常规"},
        "shaders": {"label": "材质", "category": "1 - 常规"},
        "unfrozenTransforms": {"label": "未冻结的变换", "category": "1 - 常规"},
        "uncenteredPivots": {"label": "未居中的轴心", "category": "1 - 常规"},
        "parentGeometry": {"label": "父级几何体", "category": "1 - 常规"},
        "emptyGroups": {"label": "空组", "category": "1 - 常规"},
        "triangles": {"label": "三角面", "category": "3 - 网格拓扑"},
        "ngons": {"label": "多边形面(Ngons)", "category": "3 - 网格拓扑"},
        "openEdges": {"label": "开放的边", "category": "3 - 网格拓扑"},
        "poles": {"label": "极点（Poles）", "category": "3 - 网格拓扑"},
        "hardEdges": {"label": "硬边", "category": "3 - 网格拓扑"},
        "lamina": {"label": "Lamina", "category": "3 - 网格拓扑"},
        "zeroAreaFaces": {"label": "0面积的面", "category": "3 - 网格拓扑"},
        "zeroLengthEdges": {"label": "0长度的边", "category": "3 - 网格拓扑"},
        "noneManifoldEdges": {"label": "非流形边", "category": "3 - 网格拓扑"},
        "starlike": {"label": "星形点", "category": "3 - 网格拓扑"},
        "selfPenetratingUVs": {"label": "重叠的UVs", "category": "4 - UVs"},
        "missingUVs": {"label": "缺失的UVs", "category": "4 - UVs"},
        "uvRange": {"label": "UV范围", "category": "4 - UVs"},
        "crossBorder": {"label": "跨界的UVs", "category": "4 - UVs"},
        "onBorder": {"label": "在边界上的UVs", "category": "4 - UVs"}
    }

    def __init__(self, parent=None):
        if parent is None:
            ptr = omui.MQtUtil.mainWindow()
            parent = wrapInstance(int(ptr), QtWidgets.QWidget) if ptr else None
        super(UI, self).__init__(parent)
        self.setObjectName("PolyGuardUI")
        self.setWindowTitle("PolyGuard " + __version__)
        self.commandsList = self.loadRulesConfig()
        
        self.categoryWidget, self.categoryLayout, self.categoryCollapse = {}, {}, {}
        self.commandWidget, self.commandLayout, self.commandLabel = {}, {}, {}
        self.commandCheckBox, self.errorNodesButton = {}, {}
        self.commandRunButton, self.commandFixButton = {}, {}
        
        self.diagnostics = {}
        self.currentContextUUID = "Global"
        self.contexts = {
            "Global": {"name": "全局", "diagnostics": {}, "nodes": []},
        }

        mainWidget = QtWidgets.QWidget(self); self.setCentralWidget(mainWidget)
        mainLayout = QtWidgets.QVBoxLayout(mainWidget)
        self.mainSplitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        lPanel, rPanel = QtWidgets.QWidget(), QtWidgets.QWidget()
        lPanel.setLayout(self.buildChecksList()); rPanel.setLayout(self.buildContextUI())
        self.mainSplitter.addWidget(lPanel); self.mainSplitter.addWidget(rPanel)
        self.mainSplitter.setStretchFactor(0, 1); self.mainSplitter.setStretchFactor(1, 2)
        mainLayout.addWidget(self.mainSplitter)
        self.resize(1200, 900); self.createReport("Global")
        self.consolidatedCheck.stateChanged.connect(self.changeConsolidated)

    def loadRulesConfig(self):
        try:
            p = os.path.join(os.path.dirname(__file__), "rules_config.json")
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    if d: return d
        except: pass
        return self.DEFAULT_RULES

    def getCategories(self, commands): return sorted(list(set(c['category'] for c in commands.values())))

    @classmethod
    def show_UI(cls):
        if not cls.qmwInstance: cls.qmwInstance = UI()
        if cls.qmwInstance.isHidden(): cls.qmwInstance.show()
        else: cls.qmwInstance.raise_(); cls.qmwInstance.activateWindow()

    def buildContextUI(self):
        layout = QtWidgets.QVBoxLayout()
        ctxTableWidget = QtWidgets.QWidget(); ctxLayout = QtWidgets.QVBoxLayout(ctxTableWidget)
        self.contextTable = QtWidgets.QTableWidget(); ctxLayout.addWidget(self.contextTable)
        btnL = QtWidgets.QHBoxLayout(); addBtn, remBtn = QtWidgets.QPushButton("Add Context"), QtWidgets.QPushButton("Remove Selected")
        addBtn.clicked.connect(self.addSelectedNodesAsNewContexts); remBtn.clicked.connect(self.removeSelectedContexts)
        btnL.addWidget(addBtn); btnL.addWidget(remBtn); ctxLayout.addLayout(btnL)

        self.contextTable.setColumnCount(4); self.contextTable.setHorizontalHeaderLabels(['UUID', 'CONTEXT', 'NODES', 'STATUS'])
        self.contextTable.verticalHeader().setVisible(False); self.contextTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.contextTable.cellClicked.connect(self.setCurrentContext); self.contextTable.setColumnHidden(0, True); self.contextTable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        for idx, c in enumerate(["Global"]):
            uI, cI, nI, sI = QtWidgets.QTableWidgetItem(c), QtWidgets.QTableWidgetItem(c), QtWidgets.QTableWidgetItem("0"), QtWidgets.QTableWidgetItem("Ready")
            self.contexts[c]['tableItem'] = uI; self.contextTable.insertRow(idx)
            self.contextTable.setItem(idx, 0, uI); self.contextTable.setItem(idx, 1, cI); self.contextTable.setItem(idx, 2, nI); self.contextTable.setItem(idx, 3, sI)

        self.reportOutputUI = QtWidgets.QTextEdit(); self.reportOutputUI.setReadOnly(True)
        aiCont = QtWidgets.QWidget(); aiL = QtWidgets.QVBoxLayout(aiCont)
        aiL.addWidget(QtWidgets.QLabel("<b>AI Optimization Advice</b>"))
        self.aiAdviceUI = QtWidgets.QTextEdit(); self.aiAdviceUI.setReadOnly(True); self.aiAdviceUI.setMaximumHeight(180); aiL.addWidget(self.aiAdviceUI)
        aiAct = QtWidgets.QHBoxLayout(); self.aiRunBtn = QtWidgets.QPushButton("AI 智能分析报告"); self.aiRunBtn.clicked.connect(self.runAIAnalysis); aiAct.addStretch(); aiAct.addWidget(self.aiRunBtn); aiL.addLayout(aiAct)

        runL = QtWidgets.QHBoxLayout(); self.consolidatedCheck = QtWidgets.QCheckBox("综合显示")
        clrBtn, self.runAllBtn, self.fixAllBtn = QtWidgets.QPushButton("清理"), QtWidgets.QPushButton("运行所选"), QtWidgets.QPushButton("✨ 全局修复")
        self.fixAllBtn.setStyleSheet("background-color: #2e5a88; font-weight: bold;")
        clrBtn.clicked.connect(self.clearCurrentReport); self.runAllBtn.clicked.connect(self.sanityCheckChecked); self.fixAllBtn.clicked.connect(self.fixAllErrorsInContext)
        runL.addWidget(self.consolidatedCheck); runL.addStretch(); runL.addWidget(clrBtn); runL.addWidget(self.runAllBtn); runL.addWidget(self.fixAllBtn)

        split = QtWidgets.QSplitter(QtCore.Qt.Vertical); split.addWidget(ctxTableWidget); split.addWidget(self.reportOutputUI); split.addWidget(aiCont)
        split.setStretchFactor(0, 2); split.setStretchFactor(1, 4); split.setStretchFactor(2, 2)
        layout.addWidget(split); layout.addLayout(runL)
        return layout

    def buildChecksList(self):
        layout = QtWidgets.QVBoxLayout(); scroll = QtWidgets.QScrollArea(); scroll.setWidgetResizable(True)
        cont = QtWidgets.QWidget(); scL = QtWidgets.QVBoxLayout(cont)
        for obj in self.getCategories(self.commandsList):
            self.categoryWidget[obj], self.categoryLayout[obj] = QtWidgets.QWidget(), QtWidgets.QVBoxLayout()
            header = QtWidgets.QHBoxLayout(); btn = QtWidgets.QPushButton(obj); btn.setStyleSheet("background-color: #444; color: white; font-weight: bold;")
            btn.clicked.connect(partial(self.checkCategory, obj)); coll = QtWidgets.QPushButton(u'\u2193'); coll.setMaximumWidth(30)
            coll.clicked.connect(partial(self.toggleUI, obj)); header.addWidget(btn); header.addWidget(coll)
            self.categoryWidget[obj].setLayout(self.categoryLayout[obj]); self.categoryCollapse[obj] = coll
            scL.addLayout(header); scL.addWidget(self.categoryWidget[obj])

        for name in sorted(self.commandsList.keys()):
            l, cat = self.commandsList[name]['label'], self.commandsList[name]['category']
            itW = QtWidgets.QWidget(); itL = QtWidgets.QHBoxLayout(itW); itL.setContentsMargins(5, 2, 5, 2)
            self.commandCheckBox[name] = QtWidgets.QCheckBox(); self.commandLabel[name] = QtWidgets.QLabel(l); self.commandLabel[name].setMinimumWidth(120)
            rB, fB, eB = QtWidgets.QPushButton("▶"), QtWidgets.QPushButton("🛠"), QtWidgets.QPushButton("🔍")
            for b in [rB, fB, eB]: b.setMaximumWidth(30)
            rB.clicked.connect(partial(self.runOneCheck, name)); fB.clicked.connect(partial(self.fixOneItem, name)); eB.clicked.connect(partial(self.selectErrorNodesForCommand, name))
            self.commandRunButton[name], self.commandFixButton[name], self.errorNodesButton[name] = rB, fB, eB
            fB.setEnabled(False); eB.setEnabled(False); itL.addWidget(self.commandCheckBox[name]); itL.addWidget(self.commandLabel[name])
            itL.addStretch(); itL.addWidget(rB); itL.addWidget(fB); itL.addWidget(eB)
            self.categoryLayout[cat].addWidget(itW); self.commandWidget[name] = itW

        scL.addStretch(); scroll.setWidget(cont); layout.addWidget(scroll)
        btnL = QtWidgets.QHBoxLayout(); allB, noneB = QtWidgets.QPushButton("全选"), QtWidgets.QPushButton("全不选")
        allB.clicked.connect(self.checkAll); noneB.clicked.connect(self.uncheckAll); btnL.addWidget(allB); btnL.addWidget(noneB); layout.addLayout(btnL)
        return layout

    def sanityCheckChecked(self):
        checked = [n for n in self.commandsList if self.commandCheckBox[n].isChecked()]
        if not checked: return
        
        if self.currentContextUUID == "Global": nodes = self.filterGetAllNodes()
        else: nodes = self.contexts[self.currentContextUUID].get('nodes', [])
        
        if not nodes: return
        self.runAllBtn.setEnabled(False); self.statusUpdate(self.currentContextUUID, "Running...")
        try:
            SLMesh = om.MSelectionList(); valid = [n for n in nodes if cmds.ls(n)]
            for n in valid:
                try:
                    s = cmds.listRelatives(cmds.ls(n)[0], s=True, typ="mesh")
                    if s: SLMesh.add(n)
                except: continue
            diag = {}
            for c in checked:
                if hasattr(mcc, c):
                    self.statusUpdate(self.currentContextUUID, "Checking {}...".format(c)); QtWidgets.QApplication.processEvents()
                    t, e = getattr(mcc, c)(valid, SLMesh); diag[c] = {"type": t, "uuids": e}
            self.contexts[self.currentContextUUID]['nodes'] = valid
            self.contexts[self.currentContextUUID]['diagnostics'].update(diag)
            self.statusUpdate(self.currentContextUUID, "Done")
        except Exception as e:
            self.statusUpdate(self.currentContextUUID, "Error!"); self.reportOutputUI.setHtml("<font color=red>{}</font>".format(str(e)))
        finally:
            self.runAllBtn.setEnabled(True); self.createReport(self.currentContextUUID); self.updateTableAppearance(self.currentContextUUID)

    def updateTableAppearance(self, uuid):
        ctx = self.contexts.get(uuid)
        if not ctx: return
        d = ctx['diagnostics']; fails = sum(1 for x in d.values() if x['uuids']); it = ctx.get('tableItem')
        if it:
            row = self.contextTable.row(it); color = QtGui.QColor(120, 60, 60) if fails > 0 else QtGui.QColor(60, 120, 60)
            for c in range(4): self.contextTable.item(row, c).setBackground(QtGui.QBrush(color))
            self.contextTable.item(row, 2).setText(str(len(ctx.get('nodes', []))))
            if fails > 0: self.contextTable.item(row, 3).setText("Found {} Errors".format(fails))
            else: self.contextTable.item(row, 3).setText("Clean")

    def runAIAnalysis(self):
        if hasattr(self, 'aiThread') and self.aiThread.isRunning(): return
        diags = self.contexts[self.currentContextUUID]['diagnostics']
        failed_ids = [rid for rid, data in diags.items() if (sum(len(ids) for ids in data['uuids'].values()) if isinstance(data['uuids'], dict) else len(data['uuids'])) > 0]
        self.aiAdviceUI.setHtml("<i style='color:#888;'>深度分析当前检查项中，请稍候...</i>"); self.aiRunBtn.setEnabled(False)
        self.aiThread = AIThread(",".join(failed_ids) if failed_ids else "NoErrors")
        self.aiThread.aiFinished.connect(lambda html: [self.aiAdviceUI.setHtml(html), self.aiRunBtn.setEnabled(True)]); self.aiThread.start()

    def runOneCheck(self, c):
        for n in self.commandsList: self.commandCheckBox[n].setChecked(n == c)
        self.sanityCheckChecked()

    def fixOneItem(self, c):
        diag = self.contexts[self.currentContextUUID]['diagnostics'].get(c)
        if not diag or not diag['uuids']: return
        try:
            f = getattr(mcf, c, mcf.default_fix); errs = list(diag['uuids'].keys()) if isinstance(diag['uuids'], dict) else diag['uuids']
            f(errs); cmds.refresh(); self.runOneCheck(c)
        except Exception as e: cmds.warning("Fix Error: " + str(e))

    def fixAllErrorsInContext(self):
        for c, d in self.contexts[self.currentContextUUID]['diagnostics'].items():
            if d['uuids']: self.fixOneItem(c); QtWidgets.QApplication.processEvents()
        cmds.inViewMessage(amg="Global Fix Complete!", pos='midCenter', fade=True)

    def createReport(self, uuid):
        ctx = self.contexts.get(uuid)
        if not ctx: return
        diags, html = ctx['diagnostics'], "<h2>Report: {}</h2>".format(ctx['name'])
        for c in sorted(self.commandsList.keys()):
            if c not in diags:
                self.commandLabel[c].setStyleSheet(""); self.commandFixButton[c].setEnabled(False); self.errorNodesButton[c].setEnabled(False); continue
            errs = self.parseErrors(diags[c]); isF = len(errs) > 0; self.commandLabel[c].setStyleSheet("background-color: {}; color: white; border-radius: 3px;".format("#844" if isF else "#484"))
            self.commandFixButton[c].setEnabled(isF); self.errorNodesButton[c].setEnabled(isF)
            html += "<b>{}</b>: {} ({} errors)<br>".format(self.commandsList[c]['label'], "<font color=#ff6666>[ FAIL ]</font>" if isF else "<font color=#66ff66>[ PASS ]</font>", len(errs))
            if isF and not self.consolidatedCheck.isChecked():
                for e in errs[:10]: html += "&nbsp;&nbsp;└─ {}<br>".format(e)
                if len(errs) > 10: html += "&nbsp;&nbsp;...<br>"
        self.reportOutputUI.setHtml(html)

    def parseErrors(self, data):
        uuids = data['uuids']
        if not uuids: return []
        if data['type'] == 'nodes': return [cmds.ls(u)[0] for u in uuids if cmds.ls(u)]
        suffix = {"uv": ".map[{}]", "vertex": ".vtx[{}]", "edge": ".e[{}]", "polygon": ".f[{}]"}.get(data['type'], "[{}]")
        out = []
        for u, ids in uuids.items():
            name = cmds.ls(u)
            if name: 
                for i in ids: out.append(name[0] + suffix.format(i))
        return out

    def filterGetAllNodes(self): return [cmds.ls(n, uuid=True)[0] for n in cmds.ls(transforms=True, long=True) if n not in {'|front', '|persp', '|top', '|side'}]
    def selectHierachy(self, uuids):
        found = set()
        for u in uuids:
            names = cmds.ls(u, long=True); found.add(u); children = cmds.listRelatives(names[0], ad=True, typ='transform', f=True)
            if children:
                for c in children: found.add(cmds.ls(c, uuid=True)[0])
        return list(found)
    def statusUpdate(self, uuid, text):
        it = self.contexts.get(uuid, {}).get('tableItem')
        if it: self.contextTable.item(self.contextTable.row(it), 3).setText(text)
    def selectErrorNodesForCommand(self, c):
        diag = self.contexts[self.currentContextUUID]['diagnostics'].get(c)
        if diag: cmds.select(self.parseErrors(diag))
    def toggleUI(self, cat):
        vis = not self.categoryWidget[cat].isVisible(); self.categoryWidget[cat].setVisible(vis); self.categoryCollapse[cat].setText(u'\u2193' if vis else u'\u21B5')
    def checkAll(self):
        for cb in self.commandCheckBox.values(): cb.setChecked(True)
    def uncheckAll(self):
        for cb in self.commandCheckBox.values(): cb.setChecked(False)
    def selectFailed(self):
        d = self.contexts[self.currentContextUUID]['diagnostics']
        for n in self.commandsList: self.commandCheckBox[n].setChecked(n in d and bool(d[n]['uuids']))
    def checkCategory(self, cat):
        its = [n for n, d in self.commandsList.items() if d['category'] == cat]; all_c = all(self.commandCheckBox[i].isChecked() for i in its)
        for i in its: self.commandCheckBox[i].setChecked(not all_c)
    def clearCurrentReport(self): self.contexts[self.currentContextUUID]['diagnostics'] = {}; self.createReport(self.currentContextUUID)
    def setCurrentContext(self, row, col):
        it = self.contextTable.item(row, 0)
        if it: self.currentContextUUID = it.text(); self.createReport(self.currentContextUUID)
    def changeConsolidated(self): self.createReport(self.currentContextUUID)
    def addSelectedNodesAsNewContexts(self):
        for n in cmds.ls(sl=True): self.addNodeAsContext(n)
    def addNodeAsContext(self, node):
        try:
            u = cmds.ls(node, uuid=True)[0]; ns = self.selectHierachy([u]); r = self.contextTable.rowCount(); self.contextTable.insertRow(r)
            uI, cI, nI, sI = QtWidgets.QTableWidgetItem(u), QtWidgets.QTableWidgetItem(node), QtWidgets.QTableWidgetItem(str(len(ns))), QtWidgets.QTableWidgetItem("Ready")
            self.contexts[u] = {'name': node, 'diagnostics': {}, 'nodes': ns, 'tableItem': uI}
            self.contextTable.setItem(r, 0, uI); self.contextTable.setItem(r, 1, cI); self.contextTable.setItem(r, 2, nI); self.contextTable.setItem(r, 3, sI)
        except: pass
    def removeSelectedContexts(self):
        for idx in sorted(self.contextTable.selectionModel().selectedRows(), reverse=True):
            u = self.contextTable.item(idx.row(), 0).text()
            if u not in ["Global"]: self.contextTable.removeRow(idx.row()); self.contexts.pop(u)
    def saveSettings(self): pass
    def loadSettings(self): pass

if __name__ == '__main__':
    UI.show_UI()
