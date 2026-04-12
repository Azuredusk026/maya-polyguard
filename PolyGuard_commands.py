from collections import defaultdict
import maya.cmds as cmds
import maya.api.OpenMaya as om

def _getNodeName(uuid):
    nodeName = cmds.ls(uuid, uuid=True)
    return nodeName[0] if nodeName else None

# --- 精确的轴心检查 ---
def uncenteredPivots(nodes, _):
    """检查轴心是否偏离了物体的几何中心(Bounding Box Center)"""
    invalid = []
    for n in nodes:
        name = _getNodeName(n)
        if not name: continue
        # 获取旋转轴心位置
        pivot = cmds.xform(name, q=True, ws=True, rp=True)
        # 获取包围盒中心
        bbox = cmds.exactWorldBoundingBox(name)
        center = [(bbox[0] + bbox[3]) / 2, (bbox[1] + bbox[4]) / 2, (bbox[2] + bbox[5]) / 2]
        
        # 允许极小的浮点误差
        dist = sum((p - c) ** 2 for p, c in zip(pivot, center)) ** 0.5
        if dist > 0.001:
            invalid.append(n)
    return "nodes", invalid

# --- 其他检查函数保持之前的优化版本 ---
def trailingNumbers(nodes, _):
    invalid = [n for n in nodes if _getNodeName(n) and _getNodeName(n)[-1].isdigit()]
    return "nodes", invalid

def duplicatedNames(nodes, _):
    nodesByShortName = defaultdict(list)
    for node in nodes:
        name = _getNodeName(node).rsplit('|', 1)[-1]
        nodesByShortName[name].append(node)
    invalid = [n for short_nodes in nodesByShortName.values() if len(short_nodes) > 1 for n in short_nodes]
    return "nodes", invalid

def namespaces(nodes, _):
    invalid = [n for n in nodes if _getNodeName(n) and ':' in _getNodeName(n)]
    return "nodes", invalid

def shapeNames(nodes, _):
    invalid = []
    for node in nodes:
        nodeName = _getNodeName(node)
        if nodeName:
            shapes = cmds.listRelatives(nodeName, shapes=True)
            if shapes and shapes[0] != nodeName.split('|')[-1] + "Shape":
                invalid.append(node)
    return "nodes", invalid

def triangles(_, SLMesh):
    triangles = defaultdict(list)
    selIt = om.MItSelectionList(SLMesh)
    while not selIt.isDone():
        faceIt = om.MItMeshPolygon(selIt.getDagPath())
        uuid = om.MFnDependencyNode(selIt.getDagPath().node()).uuid().asString()
        while not faceIt.isDone():
            if faceIt.getEdges().length() == 3: triangles[uuid].append(faceIt.index())
            faceIt.next()
        selIt.next()
    return "polygon", triangles

def ngons(_, SLMesh):
    ngons = defaultdict(list)
    selIt = om.MItSelectionList(SLMesh)
    while not selIt.isDone():
        faceIt = om.MItMeshPolygon(selIt.getDagPath())
        uuid = om.MFnDependencyNode(selIt.getDagPath().node()).uuid().asString()
        while not faceIt.isDone():
            if faceIt.getEdges().length() > 4: ngons[uuid].append(faceIt.index())
            faceIt.next()
        selIt.next()
    return "polygon", ngons

def hardEdges(_, SLMesh):
    hardEdges = defaultdict(list)
    selIt = om.MItSelectionList(SLMesh)
    while not selIt.isDone():
        edgeIt = om.MItMeshEdge(selIt.getDagPath())
        uuid = om.MFnDependencyNode(selIt.getDagPath().node()).uuid().asString()
        while not edgeIt.isDone():
            if not edgeIt.isSmooth and not edgeIt.onBoundary(): hardEdges[uuid].append(edgeIt.index())
            edgeIt.next()
        selIt.next()
    return "edge", hardEdges

def lamina(_, SLMesh):
    lamina = defaultdict(list)
    selIt = om.MItSelectionList(SLMesh)
    while not selIt.isDone():
        faceIt = om.MItMeshPolygon(selIt.getDagPath())
        uuid = om.MFnDependencyNode(selIt.getDagPath().node()).uuid().asString()
        while not faceIt.isDone():
            if faceIt.isLamina(): lamina[uuid].append(faceIt.index())
            faceIt.next()
        selIt.next()
    return "polygon", lamina

