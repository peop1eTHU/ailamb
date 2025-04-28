from flask import Flask, render_template, send_file, jsonify, request, send_from_directory
import os
from datetime import datetime
import requests
from fpdf import FPDF
from threading import Thread
import time

app = Flask(__name__)
app.config['SNAPSHOT_FOLDER'] = 'static/snapshots'
os.makedirs(app.config['SNAPSHOT_FOLDER'], exist_ok=True)

# 自动清理旧快照（后台线程）
def clean_old_snapshots():
    while True:
        time.sleep(3600)  # 每小时清理一次
        now = time.time()
        for filename in os.listdir(app.config['SNAPSHOT_FOLDER']):
            filepath = os.path.join(app.config['SNAPSHOT_FOLDER'], filename)
            if os.stat(filepath).st_mtime < now - 24 * 3600:  # 保留24小时
                os.remove(filepath)

Thread(target=clean_old_snapshots, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/capture', methods=['POST'])
def capture_snapshot():
    try:
        response = requests.get("http://192.168.3.62:8080/?action=snapshot", timeout=5)
        if response.status_code != 200:
            return jsonify(success=False, error="无法获取摄像头数据")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{timestamp}.jpg"
        save_path = os.path.join(app.config['SNAPSHOT_FOLDER'], filename)

        with open(save_path, 'wb') as f:
            f.write(response.content)

        return jsonify(success=True, filename=filename)
    except Exception as e:
        return jsonify(success=False, error=str(e))

@app.route('/download/<filename>')
def download_snapshot(filename):
    # 防止路径遍历攻击
    if '..' in filename or '/' in filename:
        return jsonify(success=False, error="非法文件名")
    return send_from_directory(app.config['SNAPSHOT_FOLDER'], filename, as_attachment=True)

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    try:
        filenames = request.json.get('filenames', [])
        if not filenames:
            return jsonify(success=False, error="未选择图片")

        pdf = FPDF()
        for filename in filenames:
            path = os.path.join(app.config['SNAPSHOT_FOLDER'], filename)
            if not os.path.exists(path):
                continue

            pdf.add_page()
            pdf.image(path, x=10, y=10, w=190)  # 调整图片位置和大小

        pdf_output = os.path.join(app.config['SNAPSHOT_FOLDER'], "output.pdf")
        pdf.output(pdf_output)

        return send_file(pdf_output, as_attachment=True, download_name="snapshots.pdf")

    except Exception as e:
        return jsonify(success=False, error=str(e))
    
if __name__ == '__main__':
    # 启动 Flask 服务器（端口 5000）
    app.run(host='0.0.0.0', port=5000, debug=True)