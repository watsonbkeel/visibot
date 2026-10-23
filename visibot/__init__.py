"""Visibot - 视觉机器人集成包"""
__version__ = "1.0.0"

from .vision_controller import VisionController
from .parser import parse_vision_command

__all__ = ["VisionController", "parse_vision_command"]
