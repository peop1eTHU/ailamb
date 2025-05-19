
// 新增分页切换逻辑
function switchTab(tabName) {
    // 隐藏所有分页内容
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    // 移除所有按钮激活状态
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    // 显示目标分页并激活按钮
    document.getElementById(`${tabName}Tab`).classList.add('active');
    document.getElementById(`${tabName}but`).classList.add('active');
    localStorage.setItem('lastActiveTab', tabName);
}

// 页面加载时恢复
window.onload = () => {
    const lastTab = localStorage.getItem('lastActiveTab') || 'camera';
    switchTab(lastTab);
};



let snapshots = [];  // 存储当前会话中的所有快照文件名

// 拍照功能
async function captureSnapshot() {
    try {
        const response = await fetch('/capture', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            snapshots.push(data.filename);
            updateSnapshotList();
        } else {
            alert(`拍照失败: ${data.error}`);
        }
    } catch (error) {
        alert('请求失败: ' + error.message);
    }
}

// 更新右侧列表
function updateSnapshotList() {
    const list = document.getElementById('snapshotList');
    list.innerHTML = snapshots.map(filename => `
        <div class="snapshot-item" onclick="previewSnapshot('${filename}')">
            <img src="/static/snapshots/${filename}" alt="${filename}">
        </div>
    `).join('');
}

// 预览单张快照
function previewSnapshot(filename) {
    document.getElementById('latestSnapshot').src = `/static/snapshots/${filename}`;
    document.getElementById('latestSnapshot').style.display = 'block';
}

// 生成PDF
async function downloadPDF() {
    if (snapshots.length === 0) {
        alert('请先拍照！');
        return;
    }

    try {
        const response = await fetch('/generate_pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filenames: snapshots })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '生成PDF失败');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'snapshots.pdf';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        alert('PDF下载失败: ' + error.message);
    }
}



// 全局变量
let timerInterval = null;
let remainingSeconds = 0;

// 开始倒计时
function startTimer() {
    const duration = parseInt(document.getElementById('timerDuration').value);
    if (isNaN(duration) || duration < 1) {
        alert('请输入有效的秒数！');
        return;
    }

    ledOff();
    playStart();

    // 清除旧计时器
    if (timerInterval) clearInterval(timerInterval);

    remainingSeconds = duration;
    updateTimerDisplay();

    // 启动前端倒计时显示
    timerInterval = setInterval(() => {
        remainingSeconds--;
        updateTimerDisplay();
        if (remainingSeconds <= 0) {
            clearInterval(timerInterval);
            ledOn();
            playEnd();
        }
    }, 1000);
}

// 更新倒计时显示
function updateTimerDisplay() {
    const minutes = Math.floor(remainingSeconds / 60).toString().padStart(2, '0');
    const seconds = (remainingSeconds % 60).toString().padStart(2, '0');
    document.getElementById('timerDisplay').textContent = `${minutes}:${seconds}`;
}

function playStart(){
    fetch('/play_timer_start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ })
    }).then(response => response.json())
    .then(data => {
        if (!data.success) alert('播放失败: ' + data.error);
    });
}
function playEnd(){
    fetch('/play_timer_end', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ })
    }).then(response => response.json())
    .then(data => {
        if (!data.success) alert('播放失败: ' + data.error);
    });
}

function ledOff() {
    fetch('/toggle_led', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: 'off' })
    }).then(response => response.json())
    .then(data => {
        if (!data.success) alert('开灯失败: ' + data.error);
    });
}

// 倒计时结束后触发开灯
function ledOn() {
    fetch('/toggle_led', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: 'on' })
    }).then(response => response.json())
    .then(data => {
        if (!data.success) alert('开灯失败: ' + data.error);
    });
}

// 重置
function manualToggleLed() {
    // const isOn = document.getElementById('timerDisplay').textContent !== '00:00';
    fetch('/toggle_led', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // body: JSON.stringify({ state: isOn ? 'off' : 'on' })
        body: JSON.stringify({ state: 'off' })
    }).then(response => response.json())
    .then(data => {
        if (data.success) {
            // alert(`灯已${isOn ? '关闭' : '打开'}`);
        } else {
            alert('操作失败: ' + data.error);
        }
    });
}



// 初始化加载播放列表
loadMusicList();
setInterval(updateStatus, 1000);  // 每秒更新状态

