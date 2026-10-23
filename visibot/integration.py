"""与 english-edge 的集成接口"""
import asyncio
import os
import logging
from typing import Optional

from .parser import parse_vision_command
from .vision_controller import VisionController

LOG = logging.getLogger(__name__)


def create_vision_controller(base_controller, progress_callback=None):
    """创建视觉控制器实例
    
    Args:
        base_controller: ugv_rpi 的 BaseController 实例
        progress_callback: 进度播报回调函数 (msg: str) -> None
    
    Returns:
        VisionController 实例
    """
    # 从环境变量读取配置
    deepseek_base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    image_dir = os.environ.get("VISIBOT_IMAGE_DIR", "/tmp/visibot_images")
    
    if not deepseek_api_key:
        LOG.warning("DEEPSEEK_API_KEY not set, vision analysis will fail")
    
    return VisionController(
        base_controller=base_controller,
        deepseek_base_url=deepseek_base_url,
        deepseek_api_key=deepseek_api_key,
        image_dir=image_dir,
        progress_callback=progress_callback,
    )


def handle_vision_command_sync(text: str, base_controller, progress_callback=None) -> Optional[str]:
    """同步处理视觉指令（供 english-edge 调用）
    
    Args:
        text: 用户说的话
        base_controller: ugv_rpi 的 BaseController 实例
        progress_callback: 进度播报回调函数
    
    Returns:
        如果是视觉指令，返回执行结果描述；否则返回 None
    """
    # 解析指令
    cmd = parse_vision_command(text)
    if not cmd:
        return None
    
    LOG.info(f"Vision command detected: {cmd}")
    
    # 创建控制器
    controller = create_vision_controller(base_controller, progress_callback)
    
    # 执行（同步包装异步）
    try:
        result = asyncio.run(controller.execute_command(cmd))
        asyncio.run(controller.close())
        return result
    except Exception as e:
        LOG.error(f"Vision command failed: {e}")
        return f"视觉任务执行失败：{e}"
