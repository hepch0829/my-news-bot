import os
import subprocess
import json
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import re

# 配置区
KEYWORDS = ["The China Show", "Insight", "Asia Trade"]
HISTORY_FILE = "history.json"

def get_latest_videos():
    print("正在检查 YouTube 最新视频 (使用兼容模式)...")
    # 增加 --no-check-certificates 等稳定参数
    cmd = [
        'yt-dlp', 
        '--no-check-certificates',
        '--quiet',
        '--no-warnings',
        '--print', '%(title)s|%(id)s|%(description)s', 
        '--playlist-end', '10', 
        'https://www.youtube.com/@markets/videos'
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=60)
        if result.stderr:
            print(f"抓取警告: {result.stderr}")
        
        videos = []
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            print(f"成功抓取到 {len(lines)} 行数据")
            for line in lines:
                parts = line.split('|')
                if len(parts) >= 3:
                    videos.append({"title": parts[0], "id": parts[1], "desc": parts[2]})
        else:
            print("YouTube 返回数据为空，可能是被限制。")
        return videos
    except Exception as e:
        print(f"抓取过程发生错误: {e}")
        return []

def simple_translate(text):
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source='auto', target='zh-CN').translate(text)
    except:
        return text

def send_email(content, video_title):
    print(f"正在准备发送邮件: {video_title}")
    sender = os.environ.get("SENDER_EMAIL")
    password = os.environ.get("SENDER_PASS")
    receiver = os.environ.get("RECEIVER_EMAIL")
    
    if not all([sender, password, receiver]):
        print("错误：Secret 配置不完整，请检查 SENDER_EMAIL, SENDER_PASS, RECEIVER_EMAIL")
        return

    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = Header("Bloomberg监控助手", 'utf-8')
    msg['To'] = Header("主理人", 'utf-8')
    msg['Subject'] = Header(f"【新视频通知】{video_title}", 'utf-8')

    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())
        server.quit()
        print("✅ 邮件发送成功！")
    except Exception as e:
        print(f"❌ 邮件发送出错: {e}")

def main():
    print("--- 自动化任务开始 ---")
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w') as f: json.dump([], f)
    with open(HISTORY_FILE, 'r') as f:
        history = json.load(f)

    videos = get_latest_videos()
    
    if not videos:
        print("未获取到任何视频信息，任务终止。")
        return

    new_found = False
    for v in videos:
        # 判断标题是否包含关键字
        is_target = any(k.lower() in v['title'].lower() for k in KEYWORDS)
        if is_target:
            if v['id'] not in history:
                print(f"发现新目标视频: {v['title']}")
                # 提取时间轴并翻译
                timestamps = re.findall(r'(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(.*)', v['desc'])
                report = [f"标题：{simple_translate(v['title'])}\n", "时间轴："]
                if timestamps:
                    for ts, info in timestamps:
                        report.append(f"[{ts}] {simple_translate(info)}")
                else:
                    report.append("（原简介无时间轴，请自行查看）")
                
                send_email("\n".join(report), v['title'])
                history.append(v['id'])
                new_found = True
            else:
                print(f"已处理过，跳过: {v['title']}")

    if new_found:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)
    else:
        print("本次巡逻未发现需要推送的新节目。")
    print("--- 任务结束 ---")

if __name__ == "__main__":
    main()
