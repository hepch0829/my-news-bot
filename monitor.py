import os, subprocess, json, smtplib, urllib.request, re
import xml.etree.ElementTree as ET
from email.mime.text import MIMEText
from email.header import Header

# 配置区
RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCIALMKvObZNtJ6AmdCLP7Lg"
KEYWORDS = ["The China Show", "Insight", "Asia Trade"] # 建议删掉测试用的 Bloomberg
HISTORY_FILE = "history.json"

def get_video_description(video_id):
    cmd = ['yt-dlp', '--no-warnings', '--get-description', f'https://www.youtube.com/watch?v={video_id}']
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    return result.stdout if result.returncode == 0 else ""

def simple_translate(text):
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source='auto', target='zh-CN').translate(text)
    except: return text

def send_email(content, video_title):
    sender, password, receiver = os.environ.get("SENDER_EMAIL"), os.environ.get("SENDER_PASS"), os.environ.get("RECEIVER_EMAIL")
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'], msg['To'], msg['Subject'] = Header("Bloomberg监控", 'utf-8'), Header("主理人", 'utf-8'), Header(f"【新视频】{video_title}", 'utf-8')
    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())
        server.quit()
        print(f"✅ 邮件已发送: {video_title}")
    except Exception as e: print(f"❌ 发送失败: {e}")

def main():
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w') as f: json.dump([], f)
    with open(HISTORY_FILE, 'r') as f: history = json.load(f)

    try:
        data = urllib.request.urlopen(RSS_URL, timeout=30).read().decode('utf-8')
        root = ET.fromstring(data)
        ns = {'ns': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
        
        new_found = False
        # 倒序检查（从旧到新），确保即使多次更新也能按顺序记录
        for entry in reversed(root.findall('ns:entry', ns)):
            title = entry.find('ns:title', ns).text
            video_id = entry.find('yt:videoId', ns).text
            
            if any(k.lower() in title.lower() for k in KEYWORDS) and video_id not in history:
                desc = get_video_description(video_id)
                timestamps = re.findall(r'(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(.*)', desc)
                report = [f"标题：{simple_translate(title)}\n", "时间轴："]
                if timestamps:
                    for ts, info in timestamps: report.append(f"[{ts}] {simple_translate(info)}")
                else: report.append("（原简介无时间轴）")
                
                send_email("\n".join(report), title)
                history.append(video_id)
                new_found = True
                break # 每次只发一个最核心的，防止被封号

        if new_found:
            with open(HISTORY_FILE, 'w') as f: json.dump(history, f)
    except Exception as e: print(f"运行出错: {e}")

if __name__ == "__main__": main()
