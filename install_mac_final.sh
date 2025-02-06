#!/bin/zsh

# 确保在虚拟环境中
source .venv/bin/activate

# 清理旧依赖
pip freeze | grep -E 'moviepy|decorator|numpy' | xargs pip uninstall -y

# 安装基础工具
pip install --upgrade pip setuptools==68.0.0 wheel

# 安装Apple Silicon优化版numpy
pip install numpy==1.26.4 \
--extra-index-url=https://pypi.anaconda.org/scipy-wheels-nightly/simple \
--no-cache-dir \
--force-reinstall

# 安装视频处理套件
pip install "moviepy==1.0.3" \
"decorator==4.4.2" \
"tqdm==4.66.2" \
"imageio-ffmpeg==0.4.9" \
"proglog==0.1.10"

# 验证安装
python -c "from moviepy.editor import VideoFileClip; print('✅ 环境配置成功！')"