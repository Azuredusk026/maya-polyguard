# Maya PolyGuard

一个集 **自动化检查**、**安全修复** 与 **AI 智能建议** 于一体的 Maya 美术管线工具。

## 🚀 核心特性

- **数据驱动全量检查**：内置 26 项严格的工业级标准检查，全面覆盖：
  - **常规项** (历史记录、冻结变换、轴心居中、空组过滤等)
  - **命名规范** (数字后缀清理、重复命名检测、名称空间剥离等)
  - **网格拓扑** (Ngons/三角面、极点、非流形边、零面积/长度面边等)
  - **UV 审查** (缺失 UV、UV 范围越界、UV 边界相交检测等)
- **一键无损修复**：针对常规与命名错误提供自动化修复程序，**特别优化了蒙皮（Skinning）保护机制**，在清理历史时绝不破坏绑定资产。
- **AI 智能分析**：深度接入 LLM API，当检测到复杂拓扑或逻辑错误时，动态生成专业级的中文优化指导与性能评估。
- **生产级底层架构**：采用数据/逻辑分离设计，检查任务下放主线程+UI 异步刷新机制，大场景不卡死；底层自动识别并兼容 PySide2 (旧版) 与 PySide6 (新版)。
## 💻 环境要求

- **操作系统**：Windows / macOS / Linux
- **Maya 版本**：Maya 2022 及以上版本 (推荐 2022+)。*注：理论支持 Maya 2017+，但 2022 以下版本使用 Python 2，本工具未针对 Python 2 的字符串编码（特别是中文路径）进行深度测试。*
- **依赖库**：纯 Maya 原生 API 开发，**无需额外安装 `requests` 等第三方库**。支持 PySide2 与 PySide6 的自动识别切换。

## 📦 安装与详细使用说明

本工具采用纯 Python 脚本运行，无需复杂的插件安装。请按照以下步骤操作：

### 第一步：放置文件
将下载解压后的 `PolyGuard` 文件夹放入您的 Maya 本地脚本目录：
- **Windows**: `C:\Users\<您的用户名>\Documents\maya\scripts\`
- **macOS**: `~/Library/Preferences/Autodesk/maya/scripts/`

### Step 2: 在 Maya 中启动与配置 AI
1. 启动 Maya。
2. 点击界面右下角的 `{;}` 图标，或通过顶部菜单栏 **窗口 (Windows) -> 常规编辑器 (General Editors) -> 脚本编辑器 (Script Editor)** 打开。
3. 切换到下方的 **Python** 标签页。
4. 将以下代码完整复制进去，**替换您的真实 API Key**，全选并运行（小键盘 `Enter` 或 点击蓝色播放按钮 ▶️）：

```python
import maya.cmds as cmds
import sys

# ==========================================
# 1. 配置 AI 核心参数 (强制覆盖本地旧缓存)
# ==========================================
# 【必填】填入你的专属 API Key
cmds.optionVar(sv=("PolyGuard_AI_KEY", "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"))

# 【必填】代理或官方接口地址 (确保以 /v1/chat/completions 结尾)
cmds.optionVar(sv=("PolyGuard_AI_URL", "[https://tbnx.plus7.plus/v1/chat/completions](https://tbnx.plus7.plus/v1/chat/completions)"))

# 【必填】强制锁定使用 gpt-4o (此操作会覆写 Maya 历史缓存，杜绝 503 报错)
cmds.optionVar(sv=("PolyGuard_AI_MODEL", "gpt-4o"))

print("✅ PolyGuard AI 核心环境变量配置与覆盖完成！")

# ==========================================
# 2. 内存清理与插件启动
# ==========================================
# 强制清除旧模块缓存，防止代码更新后 Maya 读取死锁
modules_to_delete = [m for m in sys.modules if m.startswith('PolyGuard')]
for m in modules_to_delete:
    del sys.modules[m]

# 导入并启动 UI 主程序
try:
    import PolyGuard.PolyGuard_UI as pgUI
    pgUI.UI.show_UI()
    print("✅ PolyGuard 启动成功！")
except ModuleNotFoundError as e:
    cmds.error(f"启动失败！请检查文件夹命名是否严格为 'PolyGuard'，且位于正确的 scripts 目录下。详情: {e}")