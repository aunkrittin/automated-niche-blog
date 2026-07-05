import os
import datetime
import google.generativeai as genai
from git import Repo

# ตั้งค่า API Key (ดึงจาก Environment Variable เพื่อความปลอดภัย)
API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
genai.configure(api_key=API_KEY)

# ไฟล์ระบบ Content Plan
TOPICS_FILE = "topics.txt"
DONE_TOPICS_FILE = "topics_done.txt"

model = genai.GenerativeModel('gemini-2.5-flash')

# 1. จัดการเรื่องหัวข้อบทความ (Queue & Auto-Pilot)
topic = ""
remaining_topics = []

# อ่านคิวหัวข้อจากไฟล์ (หากมี)
if os.path.exists(TOPICS_FILE):
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        topics = [line.strip() for line in f if line.strip()]
else:
    topics = []

if topics:
    # โหมดกำหนดเอง: มีคิวหัวข้ออยู่ ให้หยิบหัวข้อแรกมาทำ
    topic = topics[0]
    remaining_topics = topics[1:]
    print(f"Mode: Manual Queue -> Picked topic: '{topic}'")
else:
    # โหมด Auto-Pilot: ไม่มีคิวในไฟล์ ให้ Gemini คิดหัวข้อใหม่ที่สอดคล้องกับแนวบล็อกเอง!
    print("Mode: Auto-Pilot -> Topics file is empty or not found. Gemini will generate a new topic.")
    
    # อ่านหัวข้อที่เคยเขียนไปแล้วเพื่อหลีกเลี่ยงการเขียนหัวข้อซ้ำ
    past_topics = []
    if os.path.exists(DONE_TOPICS_FILE):
        with open(DONE_TOPICS_FILE, "r", encoding="utf-8") as f:
            past_topics = [line.strip() for line in f if line.strip()]
    
    # ดึงหัวขอล่าสุดสูงสุด 15 หัวข้อ เพื่อเป็นบริบทและแนวทางให้ AI
    past_topics_context = "\n".join(past_topics[-15:])
    
    niche_prompt = f"""
คุณคือหัวหน้าบรรณาธิการของบล็อกเทคโนโลยี "Antigravity TechLab"
บล็อกนี้มีกลุ่มเป้าหมายเฉพาะทาง (Niche Blog) ที่เน้นเขียนบทความเจาะลึกด้านเทคนิคเกี่ยวกับ:
1. การปรับแต่งระบบปฏิบัติการ Windows (Windows Registry, Services, Debloating)
2. การปรับปรุงประสิทธิภาพเครือข่ายและการลดค่า Ping (Network, TCP/IP, DNS, Packet Loss Fix)
3. การประหยัด RAM/CPU และการรีดเฟรมเรตสตรีมเมอร์และเกมเมอร์ (System Performance & Game Optimization)

นี่คือรายชื่อหัวข้อที่บล็อกนี้เคยเขียนและเผยแพร่ไปแล้ว (ห้ามคิดหัวข้อซ้ำหรือคล้ายคลึงกับหัวข้อเหล่านี้เด็ดขาด):
{past_topics_context}

หน้าที่ของคุณ: จงคิดหัวข้อบทความเทคนิคเชิงลึกชิ้นใหม่ขึ้นมา 1 หัวข้อ ที่ตรงกับสไตล์ของบล็อก เจาะลึก มีรายละเอียดทางเทคนิคที่เป็นประโยชน์ และน่าดึงดูดสำหรับผู้ใช้งานคอมพิวเตอร์ขั้นสูง (Advanced Users)
ข้อกำหนดในการคิดหัวข้อ (CRITICAL SAFETY):
- หัวข้อที่คิดขึ้นต้องอยู่บนพื้นฐานความปลอดภัยสูงสุดของคอมพิวเตอร์ผู้อ่าน หลีกเลี่ยงหัวข้อที่มีความเสี่ยงสูงจนทำให้ระบบปฏิบัติการเสียหายหรือบูตไม่ขึ้น
- ตอบกลับมาเฉพาะชื่อหัวข้อภาษาไทย 1 บรรทัดสั้นๆ เท่านั้น
- ห้ามมีคำอธิบาย เกริ่นนำ ทักทาย หรือลงท้ายใดๆ ทั้งสิ้น
"""
    topic_response = model.generate_content(niche_prompt)
    topic = topic_response.text.strip().replace('"', '').replace("'", "")
    print(f"Generated new topic: '{topic}'")

# 2. ให้ Gemini เจนเนอเรต URL Slug จากหัวข้อภาษาไทย
print("Generating URL Slug...")
slug_prompt = f"""
จงแปลงหัวข้อภาษาไทยนี้ให้เป็น URL slug ภาษาอังกฤษสั้นๆ ที่เหมาะสม
ข้อกำหนด:
- ใช้ตัวพิมพ์เล็กทั้งหมด
- คั่นระหว่างคำด้วยเครื่องหมายขีดกลาง (-) เท่านั้น
- ห้ามตอบคำอื่นนอกจาก slug ที่ได้ (เช่น 'windows-dns-lag-fix')
หัวข้อ: "{topic}"
"""
slug_response = model.generate_content(slug_prompt)
slug = slug_response.text.strip().replace(" ", "-").replace('"', "").replace("'", "").lower()
print(f"Generated Slug: {slug}")