// 加载音乐列表
async function loadMusicList() {
    try {
        const response = await fetch('/music/list');
        const data = await response.json();
        if (data.success) {
            renderMusicList(data.files);
        }
    } catch (error) {
        console.error('加载失败:', error);
    }
}

// 渲染播放列表
function renderMusicList(files) {
    const container = document.getElementById('musicList');
    container.innerHTML = files.map(file => `
        <div class="track-item" onclick="playTrack('${file}')">
            ${file}
        </div>
    `).join('');
}

// 控制指令发送
async function control(action, extraData = {}) {
    console.log(action);
    const response = await fetch('/music/control', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ action, ...extraData })
    });
    const data = await response.json();
    if (!data.success) alert(data.error);
}

// 播放指定曲目
function playTrack(filename) {
    control('play_track', { file: filename });
}

// 设置音量
async function setVolume(value) {
    await fetch('/music/control', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ 
            action: 'volume',
            value: parseFloat(value)
        })
    });
}

// 更新播放状态
async function updateStatus() {
    const response = await fetch('/music/status');
    const data = await response.json();
    document.getElementById('currentTrack').textContent = 
        data.current_track || '无';
    document.getElementById('playStatus').textContent = 
        data.is_playing ? '播放中' : '已暂停/停止';
    document.getElementById('volume').value = data.volume;
}

// 上传音乐
async function uploadMusic() {
    const fileInput = document.getElementById('musicUpload');
    if (fileInput.files.length === 0) {
        alert('请选择音乐文件');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const response = await fetch('/music/upload', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (data.success) {
            await loadMusicList();
            alert('上传成功！');
        } else {
            alert('上传失败: ' + data.error);
        }
    } catch (error) {
        alert('请求失败: ' + error.message);
    }
}



// 初始化加载照片
loadStudyPhotos();
setInterval(loadStudyPhotos, 5000); // 每5秒刷新

// 加载照片列表
async function loadStudyPhotos() {
    try {
        const response = await fetch('/study/photos');
        const data = await response.json();
        if (data.success) {
            renderPhotos(data.photos);
        }
    } catch (error) {
        console.error('加载失败:', error);
    }
}

// 渲染照片网格
function renderPhotos(photos) {
    const container = document.getElementById('photoGrid');
    container.innerHTML = photos.map(photo => `
        <div class="photo-item">
            <img src="/static/study_records/${photo}" 
                onclick="showFullImage('${photo}')">
            <div class="photo-date">
                ${parseDateFromFilename(photo)}
            </div>
        </div>
    `).join('');
}

// 解析文件名中的时间戳
function parseDateFromFilename(filename) {
    const ts = filename.split('_')[1];
    const year = ts.slice(0,4);
    const month = ts.slice(4,6);
    const day = ts.slice(6,8);
    const time = ts.slice(9,15).replace(/(..)/g, '$1:').slice(0,-1);
    return `${year}-${month}-${day} ${time}`;
}

// 设置间隔时间
async function setsetInterval() {
    const interval = document.getElementById('intervalInput').value;
    const response = await fetch('/study/control', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            action: 'set_interval',
            interval: parseInt(interval)
        })
    });
    const data = await response.json();
    if (data.success) {
        alert('间隔时间设置成功');
    } else {
        alert('设置失败: ' + data.error);
    }
}

// 切换定时状态
async function toggleCapture() {
    const response = await fetch('/study/control', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ action: 'toggle_capture' })
    });
    const data = await response.json();
    if (data.success) {
        const btn = document.getElementById('toggleBtn');
        btn.textContent = data.enabled ? '停止定时' : '开启定时';
        document.getElementById('captureStatus').textContent = 
            data.enabled ? '运行中' : '已停止';
    }
}

// 立即拍照
async function captureNow() {
    const response = await fetch('/study/control', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ action: 'capture_now' })
    });
    if (response.ok) {
        setTimeout(loadStudyPhotos, 1000); // 1秒后刷新
    }
}

// 显示大图（需添加模态框组件）
function showFullImage(filename) {
    window.open(`/static/study_records/${filename}`, '_blank');
}



// 状态更新定时器
let statusInterval = null;

