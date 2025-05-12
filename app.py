from flask import Flask, render_template, send_file, jsonify, request, send_from_directory
import os
from datetime import datetime
import requests
from fpdf import FPDF
from threading import Thread
import time
from scripts.led import init_animation_thread,operate_led
import pygame
import threading
from queue import Queue
from PIL import Image
from apscheduler.schedulers.background import BackgroundScheduler
from io import BytesIO


app = Flask(__name__)
app.config['SNAPSHOT_FOLDER'] = 'static/snapshots'
os.makedirs(app.config['SNAPSHOT_FOLDER'], exist_ok=True)

pygame.mixer.init()

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

init_animation_thread()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/capture', methods=['POST'])
def capture_snapshot():
    try:
        response = requests.get("http://192.168.3.62:8080/?action=snapshot", timeout=5)
        if response.status_code != 200:
            return jsonify(success=False, error="无法获取摄像头数据")

        img = Image.open(BytesIO(response.content))
        rotated_img = img.rotate(-90, expand=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{timestamp}.jpg"
        save_path = os.path.join(app.config['SNAPSHOT_FOLDER'], filename)

        rotated_img.save(save_path)

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
    
@app.route('/toggle_led', methods=['POST'])
def toggle_led():
    """控制 LED 开关的 API"""
    try:
        state = request.json.get('state', 'off')
        operate_led(state)
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e))

@app.route('/play_timer_start', methods=['POST'])
def play_start():
    pygame.mixer.music.load("static/sounds/timer_start.mp3")
    pygame.mixer.music.play()

@app.route('/play_timer_end', methods=['POST'])
def play_end():
    pygame.mixer.music.load("static/sounds/timer_end.mp3")
    pygame.mixer.music.play()


app.config['MUSIC_FOLDER'] = 'static/music'
app.config['ALLOWED_EXT'] = {'mp3', 'wav', 'ogg', 'flac'}
os.makedirs(app.config['MUSIC_FOLDER'], exist_ok=True)

# Pygame音乐控制全局变量
pygame.mixer.init()
current_track = None
playlist = []
player_queue = Queue()
is_playing = False
volume = 1.0
lock = threading.Lock()

def music_player_daemon():
    """音乐播放守护线程"""
    global current_track, is_playing
    while True:
        if not player_queue.empty():
            with lock:
                current_track = player_queue.get()
                pygame.mixer.music.load(current_track['path'])
                pygame.mixer.music.play()
                is_playing = True
                
        if is_playing and not pygame.mixer.music.get_busy():
            with lock:
                is_playing = False
        time.sleep(1)

# 启动守护线程
threading.Thread(target=music_player_daemon, daemon=True).start()

@app.route('/music/upload', methods=['POST'])
def upload_music():
    """上传音乐文件到服务器"""
    if 'file' not in request.files:
        return jsonify(success=False, error="未选择文件")
    
    file = request.files['file']
    if file.filename == '':
        return jsonify(success=False, error="空文件名")
    
    if file and allowed_file(file.filename):
        # filename = secure_filename(file.filename)
        filename = file.filename
        file_path = os.path.join(app.config['MUSIC_FOLDER'], filename)
        file.save(file_path)
        return jsonify(success=True, filename=filename)
    
    return jsonify(success=False, error="不支持的文件类型")

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXT']

@app.route('/music/list')
def get_music_list():
    """获取服务器音乐列表"""
    try:
        files = [f for f in os.listdir(app.config['MUSIC_FOLDER']) 
                if f.split('.')[-1] in app.config['ALLOWED_EXT']]
        return jsonify(success=True, files=files)
    except Exception as e:
        return jsonify(success=False, error=str(e))

@app.route('/music/control', methods=['POST'])
def control_music():
    """音乐播放控制接口"""
    global is_playing, volume
    action = request.json.get('action')
    
    with lock:
        if action == 'play':
            if not pygame.mixer.music.get_busy():
                if current_track:
                    pygame.mixer.music.unpause()
                else:
                    return jsonify(success=False, error="无可用曲目")
            is_playing = True
        elif action == 'pause':
            pygame.mixer.music.pause()
            is_playing = False
        elif action == 'stop':
            pygame.mixer.music.stop()
            is_playing = False
        elif action == 'volume':
            volume = max(0.0, min(1.0, float(request.json.get('value', 1.0))))
            pygame.mixer.music.set_volume(volume)
        elif action == 'play_track':
            filename = request.json.get('file')
            filepath = os.path.join(app.config['MUSIC_FOLDER'], filename)
            if not os.path.exists(filepath):
                return jsonify(success=False, error="文件不存在")
            player_queue.put({'path': filepath, 'name': filename})
        elif action == 'next':
            pass  # 需要实现播放队列逻辑
        else:
            return jsonify(success=False, error="无效操作")
            
    return jsonify(success=True)

@app.route('/music/status')
def get_music_status():
    """获取当前播放状态"""
    with lock:
        return jsonify(
            current_track=current_track['name'] if current_track else None,
            is_playing=is_playing,
            volume=volume
        )

