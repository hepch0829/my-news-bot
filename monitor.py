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
    # 抓取 Bloomberg Markets 频道最近 10 条视频
    cmd = ['yt-dlp', '--print', '%(title)s|%(id)s|%(description)s', '--playlist-end', '10', 'https://www.youtube.com/@markets/videos']
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    videos = []
    if result.stdout:
        for line in result.stdout.strip().split('\n'):
            parts = line.split('|')
            if len(parts) >= 3:
                videos.append({"title": parts[0], "id": parts[1], "desc": parts[2]})
    return videos

def simple_translate(text):
    """
    使用内置的免费翻译逻辑（通过 Google 翻译免 Key 接口）
    """
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source='auto', target='zh-CN').translate(text)
        return translated
    except Exception as e:
        return text + f" (翻译失败: {e})"

def process_content(v):
    title = v['title']
    desc = v['desc']
    
    # 提取时间轴
    # 匹配格式如 00:00:00 或 00:00 或 1:20:30
    timestamps = re.findall(r'(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(.*)', desc)
    
    zh_title = simple_translate(title)
    content_list = [f"【标题翻译】：{zh_title}\n", "【详细时间轴】："]
    
    if not timestamps:
        content_list.append("简介中未发现自带时间轴。")
    else:
        for ts, info in timestamps:
            zh_info = simple_translate(info)
            content_list.append(f"[{ts}] - {zh_info}")
            
    content_list.append("\n--- 监控助手自动生成 ---")
    return "\n".join(content_list)

def send_email(content, video_title):
    sender = os.environ["SENDER_EMAIL"]
    password = os.environ["SENDER_PASS"]
    receiver = os.environ["RECEIVER_EMAIL"]
    
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = Header("Bloomberg 自动监控助手", 'utf-8')
    msg['To'] = Header("自媒体主理人", 'utf-8')
    msg['Subject'] = Header(f"更新：{video_title}", 'utf-8')

    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465) # 如果是163邮箱，请改为 smtp.163.com
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())
        server.quit()
    except Exception as e:
        print(f"邮件发送失败: {e}")

def main():
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w') as f:
            json.dump([], f)
            
    with open(HISTORY_FILE, 'r') as f:
        history = json.load(f)

    videos = get_latest_videos()
    new_found = False
    
    for v in videos:
        if any(k.lower() in v['title'].lower() for k in KEYWORDS) and v['id'] not in history:
            print(f"处理新视频: {v['title']}")
            report = process_content(v)
            send_email(report, v['title'])
            history.append(v['id'])
            new_found = True

    if new_found:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)

if __name__ == "__main__":
    main()
