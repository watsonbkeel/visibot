"""视觉指令解析器"""
import re
from typing import Optional, Dict, Any

def parse_vision_command(text: str) -> Optional[Dict[str, Any]]:
    """解析视觉指令
    
    Args:
        text: 用户说的话
    
    Returns:
        指令字典，格式：
        {
            "direction": "left" | "right" | "up" | "down",
            "angle": 20,
            "actions": ["move", "capture", "analyze"]
        }
        如果不是视觉指令，返回 None
    """
    text = text.strip()
    
    # 触发词：云台/摄像头/拍照/照相/看一下/回中
    triggers = ["云台", "摄像头", "拍照", "照相", "看一下", "看看", "转", "向左", "向右", "向上", "向下", "回中", "拍一张", "拍个", "告诉我"]
    if not any(t in text for t in triggers):
        return None
    
    result = {
        "direction": None,
        "angle": 0,
        "actions": []
    }
    
    # 解析方向
    if "左" in text:
        result["direction"] = "left"
    elif "右" in text:
        result["direction"] = "right"
    elif "上" in text:
        result["direction"] = "up"
    elif "下" in text:
        result["direction"] = "down"
    elif "中" in text or "正" in text or "回中" in text:
        result["direction"] = "center"
    
    # 解析角度（提取数字）
    angle_match = re.search(r'(\d+)\s*度', text)
    if angle_match:
        result["angle"] = int(angle_match.group(1))
    
    # 解析动作
    if result["direction"]:
        result["actions"].append("move")
    
    if any(k in text for k in ["拍照", "照相", "拍", "拍一张", "拍个"]):
        result["actions"].append("capture")
    
    if any(k in text for k in ["告诉我", "看到什么", "有什么", "分析", "识别", "看看"]):
        result["actions"].append("analyze")
    
    # 如果没有任何动作，返回 None
    if not result["actions"]:
        return None
    
    return result