app.config['STUDY_FOLDER'] = 'static/study_records'
os.makedirs(app.config['STUDY_FOLDER'], exist_ok=True)

# 定时任务调度器
scheduler = BackgroundScheduler(daemon=True)
current_interval = 5  # 默认5分钟
capture_enabled = False

def capture_study_photo(force=False):
    """定时拍照函数"""
    if not force:
        if not capture_enabled:
            return
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"study_{timestamp}.jpg"
        save_path = os.path.join(app.config['STUDY_FOLDER'], filename)
        
        # 使用fswebcam拍照（需安装）
        os.system(f"fswebcam -r 1920x1080 --no-banner {save_path}")
        
    except Exception as e:
        print(f"拍照失败: {str(e)}")

# 初始化调度器
scheduler.add_job(capture_study_photo, 'interval', minutes=current_interval, id='default')
scheduler.start()

@app.route('/study/control', methods=['POST'])
def study_control():
    """学习记录控制接口"""
    global current_interval, capture_enabled
    action = request.json.get('action')
    
    if action == 'set_interval':
        new_interval = int(request.json.get('interval'))
        if new_interval < 1:
            return jsonify(success=False, error="间隔时间需大于1分钟")
        
        current_interval = new_interval
        scheduler.reschedule_job(
            'default', 
            trigger='interval', 
            minutes=current_interval
        )
        return jsonify(success=True)
    
    elif action == 'toggle_capture':
        capture_enabled = not capture_enabled
        return jsonify(success=True, enabled=capture_enabled)
    
    elif action == 'capture_now':
        capture_study_photo(force=True)
        return jsonify(success=True)
    
    return jsonify(success=False, error="无效操作")

@app.route('/study/photos')
def get_study_photos():
    """获取学习记录照片列表"""
    try:
        photos = sorted(
            [f for f in os.listdir(app.config['STUDY_FOLDER']) if f.endswith('.jpg')],
            reverse=True
        )
        return jsonify(success=True, photos=photos)
    except Exception as e:
        return jsonify(success=False, error=str(e))

# 番茄时钟全局状态
pomodoro_status = {
    "is_working": True,
    "is_break": False,
    "remaining": 1500,  # 默认25分钟（单位：秒）
    "work_duration": 1500,
    "break_duration": 300,
    "cycles": 1,
    "total_tomatoes": 0
}

# 定时任务调度器
scheduler = BackgroundScheduler(daemon=True)
scheduler.start()

def update_pomodoro():
    """更新番茄时钟状态"""
    global pomodoro_status
    if pomodoro_status["remaining"] > 0:
        pomodoro_status["remaining"] -= 1
    else:
        handle_period_end()

def handle_period_end():
    """阶段结束处理"""
    global pomodoro_status
    if pomodoro_status["is_working"]:
        # 工作时间结束，进入休息
        pomodoro_status.update({
            "is_working": False,
            "is_break": True,
            "remaining": pomodoro_status["break_duration"]
        })
        # 控制LED闪烁提醒
        operate_led('on')
        play_end()
    else:
        # 休息时间结束，开始新番茄
        pomodoro_status.update({
            "is_working": True,
            "is_break": False,
            "remaining": pomodoro_status["work_duration"],
            "total_tomatoes": pomodoro_status["total_tomatoes"] + 1,
            "cycles": pomodoro_status["cycles"] +1
        })
        # LED长亮提醒
        operate_led('off')
        play_start()
    scheduler.resume()

@app.route('/pomodoro/control', methods=['POST'])
def pomodoro_control():
    """番茄时钟控制接口"""
    action = request.json.get('action')
    
    if action == 'start':
        if not scheduler.get_jobs():
            scheduler.add_job(update_pomodoro, 'interval', seconds=1, id='pomodoro')
        scheduler.resume()
        play_start()
        return jsonify(success=True)
    
    elif action == 'pause':
        scheduler.pause()
        return jsonify(success=True)
    
    elif action == 'reset':
        scheduler.pause()
        pomodoro_status.update({
            "is_working": True,
            "is_break": False,
            "remaining": pomodoro_status["work_duration"],
            "cycles": 1
        })
        operate_led('off')
        return jsonify(success=True)
    
    elif action == 'set_duration':
        work = int(request.json.get('work')) * 60
        break_dur = int(request.json.get('break')) * 60
        pomodoro_status["work_duration"] = work
        pomodoro_status["break_duration"] = break_dur
        pomodoro_status["remaining"] = work
        return jsonify(success=True)
    
    return jsonify(success=False, error="无效操作")

@app.route('/pomodoro/status')
def get_pomodoro_status():
    """获取当前状态"""
    return jsonify({
        "status": "working" if pomodoro_status["is_working"] else "break",
        "remaining": pomodoro_status["remaining"],
        "cycles": pomodoro_status["cycles"],
        "total_tomatoes": pomodoro_status["total_tomatoes"]
    })

if __name__ == '__main__':
    # 启动 Flask 服务器（端口 5000）
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)