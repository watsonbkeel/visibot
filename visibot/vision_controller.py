"""视觉控制器：协调云台、摄像头、图像分析"""
import asyncio
import base64
import logging
import time
import httpx
from pathlib import Path
from typing import Optional, Callable

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False

LOG = logging.getLogger(__name__)


class VisionController:
    """视觉控制器
    
    职责：
    1. 调用 ugv_rpi 的 BaseController 控制云台
    2. 调用 picamera2 拍照
    3. 调用 DeepSeek 视觉模型分析图片
    4. 每 10 秒播报进度
    """
    
    def __init__(
        self,
        base_controller,  # ugv_rpi 的 BaseController 实例
        deepseek_base_url: str,
        deepseek_api_key: str,
        image_dir: str = "/tmp/visibot_images",
        progress_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        Args:
            base_controller: ugv_rpi 的 BaseController 实例
            deepseek_base_url: DeepSeek API 地址
            deepseek_api_key: DeepSeek API key
            image_dir: 图片存储目录
            progress_callback: 进度播报回调函数
        """
        self.base = base_controller
        self.deepseek_base_url = deepseek_base_url
        self.deepseek_api_key = deepseek_api_key
        self.image_dir = Path(image_dir)
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.progress_callback = progress_callback or (lambda msg: LOG.info(msg))
        
        self.client = httpx.AsyncClient(timeout=60.0)
        self.camera = None
        if PICAMERA2_AVAILABLE:
            try:
                self.camera = Picamera2()
                LOG.info("Picamera2 initialized")
            except Exception as e:
                LOG.error(f"Failed to init picamera2: {e}")
    
    def _report_progress(self, msg: str):
        """播报进度"""
        try:
            self.progress_callback(msg)
        except Exception as e:
            LOG.error(f"Progress callback failed: {e}")
    
    async def execute_command(self, cmd: dict) -> str:
        """执行视觉指令
        
        Args:
            cmd: 解析后的指令字典，格式：
                {
                    "direction": "left" | "right" | "up" | "down" | "center",
                    "angle": 20,
                    "actions": ["move", "capture", "analyze"]
                }
        
        Returns:
            执行结果描述（用于语音播报）
        """
        result = []
        
        # 启动进度播报任务
        progress_task = asyncio.create_task(self._progress_reporter())
        
        try:
            for action in cmd["actions"]:
                if action == "move":
                    self._report_progress("正在转向")
                    await self._move_gimbal(cmd["direction"], cmd["angle"])
                    result.append(f"云台已转向{cmd['direction']} {cmd['angle']}度")
                
                elif action == "capture":
                    self._report_progress("正在拍照")
                    image_path = await self._capture_photo()
                    result.append(f"照片已保存")
                
                elif action == "analyze":
                    self._report_progress("正在分析图片")
                    if not image_path:
                        image_path = await self._capture_photo()
                    
                    analysis = await self._analyze_image(image_path)
                    result.append(analysis)
            
            return "；".join(result)
        
        finally:
            # 停止进度播报
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
    
    async def _progress_reporter(self):
        """每 10 秒播报一次进度"""
        while True:
            await asyncio.sleep(10)
            self._report_progress("正在处理中")
    
    async def _move_gimbal(self, direction: str, angle: int):
        """移动云台
        
        Args:
            direction: "left" | "right" | "up" | "down" | "center"
            angle: 角度（度）
        """
        # 云台角度范围：
        # Pan (X): ±180° (左正右负)
        # Tilt (Y): -45° ~ 90° (上正下负)
        
        if direction == "center":
            # 回中
            self.base.gimbal_base_ctrl(2, 2, 0)
            await asyncio.sleep(2)  # 等待到位
            return
        
        # 计算目标角度
        x, y = 0, 0
        if direction == "left":
            x = angle
        elif direction == "right":
            x = -angle
        elif direction == "up":
            y = angle
        elif direction == "down":
            y = -angle
        
        # 绝对角度控制
        self.base.gimbal_ctrl(x, y, 0, 0)  # speed=0(最快), acc=0(最大加速度)
        
        # 等待舵机到位（估算时间：90度约1秒）
        wait_time = max(0.5, angle / 90)
        await asyncio.sleep(wait_time)
    
    async def _capture_photo(self) -> Path:
        """拍照并保存
        
        Returns:
            图片文件路径
        """
        timestamp = int(time.time())
        image_path = self.image_dir / f"capture_{timestamp}.jpg"
        
        if not self.camera:
            raise RuntimeError("Picamera2 not available")
        
        try:
            # 同步捕获转异步
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._capture_sync(image_path)
            )
            LOG.info(f"Photo saved: {image_path}")
            return image_path
        
        except Exception as e:
            raise RuntimeError(f"拍照失败: {e}")
    
    def _capture_sync(self, image_path: Path):
        """同步拍照（在 executor 中运行）"""
        # 启动摄像头
        config = self.camera.create_still_configuration(main={"size": (1920, 1080)})
        self.camera.configure(config)
        self.camera.start()
        time.sleep(2)  # 等待自动曝光稳定
        
        # 拍照
        self.camera.capture_file(str(image_path))
        
        # 关闭摄像头
        self.camera.stop()
    
    async def _analyze_image(self, image_path: Path) -> str:
        """分析图片内容
        
        Args:
            image_path: 图片文件路径
        
        Returns:
            图片内容描述
        """
        # 读取图片并转 base64
        image_data = image_path.read_bytes()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # 调用 DeepSeek 视觉模型
        try:
            resp = await self.client.post(
                f"{self.deepseek_base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.deepseek_api_key}"},
                json={
                    "model": "deepseek-chat",  # 或 deepseek-vision
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "请详细描述这张图片的内容，包括看到了什么物体、场景、颜色等。用一两句话简洁地描述。"
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 300,
                }
            )
            resp.raise_for_status()
            result = resp.json()
            content = result["choices"][0]["message"]["content"]
            return f"照片中{content}"
        
        except httpx.HTTPError as e:
            raise RuntimeError(f"图像分析失败: {e}")
    
    async def close(self):
        """关闭资源"""
        await self.client.aclose()
        if self.camera:
            try:
                self.camera.stop()
            except:
                pass