// 控制番茄时钟
async function controlPomodoro(action) {
    const response = await fetch('/pomodoro/control', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ action: action })
    });
    
    if (action === 'start') {
        startStatusUpdates();
    } else if (action === 'pause') {
        clearInterval(statusInterval);
    }
}

// 启动状态轮询
function startStatusUpdates() {
    clearInterval(statusInterval);
    statusInterval = setInterval(updateStatusDisplay, 1000);
}

// 更新界面显示
async function updateStatusDisplay() {
    const response = await fetch('/pomodoro/status');
    const data = await response.json();
    
    // 时间格式化
    const minutes = Math.floor(data.remaining / 60).toString().padStart(2, '0');
    const seconds = (data.remaining % 60).toString().padStart(2, '0');
    document.getElementById('timeDisplay').textContent = `${minutes}:${seconds}`;
    
    // 状态指示
    const phaseMap = {
        'working': '专注时间',
        'break': '休息时间'
    };
    document.getElementById('phaseIndicator').textContent = 
        data.status ? phaseMap[data.status] : '准备开始';
    
    // 统计信息
    document.getElementById('tomatoCount').textContent = data.total_tomatoes;
    document.getElementById('cycleCount').textContent = data.cycles;
    
    // 动态颜色
    const timeDisplay = document.getElementById('timeDisplay');
    timeDisplay.style.color = data.status === 'working' ? '#e9bb1d' : '#2ecc71';
}

// 保存设置
async function saveSettings() {
    const work = document.getElementById('workTime').value;
    const breakTime = document.getElementById('breakTime').value;
    
    await fetch('/pomodoro/control', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            action: 'set_duration',
            work: work,
            break: breakTime
        })
    });
    alert('设置已保存！');
}

// 初始加载
updateStatusDisplay();



let currentAssignment = null;

var currentHomeworkList = null;

// 网络学堂登录
async function eduLogin() {
    const username = document.getElementById('eduUser').value;
    const password = document.getElementById('eduPass').value;
    
    const response = await fetch('/edu/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ username, password })
    });
    
    const data = await response.json();
    if (data.success) {
        showLoginStatus('登录成功', 'success');
        loadAssignments();
    } else {
        showLoginStatus(`登录失败: ${data.error}`, 'error');
    }
}

// 加载作业列表
async function loadAssignments() {
    const response = await fetch('/edu/assignments');
    const data = await response.json();
    
    currentHomeworkList = data.assignments;
    if (data.success) {
        renderAssignments(data.assignments);
    } else {
        showLoginStatus(`获取作业失败: ${data.error}`, 'error');
    }
}

// 渲染作业列表
function renderAssignments(assignments) {
    const container = document.querySelector('#assignmentList .list-container');
    container.innerHTML = assignments.map(assn => `
        <div class="assignment-item" 
            onclick="selectAssignment('${assn.xszyid}', this)"
            data-id="${assn.xszyid}">
            <h4>${assn.bt}</h4>
            <p>课程：${assn.kcm}</p>
            <p>截止时间：${assn.jzsjStr}</p>
        </div>
    `).join('');
}

// 选择作业
function selectAssignment(id, element) {
    currentAssignment = id;
    document.querySelectorAll('.assignment-item').forEach(item => {
        item.classList.remove('selected');
    });
    element.classList.add('selected');
}

// 提交作业
async function submitAssignment() {
    if (!currentAssignment) {
        showSubmitStatus('请先选择作业', 'error');
        return;
    }

    const formData = new FormData();
    const nowAssignment=currentHomeworkList.find(item=>item.xszyid===currentAssignment);
    formData.append('assignment', JSON.stringify(nowAssignment));

    try {
        const response = await fetch('/edu/submit', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        
        if (data.success) {
            showSubmitStatus('提交成功', 'success');
        } else {
            showSubmitStatus(`提交失败: ${data.error}`, 'error');
        }
    } catch (error) {
        showSubmitStatus(`请求失败: ${error.message}`, 'error');
    }
}

// 状态提示函数
function showLoginStatus(msg, type) {
    const el = document.getElementById('loginStatus');
    el.textContent = msg;
    el.className = `status-${type}`;
}

function showSubmitStatus(msg, type) {
    const el = document.getElementById('submitStatus');
    el.textContent = msg;
    el.className = `status-${type}`;
}

async function playMilk() {
    
    await fetch('/play-milk', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ })
    });
    
}