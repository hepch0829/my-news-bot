import os
import subprocess
import json
import smtplib
import urllib.request
import xml.etree.ElementTree as ET
from email.mime.text import MIMEText
from email.header import Header
import re

# 配置区
# Bloomberg Markets 的频道 ID: UCIALMKvObZNtJ6AmdCLP7Lg
RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCIALMKvObZNtJ6AmdCLP7Lg"
KEYWORDS = ["The China Show", "Insight", "Asia Trade", "Bloomberg"]
HISTORY_FILE = "history.json"

def get_latest_videos_rss():
    print("正在通过 RSS 订阅源获取最新视频...")
    try:
        # 抓取 RSS XML 数据
        response = urllib.request.urlopen(RSS_URL, timeout=30)
        data = response.read().decode('utf-8')
        root = ET.fromstring(data)
        
        # XML 命名空间处理
        ns = {'ns': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
        
        videos = []
        for entry in root.findall('ns:entry', ns):
            title = entry.find('ns:title', ns).text
            video_id = entry.find('yt:videoId', ns).text
            # RSS 不带详细简介，我们需要用 yt-dlp 单独获取这个视频的简介
            videos.append({"title": title, "id": video_id})
        
        print(f"RSS 抓取成功，找到 {len(videos)} 个视频")
        return videos
    except Exception as e:
        print(f"RSS 抓取失败: {e}")
        return []

def get_video_description(video_id):
    """单独获取单个视频的简介，避开频率限制"""
    print(f"正在获取视频简介: {video_id}")
    cmd = ['yt-dlp', '--get-description', f'https://www.youtube.com/watch?v={video_id}']
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    return result.stdout if result.returncode == 0 else ""

def simple_translate(text):
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source='auto', target='zh-CN').translate(text)
    except:
        return text

def send_email(content, video_title):
    print(f"正在发送邮件: {video_title}")
    sender = os.environ.get("SENDER_EMAIL")
    password = os.environ.get("SENDER_PASS")
    receiver = os.environ.get("RECEIVER_EMAIL")
    
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = Header("Bloomberg监控助手", 'utf-8')
    msg['To'] = Header("主理人", 'utf-8')
    msg['Subject'] = Header(f"【新视频】{video_title}", 'utf-8')

    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())
        server.quit()
        print("✅ 成功！")
    except Exception as e:
        print(f"❌ 失败: {e}")

def main():
    print("--- RSS 监控任务开始 ---")
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w') as f: json.dump([], f)
    with open(HISTORY_FILE, 'r') as f:
        history = json.load(f)

    videos = get_latest_videos_rss()
    new_found = False
    
    for v in videos:
        # 判断标题是否命中关键字
        if any(k.lower() in v['title'].lower() for k in KEYWORDS) and v['id'] not in history:
            print(f"发现新目标: {v['title']}")
            
            # 获取简介并翻译时间轴
            desc = get_video_description(v['id'])
            timestamps = re.findall(r'(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(.*)', desc)
            
            report = [f"标题：{simple_translate(v['title'])}\n", "时间轴："]
            if timestamps:
                for ts, info in timestamps:
                    report.append(f"[{ts}] {simple_translate(info)}")
            else:
                report.append("（该视频简介中未提供时间轴）")
            
            send_email("\n".join(report), v['title'])
            history.append(v['id'])
            new_found = True

    if new_found:
        with open(HISTORY_FILE, 'w') as f: json.dump(history, f)
    else:
        print("本次巡逻未发现新内容。")
    print("--- 任务结束 ---")

if __name__ == "__main__":
    main()
