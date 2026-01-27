import os, subprocess, json, smtplib, urllib.request, re, time
import xml.etree.ElementTree as ET
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime, timedelta

# 配置区
RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCIALMKvObZNtJ6AmdCLP7Lg"
KEYWORDS = ["The China Show", "Insight", "Asia Trade", "Bloomberg"]
HISTORY_FILE = "history.json"

def get_video_description(video_id):
    # 增加重试机制和延迟
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
    msg['From'] = f"BloombergBot <{sender}>" 
    msg['To'] = receiver
    msg['Subject'] = Header(f"【发现更新】{video_title}", 'utf-8')
    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())
        server.quit()
        print(f"✅ 邮件发送成功: {video_title}")
    except Exception as e: print(f"❌ 发信失败: {e}")

def main():
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
            published_str = entry.find('ns:published', ns).text # 格式: 2026-01-27T12:34:56+00:00
            
            # 只有匹配关键词且未发送过的才处理
            if any(k.lower() in title.lower() for k in KEYWORDS) and video_id not in history:
                # 检查发布时间，如果发布不到 40 分钟，先跳过，等下一轮抓取（为了等时间轴更新）
                pub_time = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                if datetime.now(pub_time.tzinfo) - pub_time < timedelta(minutes=40):
                    print(f"视频太新({title})，可能暂无时间轴，留待下轮抓取...")
                    continue

                print(f"开始处理: {title}")
                desc = get_video_description(video_id)
                # 增强版正则：支持 00:00, 0:00, 00:00:00 各种格式
                ts_matches = re.findall(r'(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(.*)', desc)
                
                report = [f"标题：{simple_translate(title)}\n", "【全量时间轴翻译】："]
                if ts_matches:
                    for ts, info in ts_matches: 
                        report.append(f"[{ts}] {simple_translate(info)}")
                else:
                    report.append("（注意：该视频官方简介暂无时间轴，可能为短片段）")
                    report.append(f"\n原简介参考：\n{simple_translate(desc[:500])}...")
                
                send_email("\n".join(report), title)
                history.append(video_id)
                count += 1
                if count >= 3: break 

        with open(HISTORY_FILE, 'w') as f: json.dump(history, f)
    except Exception as e: print(f"运行出错: {e}")

if __name__ == "__main__": main()
