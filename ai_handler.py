import json
import maya.cmds as cmds
import urllib.request
import urllib.error

class AIHandler:
    # 本地专家库：用于无 Key 时的逻辑验证
    LOCAL_TIPS = {
        "trailingNumbers": {"title": "命名规范化", "advice": "发现数字后缀。建议使用语义化命名（如 L_Arm）代替系统默认数字。"},
        "history": {"title": "性能预警", "advice": "构造历史过长。建议在进入下一个环节前执行 bakePartialHistory。"},
        "unfrozenTransforms": {"title": "坐标偏移风险", "advice": "变换未冻结。这在导出到游戏引擎时会引起严重的位移偏差。"},
        "ngons": {"title": "拓扑质量", "advice": "包含 N-Gons。这会导致实时渲染中出现阴影破损或细分褶皱。"},
        "poles": {"title": "表面平滑度", "advice": "发现 5 边以上极点。建议将其移动到非形变或平坦区域。"}
    }

    @staticmethod
    def get_api_info():
        # 默认使用您提供的 Plus7 代理地址
        url = cmds.optionVar(q="PolyGuard_AI_URL") or "https://tbnx.plus7.plus/v1/chat/completions"
        key = cmds.optionVar(q="PolyGuard_AI_KEY") or ""
        return url, key

    @staticmethod
    def analyze_errors(error_summary):
        url, key = AIHandler.get_api_info()
        
        # 显性状态：若无 Key 则进入模拟模式
        if not key:
            return AIHandler.get_mock_advice(error_summary)

        # 确保 API URL 路径完整
        if not url.endswith("completions"):
            url = url.rstrip("/") + "/v1/chat/completions"

        prompt_content = "以下是Maya场景资产检查出的问题ID汇总：\n"
        prompt_content += error_summary + "\n"

        model_name = cmds.optionVar(q="PolyGuard_AI_MODEL") or "gpt-4o-mini"

        # 构造请求
        data = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "你是一位资深 Maya 技术美术（TA）。请分析模型检查报告并给出专业的中文优化建议。请保持技术术语的专业性，排版清晰。"},
                {"role": "user", "content": "场景错误概摘要：" + prompt_content}
            ],
            "temperature": 0.7
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req, timeout=20) as response:
                result = json.loads(response.read().decode())
                content = result['choices'][0]['message']['content']
                return "<b style='color:#5AB9E6;'>[ 实时 AI 智能建议 - 极速模式 ]</b><br><br>" + content.replace("\n", "<br>")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode()
            return "<b style='color:#E74C3C;'>[ API 请求失败 ({}) ]</b><br><br>详情: {}".format(e.code, err_body)
        except Exception as e:
            return "<b style='color:#E67E22;'>[ 联网失败，已回退至本地专家库 ]</b><br><br>" + AIHandler.get_mock_advice(error_summary)

    @staticmethod
    def get_mock_advice(summary):
        html = "<b style='color:#9B59B6;'>[ 本地 TA 专家模拟模式 ]</b><br><br>"
        found_any = False
        rule_ids = summary.split(",")
        for rid in rule_ids:
            if rid in AIHandler.LOCAL_TIPS:
                tip = AIHandler.LOCAL_TIPS[rid]
                html += "<b>▶ {}</b>: {}<br><br>".format(tip['title'], tip['advice'])
                found_any = True
        if not found_any or "NoErrors" in summary:
            html += "<b>检查完毕</b>：场景状态良好，未发现严重拓扑或命名风险。<br>"
        html += "<br><hr><i>提示：运行激活脚本设置 API KEY 后即可启用实时 AI 诊断。</i>"
        return html
