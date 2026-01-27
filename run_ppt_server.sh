#!/bin/bash
# Paper Trade 本地启动脚本

cd "$(dirname "$0")"

# 激活 conda 环境
source ~/anaconda3/etc/profile.d/conda.sh
conda activate sai

# 创建运行时数据目录
mkdir -p run/db run/logs run/opentimestamps

echo "启动 Paper Trade 服务..."
echo "访问地址: http://0.0.0.0:11182"
echo ""

# 启动 Flask (通过 socketio)
python app.py
