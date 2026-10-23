# Visibot - 视觉机器人集成包

基于 Waveshare UGV/2轴云台套件的视觉机器人功能，集成云台控制、CSI 摄像头拍照和 DeepSeek 视觉模型分析。

## 硬件架构

```
树莓派 (Raspberry Pi)
├── UART (/dev/serial0) ─→ ESP32 驱动板 ─→ 云台舵机 (Pan/Tilt)
├── CSI 接口 ─→ 摄像头模块
└── USB 口 ─→ (可选) IMX335 USB 摄像头
```

## 软件架构

```
english-edge (对话机器人)
  ↓ 识别视觉指令
visibot.integration.handle_vision_command_sync()
  ↓
visibot.VisionController
  ├─ 调用 ugv_rpi.BaseController.gimbal_ctrl()  # 云台控制
  ├─ 调用 picamera2.capture_file()              # CSI 摄像头拍照
  └─ 调用 DeepSeek vision API                   # 图像分析
```

## 功能特性

- **云台控制**：支持绝对角度/持续运动，范围 Pan ±180°, Tilt -45°~90°
- **CSI 摄像头拍照**：使用 picamera2，分辨率 1920×1080
- **图像分析**：DeepSeek 多模态模型，自动描述图片内容
- **进度播报**：每 10 秒播报一次当前阶段（转向/拍照/分析）
- **指令解析**：自然语言理解，支持"向左20度然后拍照并告诉我有什么"

## 安装

### 1. 树莓派安装依赖

```bash
# 安装 picamera2（CSI 摄像头驱动）
sudo apt install -y python3-picamera2

# 安装 visibot
cd /opt
sudo git clone https://github.com/watsonbkeel/visibot.git
cd visibot
sudo pip3 install -e .
```

### 2. 配置环境变量

在 `/etc/english-class/students/s001.env` 中添加：

```bash
# DeepSeek API 配置
DEEPSEEK_BASE_URL=https://api.bkeel.com
DEEPSEEK_API_KEY=sk-xxx

# 图片存储目录（可选）
VISIBOT_IMAGE_DIR=/tmp/visibot_images
```

## 使用方式

### 方式 1：集成到 english-edge

在 `pi/english_voice.py` 的 `Chat.say()` 中调用：

```python
from visibot.integration import handle_vision_command_sync

def say(self, text):
    # 优先处理视觉指令
    result = handle_vision_command_sync(
        text=text,
        base_controller=self.base,  # ugv_rpi 的 BaseController 实例
        progress_callback=lambda msg: self.edge.local_message(msg)
    )
    
    if result:
        # 播报结果
        self.edge.local_message(result)
        return
    
    # 原有聊天逻辑...
```

### 方式 2：独立使用

```python
from base_ctrl import BaseController
from visibot import VisionController, parse_vision_command
import asyncio

# 初始化 ugv_rpi 控制器
base = BaseController('/dev/serial0', 115200)

# 创建视觉控制器
vision = VisionController(
    base_controller=base,
    deepseek_base_url="https://api.bkeel.com",
    deepseek_api_key="sk-xxx",
    progress_callback=lambda msg: print(f"[进度] {msg}")
)

# 解析并执行指令
cmd = parse_vision_command("向左转20度然后拍照并告诉我有什么")
result = asyncio.run(vision.execute_command(cmd))
print(result)
```

## 指令示例

| 用户说的话 | 解析结果 |
|---|---|
| "摄像头向左移动20度" | `move(left, 20°)` |
| "向右转30度然后拍照" | `move(right, 30°)` → `capture()` |
| "拍一张照片并告诉我有什么" | `capture()` → `analyze()` |
| "云台向上45度" | `move(up, 45°)` |
| "回中" | `move(center)` |
| "拍照看看前面有什么" | `capture()` → `analyze()` |

## 云台角度范围

- **Pan（水平）**：±180°（左正右负）
- **Tilt（垂直）**：-45° ~ 90°（上正下负）

## API 参考

### `parse_vision_command(text: str) -> Optional[dict]`

解析视觉指令。

**返回值**：
```python
{
    "direction": "left" | "right" | "up" | "down" | "center",
    "angle": 20,
    "actions": ["move", "capture", "analyze"]
}
```

### `VisionController.execute_command(cmd: dict) -> str`

执行视觉指令。

**返回值**：执行结果描述（用于语音播报）

## 依赖

- `ugv_rpi` / `base_ctrl.py`（云台控制，已存在）
- `picamera2`（CSI 摄像头，系统库）
- `httpx`（HTTP 客户端）
- `DeepSeek API`（图像分析）

## 故障排查

### 1. `ModuleNotFoundError: No module named 'picamera2'`

```bash
sudo apt install -y python3-picamera2
```

### 2. 云台不转动

检查 ugv_rpi 是否正常运行：

```bash
sudo systemctl status ugv_rpi
ps aux | grep ugv
```

确认 `/dev/serial0` 没有被其他进程占用。

### 3. DeepSeek API 调用失败

检查环境变量是否正确：

```bash
grep DEEPSEEK /etc/english-class/students/s001.env
```

测试 API：

```bash
curl -X POST https://api.bkeel.com/v1/chat/completions \
  -H "Authorization: Bearer sk-xxx" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"你好"}]}'
```

## 开发

```bash
# 测试指令解析
python tests/test_parser.py

# 语法检查
python -m py_compile visibot/*.py
```

## 许可证

MIT
