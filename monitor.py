import os, subprocess, json, smtplib, urllib.request, re
import xml.etree.ElementTree as ET
from email.mime.text import MIMEText
from email.header import Header

# 配置区
RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCIALMKvObZNtJ6AmdCLP7Lg"
# 加上 Bloomberg 关键字进行第一次“必中”测试，收到信后再改回来
KEYWORDS = ["The China Show", "Insight", "Asia Trade", "Bloomberg"]
HISTORY_FILE = "history.json"

def get_video_description(video_id):
    print(f"正在抓取简介: {video_id}")
    cmd = ['yt-dlp', '--no-warnings', '--get-description', f'https://www.youtube.com/watch?v={video_id}']
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    return result.stdout if result.returncode == 0 else ""

def simple_translate(text):
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source='auto', target='zh-CN').translate(text)
    except: return text

def send_email(content, video_title):
    sender = os.environ.get("SENDER_EMAIL")
    password = os.environ.get("SENDER_PASS")
    receiver = os.environ.get("RECEIVER_EMAIL")
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = Header("Bloomberg助手", 'utf-8')
    msg['To'] = Header("主理人", 'utf-8')
    msg['Subject'] = Header(f"【发现更新】{video_title}", 'utf-8')
    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())
        server.quit()
        print(f"✅ 邮件已发出: {video_title}")
    except Exception as e: print(f"❌ 发信失败: {e}")

def main():
    print("--- 任务开始 ---")
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w') as f: json.dump([], f)
    with open(HISTORY_FILE, 'r') as f: history = json.load(f)

    try:
        req = urllib.request.Request(RSS_URL, headers={'User-Agent': 'Mozilla/5.0'})
        data = urllib.request.urlopen(req, timeout=30).read().decode('utf-8')
        root = ET.fromstring(data)
        ns = {'ns': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
        
        count = 0
        for entry in root.findall('ns:entry', ns):
            title = entry.find('ns:title', ns).text
            video_id = entry.find('yt:videoId', ns).text
            
            if any(k.lower() in title.lower() for k in KEYWORDS) and video_id not in history:
                print(f"命中目标: {title}")
                desc = get_video_description(video_id)
                ts_matches = re.findall(r'(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(.*)', desc)
                
                report = [f"标题：{simple_translate(title)}\n", "时间轴索引："]
                if ts_matches:
                    for ts, info in ts_matches: report.append(f"[{ts}] {simple_translate(info)}")
                else: report.append("（原视频简介无自带时间轴）")
                
                send_email("\n".join(report), title)
                history.append(video_id)
                count += 1
                if count >= 3: break # 第一次测试最多只发3个，防止封号

        with open(HISTORY_FILE, 'w') as f: json.dump(history, f)
        print(f"任务结束，本次新增发送: {count}")
    except Exception as e: print(f"发生错误: {e}")

if __name__ == "__main__":
    main()