def zeroAreaFaces(_, SLMesh):
    zeroAreaFaces = defaultdict(list)
    selIt = om.MItSelectionList(SLMesh)
    while not selIt.isDone():
        faceIt = om.MItMeshPolygon(selIt.getDagPath())
        uuid = om.MFnDependencyNode(selIt.getDagPath().node()).uuid().asString()
        while not faceIt.isDone():
            if faceIt.getArea() <= 1e-8: zeroAreaFaces[uuid].append(faceIt.index())
            faceIt.next()
        selIt.next()
    return "polygon", zeroAreaFaces

def zeroLengthEdges(_, SLMesh):
    zeroLengthEdges = defaultdict(list)
    selIt = om.MItSelectionList(SLMesh)
    while not selIt.isDone():
        edgeIt = om.MItMeshEdge(selIt.getDagPath())
        uuid = om.MFnDependencyNode(selIt.getDagPath().node()).uuid().asString()
        while not edgeIt.isDone():
            if edgeIt.length() <= 1e-8: zeroLengthEdges[uuid].append(edgeIt.index())
            edgeIt.next()
        selIt.next()
    return "edge", zeroLengthEdges

def selfPenetratingUVs(nodes, _):
    invalid = defaultdict(list)
    for node in nodes:
        name = _getNodeName(node)
        shapes = cmds.listRelatives(name, shapes=True, type="mesh", noIntermediate=True)
        if shapes:
            overlapping = cmds.polyUVOverlap("{}.f[*]".format(shapes[0]), oc=True)
            if overlapping:
                invalid[node] = [o.split(".f[")[-1][:-1] for o in overlapping]
    return "polygon", invalid

def noneManifoldEdges(_, SLMesh):
    invalid = defaultdict(list)
    selIt = om.MItSelectionList(SLMesh)
    while not selIt.isDone():
        edgeIt = om.MItMeshEdge(selIt.getDagPath())
        uuid = om.MFnDependencyNode(selIt.getDagPath().node()).uuid().asString()
        while not edgeIt.isDone():
            if edgeIt.numConnectedFaces() > 2: invalid[uuid].append(edgeIt.index())
            edgeIt.next()
        selIt.next()
    return "edge", invalid

def openEdges(_, SLMesh):
    invalid = defaultdict(list)
    selIt = om.MItSelectionList(SLMesh)
    while not selIt.isDone():
        edgeIt = om.MItMeshEdge(selIt.getDagPath())
        uuid = om.MFnDependencyNode(selIt.getDagPath().node()).uuid().asString()
        while not edgeIt.isDone():
            if edgeIt.numConnectedFaces() < 2: invalid[uuid].append(edgeIt.index())
            edgeIt.next()
        selIt.next()
    return "edge", invalid

def poles(_, SLMesh):
    invalid = defaultdict(list)
    selIt = om.MItSelectionList(SLMesh)
    while not selIt.isDone():
        vertexIt = om.MItMeshVertex(selIt.getDagPath())
        uuid = om.MFnDependencyNode(selIt.getDagPath().node()).uuid().asString()
        while not vertexIt.isDone():
            if vertexIt.numConnectedEdges() > 5: invalid[uuid].append(vertexIt.index())
            vertexIt.next()
        selIt.next()
    return "vertex", invalid

def starlike(_, SLMesh):
    invalid = defaultdict(list)
    selIt = om.MItSelectionList(SLMesh)
    while not selIt.isDone():
        polyIt = om.MItMeshPolygon(selIt.getDagPath())
        uuid = om.MFnDependencyNode(selIt.getDagPath().node()).uuid().asString()
        while not polyIt.isDone():
            if not polyIt.isStarlike(): invalid[uuid].append(polyIt.index())
            polyIt.next()
        selIt.next()
    return "polygon", invalid

def missingUVs(_, SLMesh):
    invalid = defaultdict(list)
    selIt = om.MItSelectionList(SLMesh)
    while not selIt.isDone():
        faceIt = om.MItMeshPolygon(selIt.getDagPath())
        uuid = om.MFnDependencyNode(selIt.getDagPath().node()).uuid().asString()
        while not faceIt.isDone():
            if not faceIt.hasUVs(): invalid[uuid].append(faceIt.index())
            faceIt.next()
        selIt.next()
    return "polygon", invalid

