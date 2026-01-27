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
    print("正在检查 YouTube 最新视频...")
    # 抓取 Bloomberg Markets 频道最近 10 条视频
    cmd = ['yt-dlp', '--print', '%(title)s|%(id)s|%(description)s', '--playlist-end', '10', 'https://www.youtube.com/@markets/videos']
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    videos = []
    if result.stdout:
        lines = result.stdout.strip().split('\n')
        print(f"找到 {len(lines)} 个视频元数据")
        for line in lines:
            parts = line.split('|')
            if len(parts) >= 3:
                videos.append({"title": parts[0], "id": parts[1], "desc": parts[2]})
    return videos

def simple_translate(text):
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source='auto', target='zh-CN').translate(text)
    except:
        return text

def process_content(v):
    print(f"正在处理视频: {v['title']}")
    title = v['title']
    desc = v['desc']
    timestamps = re.findall(r'(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(.*)', desc)
    zh_title = simple_translate(title)
    content_list = [f"【标题翻译】：{zh_title}\n", "【详细时间轴】："]
    if not timestamps:
        content_list.append("简介中未发现自带时间轴。")
    else:
        for ts, info in timestamps:
            content_list.append(f"[{ts}] - {simple_translate(info)}")
    return "\n".join(content_list)

def send_email(content, video_title):
    print(f"正在尝试发送邮件: {video_title}")
    sender = os.environ.get("SENDER_EMAIL")
    password = os.environ.get("SENDER_PASS")
    receiver = os.environ.get("RECEIVER_EMAIL")
    
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = Header("Bloomberg监控助手", 'utf-8')
    msg['To'] = Header("主理人", 'utf-8')
    msg['Subject'] = Header(f"更新：{video_title}", 'utf-8')

    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())
        server.quit()
        print("邮件发送成功！")
    except Exception as e:
        print(f"邮件发送出错: {e}")

def main():
    print("--- 任务开始 ---")
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w') as f:
            json.dump([], f)
    with open(HISTORY_FILE, 'r') as f:
        history = json.load(f)

    videos = get_latest_videos()
    new_found = False
    
    for v in videos:
        is_target = any(k.lower() in v['title'].lower() for k in KEYWORDS)
        if is_target and v['id'] not in history:
            report = process_content(v)
            send_email(report, v['title'])
            history.append(v['id'])
            new_found = True
        elif is_target:
            print(f"跳过已发送的视频: {v['title']}")

    if new_found:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)
    print("--- 任务结束 ---")

if __name__ == "__main__":
    main()
