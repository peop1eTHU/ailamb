import json
from bs4 import BeautifulSoup
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')           # 无头模式
options.add_argument('--disable-gpu')        # 关闭GPU（有些版本的Chrome需要）
options.add_argument('--no-sandbox')         # 在root用户下运行Chrome时需要
options.add_argument('--disable-dev-shm-usage')  # 避免/dev/shm空间不足


def wlxt_login(username,password):

    driver = webdriver.Chrome(options=options)

    driver.get("https://learn.tsinghua.edu.cn/f/login")

    WebDriverWait(driver,10).until(
        EC.visibility_of_element_located((By.ID, "loginButtonId"))
    )

# 找到输入框并输入账号和密码（根据实际网页元素的 id/name/class）
    username_input = driver.find_element(By.NAME, "i_user")
    password_input = driver.find_element(By.NAME, "i_pass")

    username_input.send_keys(username)
    password_input.send_keys(password)

# 提交表单（可能是点击按钮，也可能是按 Enter）
    try:
        username_input.send_keys(Keys.ENTER)
    except Exception:
        pass

# 等待登录结果页面加载
    WebDriverWait(driver, 10).until(
        EC.url_contains("/index")
    )

# 获取 cookies
    cookies = driver.get_cookies()

# 转换为 requests 可用的 cookie 字典格式
    cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}

    print(cookie_dict)

    index_url = "https://learn.tsinghua.edu.cn/f/wlxt/index/course/student/"

    response = requests.get(index_url, cookies=cookie_dict)
    soup = BeautifulSoup(response.text, "html.parser")
# 找到含有 csrf 的 input 元素
    input_tag = soup.find("input", {"id": "up-btn-ok"})

# 用正则提取 _csrf 参数
    match = re.search(r"_csrf=([\w-]+)", response.text)
    csrf_token=""
    if match:
        csrf_token = match.group(1)
        print("CSRF Token:", csrf_token)
    else:
        print("CSRF Token not found")

    match = re.search(r'<input[^>]*id="currentSemester"[^>]*value="([\d\-]+)"', response.text)
    semester = ""
    if match:
        semester = match.group(1)
        print(semester)
    else:
        print("no semester found")
    driver.quit()
    return cookie_dict, csrf_token, semester

def get_json(url, cookie_dict):
    print("getting:",url)
    response = requests.get(url,cookies=cookie_dict)
    if response.status_code == 200:
        data = response.json()  # 自动解析 JSON
        return data
    else:
        print("请求失败，状态码：", response.status_code)

def wlxt_get_homework(cookie_dict, csrf_token, semester):

    classes = get_json("https://learn.tsinghua.edu.cn/b/wlxt/kc/v_wlkc_xs_xkb_kcb_extend/student/loadCourseBySemesterId/"
                    +semester+"/zh?_csrf="+csrf_token, cookie_dict)

    if classes is None:
        print("no classes get")
        exit()
    hw_list = []
    for aclass in classes["resultList"]:
        wj = get_json("https://learn.tsinghua.edu.cn/b/wlxt/kczy/zy/student/index/zyListWj?"+
                    "wlkcid="+aclass["wlkcid"]+
                    "&size=50"+
                    "&_csrf="+csrf_token, cookie_dict)
        yjwg = get_json("https://learn.tsinghua.edu.cn/b/wlxt/kczy/zy/student/index/zyListYjwg?"+
                    "wlkcid="+aclass["wlkcid"]+
                    "&size=50"+
                    "&_csrf="+csrf_token, cookie_dict)
    
        if wj:
            for hw in wj['object']['aaData']:
                if(time.time()*1000 < hw['jzsj']):
                    hw['kcm']=aclass['kcm']
                    hw_list.append(hw)

        if yjwg:
            for hw in yjwg['object']['aaData']:
                if(time.time()*1000 < hw['jzsj']):
                    hw['kcm']=aclass['kcm']
                    hw_list.append(hw)

    return hw_list

def wlxt_send_homework(cookie_dict, csrf_token, semester, hw, filepath):

    print(hw)
    hw = json.loads(hw)

    print(cookie_dict)
    driver = webdriver.Chrome(options=options)


    url = "https://learn.tsinghua.edu.cn/f/wlxt/kczy/zy/student/viewZy?"+\
        "wlkcid="+hw['wlkcid']+\
        "&zyid="+hw['zyid']+\
        "&xszyid="+hw['xszyid']+"&sfgq=0"
    print(url)
    driver.get(url)

    for key in cookie_dict:
        driver.add_cookie({'name':key,'value':cookie_dict[key]})

    driver.refresh()
    
    WebDriverWait(driver,10).until(
        EC.visibility_of_element_located((By.ID, "saveBtn"))
    )
    print("saveBtn found")
    submit_button = driver.find_element(By.ID, "saveBtn")
    submit_button.click()
    WebDriverWait(driver,10).until(
        EC.presence_of_element_located((By.ID, "fileupload"))
    )

    print("fileupload found")
    upload_input = driver.find_element(By.ID, "fileupload")

    print("uploading",filepath)
    upload_input.send_keys(filepath)


    WebDriverWait(driver,10).until(
        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '删除')]"))
    )
    print("delete found")
    submit_file_button = driver.find_element(By.XPATH, '//input[@value="提交"]')

    submit_file_button.click()
    print("waiting")
    try:
        # 等待最多10秒，直到包含“作业提交成功”的元素出现在页面上
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '提交作业成功')]"))
        )
        print("作业提交成功提示已出现！")
    except:
        print("超时未出现提交成功提示")
    finally:
        driver.quit()