def uvRange(_, SLMesh):
    invalid = defaultdict(list)
    selIt = om.MItSelectionList(SLMesh)
    while not selIt.isDone():
        mesh = om.MFnMesh(selIt.getDagPath())
        uuid = om.MFnDependencyNode(selIt.getDagPath().node()).uuid().asString()
        Us, Vs = mesh.getUVs()
        invalid[uuid] = [i for i in range(len(Us)) if Us[i] < 0 or Us[i] > 10 or Vs[i] < 0]
        selIt.next()
    return "uv", invalid

def onBorder(_, SLMesh):
    invalid = defaultdict(list)
    selIt = om.MItSelectionList(SLMesh)
    while not selIt.isDone():
        mesh = om.MFnMesh(selIt.getDagPath())
        uuid = om.MFnDependencyNode(selIt.getDagPath().node()).uuid().asString()
        Us, Vs = mesh.getUVs()
        invalid[uuid] = [i for i in range(len(Us)) if abs(int(Us[i])-Us[i]) < 1e-5 or abs(int(Vs[i])-Vs[i]) < 1e-5]
        selIt.next()
    return "uv", invalid

def crossBorder(_, SLMesh):
    invalid = defaultdict(list)
    selIt = om.MItSelectionList(SLMesh)
    while not selIt.isDone():
        faceIt = om.MItMeshPolygon(selIt.getDagPath())
        uuid = om.MFnDependencyNode(selIt.getDagPath().node()).uuid().asString()
        while not faceIt.isDone():
            try:
                Us, Vs = faceIt.getUVs()
                U_bins = set(int(u) if u > 0 else int(u)-1 for u in Us)
                V_bins = set(int(v) if v > 0 else int(v)-1 for v in Vs)
                if len(U_bins) > 1 or len(V_bins) > 1: invalid[uuid].append(faceIt.index())
            except: pass
            faceIt.next()
        selIt.next()
    return "polygon", invalid

def unfrozenTransforms(nodes, _):
    invalid = []
    for n in nodes:
        name = _getNodeName(n)
        if name:
            t = cmds.xform(name, q=1, ws=1, t=1)
            r = cmds.xform(name, q=1, ws=1, ro=1)
            s = cmds.xform(name, q=1, ws=1, s=1)
            if t != [0.0,0.0,0.0] or r != [0.0,0.0,0.0] or s != [1.0,1.0,1.0]: invalid.append(n)
    return "nodes", invalid

def layers(nodes, _):
    invalid = [n for n in nodes if cmds.listConnections(_getNodeName(n), type="displayLayer")]
    return "nodes", invalid

def shaders(nodes, _):
    invalid = []
    for n in nodes:
        name = _getNodeName(n)
        shape = cmds.listRelatives(name, s=True, f=True)
        if shape and cmds.nodeType(shape[0]) == 'mesh':
            sg = cmds.listConnections(shape[0], type='shadingEngine')
            if sg and sg[0] != 'initialShadingGroup': invalid.append(n)
    return "nodes", invalid

def history(nodes, _):
    invalid = []
    for n in nodes:
        name = _getNodeName(n)
        shape = cmds.listRelatives(name, s=True, f=True)
        if shape and cmds.nodeType(shape[0]) == 'mesh':
            if len(cmds.listHistory(shape[0])) > 1: invalid.append(n)
    return "nodes", invalid

def emptyGroups(nodes, _):
    invalid = []
    for node in nodes:
        name = _getNodeName(node)
        if not name: continue
        if not cmds.listRelatives(name, ad=True):
            if not cmds.listRelatives(name, s=True) and cmds.nodeType(name) != 'joint':
                invalid.append(node)
    return "nodes", invalid

def parentGeometry(nodes, _):
    invalid = []
    for n in nodes:
        name = _getNodeName(n)
        parents = cmds.listRelatives(name, p=True, f=True)
        if parents:
            if any(cmds.nodeType(c) == 'mesh' for c in cmds.listRelatives(parents[0], f=True)): invalid.append(n)
    return "nodes", invalid
