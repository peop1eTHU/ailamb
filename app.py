from flask import Flask, render_template, send_file, jsonify, request
import os
from datetime import datetime
import requests

app = Flask(__name__)
app.config['SNAPSHOT_FOLDER'] = 'static/snapshots'  # 拍照保存路径

# 确保快照目录存在
os.makedirs(app.config['SNAPSHOT_FOLDER'], exist_ok=True)

# MJPG-Streamer 的推流地址（根据实际情况修改）
MJPG_STREAMER_URL = "http://192.168.3.62:8080"

@app.route('/')
def index():
    """主页面：渲染包含视频和按钮的模板"""
    return render_template('index.html',MJPG_STREAMER_URL=MJPG_STREAMER_URL)

@app.route('/capture', methods=['POST'])
def capture_snapshot():
    """拍照API：通过 MJPG-Streamer 抓取快照并保存到本地"""
    try:
        # 从 MJPG-Streamer 获取快照
        response = requests.get(f"{MJPG_STREAMER_URL}/?action=snapshot", timeout=5)
        if response.status_code != 200:
            return jsonify(success=False, error="无法获取摄像头数据")

        # 生成唯一文件名（时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{timestamp}.jpg"
        save_path = os.path.join(app.config['SNAPSHOT_FOLDER'], filename)

        # 保存图片
        with open(save_path, 'wb') as f:
            f.write(response.content)

        return jsonify(success=True, filename=filename)

    except Exception as e:
        return jsonify(success=False, error=str(e))

@app.route('/download/<filename>')
def download_snapshot(filename):
    """下载API：通过文件名下载图片"""
    try:
        path = os.path.join(app.config['SNAPSHOT_FOLDER'], filename)
        return send_file(path, as_attachment=True)
    except FileNotFoundError:
        return jsonify(success=False, error="文件不存在")

if __name__ == '__main__':
    # 启动 Flask 服务器（端口 5000）
    app.run(host='0.0.0.0', port=5000, debug=True)