#!/usr/bin/env python3
"""
Antigravity TechLab - Auto Blogger Engine
Engine for generating niche technical blog posts using Gemini 3.5 Flash and Hugo.
Author: Automation Engineer & AI Developer
"""

import os
import datetime
import google.generativeai as genai
from git import Repo

# System configurations
TOPICS_FILE = "topics.txt"
DONE_TOPICS_FILE = "topics_done.txt"


def log_banner(message: str):
    """Print a styled banner for console visibility."""
    border = "=" * len(message)
    print(f"\n{border}")
    print(message)
    print(f"{border}\n")


def load_api_key() -> str:
    """
    Safely load and validate the Gemini API Key from environment variables.
    Exits the process with clear instructions if keys are missing.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        
    if not api_key:
        print("==================================================================")
        print("❌ ERROR: Gemini API Key not found in system environment!")
        print("Please verify you have added 'GEMINI_API_KEY' to Repository Secrets.")
        print("==================================================================")
        exit(1)
    return api_key


def read_topics_queue() -> tuple[list[str], str, list[str]]:
    """
    Read the manual topics queue from topics.txt.
    Returns:
        tuple: (all_topics, current_topic, remaining_topics)
    """
    if os.path.exists(TOPICS_FILE):
        with open(TOPICS_FILE, "r", encoding="utf-8") as f:
            topics = [line.strip() for line in f if line.strip()]
    else:
        topics = []
        
    if topics:
        topic = topics[0]
        remaining = topics[1:]
        print(f"Mode: Manual Queue -> Picked topic: '{topic}'")
        return topics, topic, remaining
    return [], "", []


def get_autopilot_prompt(done_topics_file: str) -> str:
    """
    Construct the prompt for generating a new topic when the queue is empty.
    Avoids duplicate topics by referencing done_topics_file history.
    """
    past_topics = []
    if os.path.exists(done_topics_file):
        with open(done_topics_file, "r", encoding="utf-8") as f:
            past_topics = [line.strip() for line in f if line.strip()]
            
    # Include up to 15 recent topics for context
    past_topics_context = "\n".join(past_topics[-15:])
    
    return f"""
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


def generate_article_prompt(topic: str) -> str:
    """Construct the main prompt for writing the full technical article."""
    return f"""
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
6. การสอดแทรกลิงก์แนะนำสินค้าเพื่อสร้างรายได้ (Monetization & Affiliate Marketing):
   - ในส่วนท้ายของบทความ หรือระหว่างเนื้อหาที่เหมาะสม ให้สอดแทรกคำแนะนำอุปกรณ์คอมพิวเตอร์ ฮาร์ดแวร์ หรือเครื่องมือที่เกี่ยวข้องและช่วยเพิ่มประสิทธิภาพได้จริงตามหัวข้อนั้นๆ อย่างเป็นธรรมชาติ (เช่น สาย LAN คุณภาพสูง, อุปกรณ์ช่วยระบายความร้อน, Router Gaming เป็นต้น)
   - ให้แนบลิงก์จำลอง (Affiliate Link Placeholder) สำหรับสั่งซื้อสินค้านั้นๆ เพื่อให้ผู้อ่านคลิกไปชมสินค้าได้ โดยใช้รูปแบบลิงก์ของ Shopee/Lazada หรือ Amazon ในรูปแบบ Markdown: `[ดูรายละเอียดอุปกรณ์หรือสั่งซื้อได้ที่นี่](https://shopee.co.th/search?keyword=...)`
"""


def save_article_file(topic: str, content: str, slug: str) -> str:
    """Save front matter and article body to a Hugo content markdown file."""
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
    return filename


def update_queues(topic: str, remaining_topics: list[str], topics_exist: bool):
    """Log the completed topic and refresh queue files."""
    # Write to done history
    with open(DONE_TOPICS_FILE, "a", encoding="utf-8") as f:
        f.write(topic + "\n")
        
    # Update topics queue
    if topics_exist:
        with open(TOPICS_FILE, "w", encoding="utf-8") as f:
            for t in remaining_topics:
                f.write(t + "\n")
        print(f"Updated manual queue queue in {TOPICS_FILE}")
    else:
        # Clear queue file to stay ready for new manual entry
        if os.path.exists(TOPICS_FILE):
            with open(TOPICS_FILE, "w", encoding="utf-8") as f:
                pass
    print(f"Logged completed topic to {DONE_TOPICS_FILE}")


def run_git_automation(filename: str):
    """Handle Git operations for local workflow runs."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print("Running on GitHub Actions. Skipping Python Git Automation to let YAML handle it.")
        return
        
    try:
        print("Initializing Git local repository tracking...")
        repo = Repo(".")
        
        # Add generated files
        repo.git.add(filename)
        if os.path.exists(TOPICS_FILE):
            repo.git.add(TOPICS_FILE)
        if os.path.exists(DONE_TOPICS_FILE):
            repo.git.add(DONE_TOPICS_FILE)
            
        commit_msg = f"Feat: auto-generate post - {filename.split('/')[-1]}"
        repo.index.commit(commit_msg)
        print(f"Local commit successful: '{commit_msg}'")
        
        # Push to remote repository
        if repo.remotes:
            print("Pushing commits to remote origin branch...")
            origin = repo.remote(name="origin")
            origin.push()
            print("Successfully pushed to remote!")
        else:
            print("Notice: No remote origin detected. Changes saved locally.")
    except Exception as e:
        print(f"Git automation encountered an error: {e}")


def main():
    log_banner("🚀 Starting Antigravity AutoTech Blogger Engine 🚀")
    
    # 1. Authorize Gemini API
    api_key = load_api_key()
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3.5-flash')
    
    # 2. Pick Niche Topic
    topics, topic, remaining = read_topics_queue()
    if not topic:
        print("Mode: Auto-Pilot -> Queue empty. AI editor will generate a new topic.")
        niche_prompt = get_autopilot_prompt(DONE_TOPICS_FILE)
        topic_response = model.generate_content(niche_prompt)
        topic = topic_response.text.strip().replace('"', '').replace("'", "")
        print(f"Generated new topic: '{topic}'")
        
    # 3. Generate URL English Slug
    print("Generating SEO URL slug...")
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
    print(f"Slug: {slug}")
    
    # 4. Generate Content Article
    print("Generating comprehensive article body...")
    article_prompt = generate_article_prompt(topic)
    response = model.generate_content(article_prompt)
    content = response.text
    
    # 5. Write to File
    filename = save_article_file(topic, content, slug)
    print(f"Successfully generated file: {filename}")
    
    # 6. Update History and Queues
    update_queues(topic, remaining, bool(topics))
    
    # 7. Run Git updates
    run_git_automation(filename)
    
    log_banner("🎉 Process Completed Successfully 🎉")


if __name__ == "__main__":
    main()
