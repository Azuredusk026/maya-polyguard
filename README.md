# Maya PolyGuard

一个集 **自动化检查**、**安全修复** 与 **AI 智能建议** 于一体的 Maya 美术管线工具。

## 🚀 功能特性

- **数据驱动检查**：内置 26 项核心检查，包括命名、常规、拓扑、UV 四大维度。
- **一键安全修复**：针对可自动处理的问题提供修复方案，特别优化了蒙皮保护与命名冲突检测。
- **AI 智能分析**：接入 LLM API，根据场景错误提供专业的技术美术优化建议。
- **生产级架构**：多线程执行，大场景不卡顿；动态兼容旧版与新版 Maya UI 库。

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

### 第二步：在 Maya 中打开脚本编辑器
1. 启动 Maya。
2. 在顶部菜单栏中，依次点击：**窗口 (Windows)** -> **常规编辑器 (General Editors)** -> **脚本编辑器 (Script Editor)**。
   *(或者直接点击 Maya 界面右下角的 `{;}` 图标)。*
3. 在弹出的脚本编辑器中，选择下方的 **Python** 标签页（千万不要选 MEL）。

### 第三步：配置 API 并启动插件
将以下完整的 Python 代码复制并粘贴到您的脚本编辑器中。**请务必将代码中的 `API Key` 替换为您自己的真实 Key**。全选代码后，按下小键盘的 `Enter` 键或点击顶部的蓝色播放按钮 ▶️ 运行：

```python
import maya.cmds as cmds
import sys

# 1. 配置 AI 大模型 API 环境变量
# 【必填】设置您的 API Key (请将下方字符串替换为您的真实 Key)
cmds.optionVar(sv=("PolyGuard_AI_KEY", "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"))

# 【可选】设置 API 代理地址 (默认请求 OpenAI 官方，此处默认填入测试代理节点)
cmds.optionVar(sv=("PolyGuard_AI_URL", "https://tbnx.plus7.plus/v1/chat/completions"))

# 【可选】设置请求的模型名称 (默认为 gpt-4o，推荐使用此版本以保证速度和兼容性)
cmds.optionVar(sv=("PolyGuard_AI_MODEL", "gpt-4o"))

print("AI API 环境变量配置完成！")

# 2. 强制清理内存缓存并启动插件 UI
# 卸载旧模块，确保每次运行加载 of 都是最新代码，避免 Maya 缓存死锁
modules_to_delete = [m for m in sys.modules if m.startswith('PolyGuard')]
for m in modules_to_delete:
    del sys.modules[m]

# 导入并显示主界面
import PolyGuard.PolyGuard_UI as pgUI
pgUI.UI.show_UI()
```