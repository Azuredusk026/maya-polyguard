import maya.cmds as cmds

def _getNodeName(uuid):
    nodeName = cmds.ls(uuid, uuid=True)
    return nodeName[0] if nodeName else None

def trailingNumbers(errors):
    """尝试移除数字后缀，若发生命名冲突则跳过并警告用户。"""
    for u in errors:
        node = _getNodeName(u)
        if not node: continue
        
        target_name = node.rstrip('0123456789')
        if target_name == node: continue
        
        # 检查目标名称是否已被占用
        if cmds.objExists(target_name):
            cmds.warning("无法修复 {}: 目标名称 '{}' 已存在，请手动命名以解决冲突。".format(node, target_name))
            continue
            
        try:
            cmds.rename(node, target_name)
        except Exception as e:
            cmds.warning("重命名 {} 失败: {}".format(node, str(e)))

def history(errors):
    """SAFE FIX: 仅烘焙非变形历史，保留蒙皮。"""
    for u in errors:
        node = _getNodeName(u)
        if node:
            cmds.bakePartialHistory(node, prePostDeformers=True)

def uncenteredPivots(errors):
    """将轴心移动到几何体中心。"""
    for u in errors:
        node = _getNodeName(u)
        if node:
            cmds.xform(node, cp=True)

# --- 其余修复函数保持不变 ---
def namespaces(errors):
    for u in errors:
        node = _getNodeName(u); 
        if node and ":" in node: cmds.rename(node, node.split(":")[-1])

def unfrozenTransforms(errors):
    for u in errors:
        node = _getNodeName(u); 
        if node: cmds.makeIdentity(node, apply=True, t=1, r=1, s=1, n=0)

def emptyGroups(errors):
    for u in errors:
        node = _getNodeName(u); 
        if node: cmds.delete(node)

def lamina(errors):
    for u in errors:
        node = _getNodeName(u); 
        if node: cmds.polyCleanupArg(node, lmn=True)

def noneManifoldEdges(errors):
    for u in errors:
        node = _getNodeName(u); 
        if node: cmds.polyCleanupArg(node, nmf=True)

def zeroAreaFaces(errors):
    for u in errors:
        node = _getNodeName(u); 
        if node: cmds.polyCleanupArg(node, fza=True)

def zeroLengthEdges(errors):
    for u in errors:
        node = _getNodeName(u); 
        if node: cmds.polyCleanupArg(node, ezl=True)

def shaders(errors):
    for u in errors:
        node = _getNodeName(u); 
        if node: cmds.sets(node, e=True, forceElement='initialShadingGroup')

def layers(errors):
    for u in errors:
        node = _getNodeName(u); 
        if node:
            try: cmds.disconnectAttr(node + ".drawOverride")
            except: pass

def shapeNames(errors):
    for u in errors:
        node = _getNodeName(u); 
        if node:
            shapes = cmds.listRelatives(node, s=True)
            if shapes: cmds.rename(shapes[0], node + "Shape")

def default_fix(errors):
    cmds.warning("此项暂不支持自动修复，请根据 AI 建议手动处理。")
