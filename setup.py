from setuptools import setup, find_packages

setup(
    name="visibot",
    version="1.0.0",
    description="视觉机器人集成包 - Waveshare 2轴云台 + CSI摄像头 + DeepSeek视觉分析",
    author="Watson",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "httpx>=0.25.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
        ],
    },
)