# 3. ให้ Gemini เจนเนอเรตเนื้อหาบทความเชิงลึก
print("Generating article content using Gemini...")
prompt = f"""
คุณคือผู้เชี่ยวชาญด้าน System Architecture, Network Optimization และ Game Server Developer
หน้าที่ของคุณคือเขียนบทความบล็อกเชิงลึกแบบมืออาชีพในหัวข้อ: "{topic}"

ข้อกำหนดในการเขียน:
1. ภาษาและโทน: ใช้ภาษาไทยที่เป็นกันเองแต่อัดแน่นด้วยข้อมูลทางเทคนิค (Tech-savvy)
2. โครงสร้าง: ใช้ Markdown ให้ถูกต้อง ต้องมี Headings (##, ###) แบ่งหัวข้อชัดเจน
3. โค้ดสคริปต์: หากมีโค้ด ต้องครอบด้วย Code Block (```) พร้อมระบุภาษา
4. ห้ามมีคำเกริ่นนำหรือคำลงท้ายแบบ AI ให้ตอบกลับมาเฉพาะเนื้อหาเท่านั้น
5. ความถูกต้องและความปลอดภัยของข้อมูล (CRITICAL SAFETY):
   - ข้อมูลเชิงลึกและแนวทางทั้งหมดต้องมีความแม่นยำทางเทคนิค 100% ห้ามมโน เดา หรือให้ข้อมูลที่คลาดเคลื่อนโดยเด็ดขาด (No Hallucination)
   - สคริปต์ โค้ด หรือขั้นตอนปรับแต่งทั้งหมดต้องรับประกันความปลอดภัยสูงสุดต่อคอมพิวเตอร์ของผู้อ่าน ห้ามนำเสนอขั้นตอน/คำสั่งที่เสี่ยงทำให้ระบบไม่เสถียร บูตไม่ขึ้น หรือระบบล่มเด็ดขาด
   - หากมีการสอนปรับแต่งส่วนสำคัญที่มีความเสี่ยง (เช่น การแก้ไข Registry หรือ ปิด Services บางตัว) จะต้องมีกล่องข้อความแจ้งเตือนภัย/ข้อควรระวัง (Warning Alert) กำกับอย่างเด่นชัด และแนะนำให้ผู้อ่านทำการสำรองข้อมูล (Backup) หรือสร้าง System Restore Point ก่อนเริ่มลงมือทำทุกครั้ง
"""
response = model.generate_content(prompt)
content = response.text

# 4. จัดการโครงสร้างไฟล์และ Front Matter
date_str = datetime.datetime.now().strftime("%Y-%m-%d")
filename = f"content/posts/{date_str}-{slug}.md"

front_matter = f"""---
title: "{topic}"
date: {datetime.datetime.now().astimezone().isoformat()}
tags: ["Optimization", "Tech"]
draft: false
---

"""

os.makedirs("content/posts", exist_ok=True)
with open(filename, "w", encoding="utf-8") as f:
    f.write(front_matter + content)

print(f"Success! Article written to {filename}")

# 5. บันทึกประวัติและอัปเดตไฟล์คิว
with open(DONE_TOPICS_FILE, "a", encoding="utf-8") as f:
    f.write(topic + "\n")

# อัปเดตไฟล์คิวกรณีที่มีคิวรันอยู่
if topics:
    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        for t in remaining_topics:
            f.write(t + "\n")
    print(f"Updated queue in {TOPICS_FILE}")
else:
    # เคลียร์ไฟล์ topics.txt ให้ว่างเปล่าเพื่อรอรับคิวถัดไปถ้ามีการใส่ข้อมูลเพิ่ม
    if os.path.exists(TOPICS_FILE):
        with open(TOPICS_FILE, "w", encoding="utf-8") as f:
            pass

print(f"Logged completed topic to {DONE_TOPICS_FILE}")

# 6. Git Automation
try:
    print("Starting Git tracking...")
    repo = Repo(".")
    
    # Add generated file and commit
    repo.git.add(filename)
    if os.path.exists(TOPICS_FILE):
        repo.git.add(TOPICS_FILE)
    if os.path.exists(DONE_TOPICS_FILE):
        repo.git.add(DONE_TOPICS_FILE)
        
    commit_message = f"Feat: auto-generate post - {topic}"
    repo.index.commit(commit_message)
    print(f"Committed changes locally with message: '{commit_message}'")
    
    # Check if remote repository exists
    if repo.remotes:
        print("Pushing changes to remote repository...")
        origin = repo.remote(name="origin")
        origin.push()
        print("Success! Pushed to remote repository.")
    else:
        print("Notice: No remote 'origin' detected. Changes were committed locally.")
except Exception as e:
    print(f"Git automation encountered an error: {e}")
