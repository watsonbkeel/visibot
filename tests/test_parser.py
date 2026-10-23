"""测试视觉指令解析"""
import sys
sys.path.insert(0, '.')

from visibot.parser import parse_vision_command

# 测试用例
tests = [
    # (输入, 预期是否匹配, 预期方向, 预期角度, 预期动作)
    ("摄像头向左移动20度", True, "left", 20, ["move"]),
    ("向右转30度然后拍照", True, "right", 30, ["move", "capture"]),
    ("拍一张照片并告诉我有什么", True, None, 0, ["capture", "analyze"]),
    ("云台向上45度", True, "up", 45, ["move"]),
    ("回中", True, "center", 0, ["move"]),
    ("拍照看看前面有什么", True, None, 0, ["capture", "analyze"]),
    ("你好", False, None, 0, []),
    ("学英语", False, None, 0, []),
]

print("测试视觉指令解析：")
for text, should_match, exp_dir, exp_angle, exp_actions in tests:
    result = parse_vision_command(text)
    
    if should_match:
        if result is None:
            print(f"❌ \"{text}\" → None (预期匹配)")
        else:
            # 检查方向、角度、动作
            dir_ok = result["direction"] == exp_dir
            angle_ok = result["angle"] == exp_angle
            actions_ok = result["actions"] == exp_actions
            
            if dir_ok and angle_ok and actions_ok:
                print(f"✅ \"{text}\" → {result}")
            else:
                print(f"❌ \"{text}\" → {result}")
                print(f"   预期: dir={exp_dir}, angle={exp_angle}, actions={exp_actions}")
    else:
        if result is None:
            print(f"✅ \"{text}\" → None (正确过滤)")
        else:
            print(f"❌ \"{text}\" → {result} (应该过滤)")
