---
title: "เจาะลึก Windows Multimedia Class Scheduler (MMCSS): ปรับแต่งระบบจัดสรรลำดับความสำคัญ CPU และ Network สำหรับเกมเมอร์และสตรีมเมอร์"
date: 2026-07-07T04:40:48.183937+00:00
tags: ["Optimization", "Tech"]
draft: false
---

# เจาะลึก Windows Multimedia Class Scheduler (MMCSS): ปรับแต่งระบบจัดสรรลำดับความสำคัญ CPU และ Network สำหรับเกมเมอร์และสตรีมเมอร์

สำหรับเกมเมอร์ระดับฮาร์ดคอร์และสตรีมเมอร์ที่ต้องการรีดเฟรมเรตทุกเฟรม และลดค่า Latency (Ping) ให้ต่ำที่สุดในระดับมิลลิวินาที การปรับแต่งกราฟิกในการ์ดจอหรือการ Overclock CPU อาจยังไม่เพียงพอ เพราะเบื้องหลังระบบปฏิบัติการ Windows มีสถาปัตยกรรมหนึ่งที่คอยควบคุมระบบการทำงานทั้งหมด นั่นคือ **Multimedia Class Scheduler Service (MMCSS)**

บทความนี้จะพาทุกคนไปเจาะลึกการทำงานของ MMCSS ในระดับ System Architecture เรียนรู้วิธีการทำงานของมัน และแจกสูตรการปรับแต่ง Registry เพื่อรีดประสิทธิภาพสูงสุดสำหรับเล่นเกมและสตรีมมิ่งอย่างปลอดภัย 100%

---

## 1. MMCSS คืออะไร? สถาปัตยกรรมเบื้องหลังการจัดสรรทรัพยากรของ Windows

**Multimedia Class Scheduler (MMCSS)** เป็นบริการ (Service) ของ Windows (เปิดตัวครั้งแรกใน Windows Vista และยังคงใช้งานใน Windows 10 และ 11) มีหน้าที่สำคัญคือ **"ทำให้แน่ใจว่าแอปพลิเคชันมัลติมีเดีย (เช่น วิดีโอสตรีม, เสียง, และเกม) ได้รับการจัดสรรรอบการทำงานของ CPU (CPU Cycles) อย่างต่อเนื่องและไม่สะดุด"**

```
+-------------------------------------------------------------------+
|                         Windows OS Kernel                         |
+-------------------------------------------------------------------+
                                  |
         +------------------------+------------------------+
         |                                                 |
         v                                                 v
   [Normal Threads]                                 [MMCSS Registered]
 (Office, Browsers, etc.)                         (Audio, Video, Games)
   Priority: 1 - 15                                 Boosted Priority: Up to 26
```

### กลไกการทำงานของ MMCSS:
1. **Thread Priority Boosting:** โดยทั่วไป Windows จะจัดลำดับความสำคัญของ Thread (Priority Level) อยู่ที่ 0-31 โดยทั่วไปแอปทั่วไปจะอยู่ที่ระดับ 8 (Normal) แต่เมื่อแอปพลิเคชันที่ลงทะเบียนกับ MMCSS (เช่น เกม หรือ OBS) ทำงาน MMCSS จะดึงลำดับความสำคัญของ Thread นั้นขึ้นไปอยู่ที่ระดับ **15 ถึง 26** เพื่อการันตีว่า CPU จะประมวลผลงานชิ้นนี้ก่อน
2. **Resource Reservation:** ตามค่าเริ่มต้น MMCSS จะกันทรัพยากร CPU ไว้ประมาณ 20% ให้กับงานเบื้องหลัง (Background Tasks) เพื่อไม่ให้ระบบค้าง และเหลืออีก 80% ให้กับงานมัลติมีเดียที่กำลังทำงานอยู่ (Foreground Multimedia)
3. **Network Throttling:** นี่คือ "จุดตาย" สำหรับเกมเมอร์ เพราะ Windows ออกแบบมาว่า เมื่อมีการประมวลผลสื่อมัลติมีเดียที่มีความละเอียดสูง Network Driver อาจส่งผลกระทบต่อประสิทธิภาพ CPU (ผ่านทาง DPC หรือ Deferred Procedure Calls) Windows จึงทำการ **จำกัดปริมาณการประมวลผลแพ็กเก็ตเครือข่ายที่ไม่ใช่มัลติมีเดียไว้ที่ 10 แพ็กเก็ตต่อมิลลิวินาที** ส่งผลให้เกิดอาการ Ping สวิง, Packet Loss หรือสะดุดชั่วขณะในขณะเล่นเกมออนไลน์พร้อมกับเปิดสตรีมหรือฟังเพลง

---

> [!WARNING]
> ### ⚠️ ข้อควรระวังและระบบความปลอดภัยก่อนเริ่มใช้งาน (CRITICAL SAFETY)
> การปรับแต่งค่า Registry เป็นการเปลี่ยนแปลงโครงสร้างระดับระบบปฏิบัติการ (OS Level) การใส่ค่าที่ผิดพลาดอาจทำให้ระบบไม่เสถียรได้
> 
> **สิ่งที่ต้องทำก่อนเริ่มลงมือ:**
> 1. **สร้าง System Restore Point:** ไปที่ช่องค้นหาของ Windows พิมพ์ `Create a restore point` จากนั้นคลิกสร้าง (Create) เพื่อสำรองระบบปัจจุบันไว้
> 2. **สำรอง Registry:** เปิด `regedit` ไปที่ `File` -> `Export` และเซฟไฟล์เก็บไว้ในที่ปลอดภัย เพื่อใช้สำหรับกู้คืนระบบกลับสู่ค่าเริ่มต้นหากเกิดปัญหา

---

## 2. ขั้นตอนการปรับแต่ง MMCSS และ Network สำหรับเกมเมอร์และสตรีมเมอร์

เราจะทำการปรับแต่งระบบผ่าน Registry Editor เพื่อยกเลิกการจำกัดความเร็ว Network (Network Throttling) และปรับแต่งให้ CPU ทุ่มพลัง 100% ไปที่การประมวลผลเกมและการทำไลฟ์สตรีม

### ขั้นตอนที่ 1: การยกเลิก Network Throttling (แก้ปัญหา Ping สวิงและ Packet Loss)

เมื่อเราปิดระบบจำกัดแพ็กเก็ต การ์ดแลน (NIC) จะประมวลผลข้อมูลเต็มประสิทธิภาพทันทีที่ได้รับแพ็กเก็ตเข้ามา ส่งผลให้ค่า Latency ในเกมมีความนิ่งและเสถียรขึ้นอย่างเห็นได้ชัด

1. กดปุ่ม `Windows + R` พิมพ์ `regedit` แล้วกด Enter
2. เข้าไปยัง Path ดังนี้:
   ```text
   HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile
   ```
3. ดับเบิลคลิกที่ค่าคีย์ชื่อ `NetworkThrottlingIndex`
4. ปรับเปลี่ยนข้อมูลดังนี้:
   * **Value data:** ใส่ค่า `ffffffff` (เลข f 8 ตัว) ในฐาน Hexadecimal (หรือ `4294967295` ในฐาน Decimal)
   * *หมายเหตุ: การปรับคีย์นี้เป็น ffffffff จะเป็นการสั่งปิดใช้งาน Network Throttling อย่างถาวร*

```
Value Name: NetworkThrottlingIndex
Value Data: 0xffffffff (Hexadecimal)
```

---

### ขั้นตอนที่ 2: ปรับแต่งการจัดสรรความสำคัญของ CPU (System Responsiveness)

ตามค่าเริ่มต้น Windows จะสำรอง CPU 20% ให้กับงานเบื้องหลัง เราจะปรับให้ระบบแบ่งพลังงานให้กับงานสำคัญอย่างเกมและโปรแกรมสตรีม (เช่น OBS Studio) แบบเต็ม 100%

1. ยังคงอยู่ที่ Path เดิม:
   ```text
   HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile
   ```
2. ดับเบิลคลิกที่ค่าคีย์ชื่อ `SystemResponsiveness`
3. ปรับเปลี่ยนข้อมูลดังนี้:
   * **Value data:** ใส่ค่า `0` (ฐาน Hexadecimal หรือ Decimal ก็ได้)
   * *หมายเหตุ: การปรับเป็น 0 คือการบอกระบบว่าไม่ต้องสำรอง CPU ทิ้งไว้ให้แอปพลิเคชันเบื้องหลังทั่วไปอย่างไม่มีเหตุผล ให้ความสำคัญกับแอปหลักก่อนทันที*

---

### ขั้นตอนที่ 3: ยกระดับความสำคัญของชุดประมวลผล "Games" ในระดับ Kernel

Windows จะมีโปรไฟล์ย่อยสำหรับจัดการแอปพลิเคชันแต่ละประเภท เราจะเข้าไปตั้งค่าโปรไฟล์ "Games" ให้ขยับลำดับความสำคัญ (Priority) ขึ้นไปอยู่ที่ระดับสูงสุด

1. เข้าไปยัง Path ย่อยนี้:
   ```text
   HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games
   ```
2. ทำการตรวจสอบและปรับแต่งคีย์ดังต่อไปนี้ (หากไม่มีให้คลิกขวา -> New -> DWORD (32-bit) Value หรือ String Value ตามความเหมาะสม):
   * **GPU Priority** (DWORD): เปลี่ยนค่าเป็น `8` (ความสำคัญสูงสุดในการจัดตารางเวลาของ GPU)
   * **Priority** (DWORD): เปลี่ยนค่าเป็น `6` (เพิ่มลำดับความสำคัญระดับโปรเซสเซอร์)
   * **Scheduling Category** (String/REG_SZ): เปลี่ยนค่าเป็น `High`
   * **SFIO Priority** (String/REG_SZ): เปลี่ยนค่าเป็น `High` (ให้ความสำคัญกับการอ่านเขียนไฟล์ I/O ที่เกี่ยวข้องกับตัวเกมสูงสุด)

```
[HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games]
"GPU Priority"=dword:00000008
"Priority"=dword:00000006
"Scheduling Category"="High"
"SFIO Priority"="High"
```

---

## 3. สคริปต์อัตโนมัติสำหรับการปรับแต่ง (ปลอดภัยและรวดเร็ว)

หากคุณไม่ต้องการเข้าไปกดค้นหาทีละโฟลเดอร์ใน Registry Editor คุณสามารถใช้สคริปต์ลงทะเบียนระบบอัตโนมัตินี้ได้ทันที

### วิธีที่ 1: การใช้ไฟล์ `.reg` (Registry File)

ให้ทำการคัดลอกข้อความด้านล่างนี้ ไปวางในโปรแกรม **Notepad** จากนั้นบันทึกไฟล์เป็นชื่อ `MMCSS_Optimizer.reg` (ตรวจสอบให้แน่ใจว่าไม่ได้เซฟเป็นไฟล์ .txt) แล้วทำการดับเบิลคลิกไฟล์เพื่อรันระบบ

```registry
Windows Registry Editor Version 5.00

[HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile]
"NetworkThrottlingIndex"=dword:ffffffff
"SystemResponsiveness"=dword:00000000

[HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games]
"GPU Priority"=dword:00000008
"Priority"=dword:00000006
"Scheduling Category"="High"
"SFIO Priority"="High"
```

### วิธีที่ 2: การใช้สคริปต์กู้คืน (หากต้องการคืนค่าดั้งเดิมของ Windows)

หากเกิดปัญหาหรือไม่พึงพอใจในผลลัพธ์ สามารถสร้างไฟล์ชื่อ `MMCSS_Restore.reg` ด้วยวิธีการเดียวกันเพื่อย้อนระบบกลับสู่ค่าดั้งเดิมของ Windows:

```registry
Windows Registry Editor Version 5.00

[HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile]
"NetworkThrottlingIndex"=dword:0000000a
"SystemResponsiveness"=dword:00000014

[HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games]
"GPU Priority"=dword:00000008
"Priority"=dword:00000002
"Scheduling Category"="Medium"
"SFIO Priority"="Normal"
```

*ทำการรีสตาร์ทคอมพิวเตอร์ของคุณ 1 ครั้ง เพื่อให้การตั้งค่าทั้งหมดมีผลในระดับ Kernel*

---

## 4. ผลลัพธ์ต่อสตรีมเมอร์ (สตรีมผ่าน OBS / Streamlabs) และสถาปัตยกรรมระบบที่ดีที่สุด

สำหรับสตรีมเมอร์ที่เจอปัญหาเฟรมเรตตกในไลฟ์สตรีม (Dropped Frames) หรือหน้าจอเกมลื่นแต่ในไลฟ์กระตุก การตั้งค่าด้านบนจะมีส่วนช่วยอย่างมากเนื่องจาก:

1. **ลดคอขวดบน CPU:** เมื่อ `SystemResponsiveness` ถูกปรับเป็น `0` ซอฟต์แวร์ OBS ซึ่งเรียกใช้งานตัวแปลงสัญญาณวิดีโอ (Video Encoder) ร่วมกับ Thread ของเกม จะเข้าถึงพลังของ CPU โดยไม่มีกำแพงการจองทรัพยากร 20% มาบล็อกไว้
2. **การป้องกันปัญหา Audio Desync:** MMCSS มีบทบาทสำคัญในการควบคุม Audio Engine (WASAPI) การเพิ่มระดับความสำคัญให้กับ Tasks ของมัลติมีเดียจะช่วยแก้ปัญหาระบบเสียงดีเลย์หรือเสียงภาพไม่ตรงกันเมื่อสตรีมมิ่งเป็นระยะเวลานาน

---

## 5. อัปเกรดฮาร์ดแวร์เพื่อรีดประสิทธิภาพเครือข่ายให้ถึงขีดสุด

แม้ว่าเราจะปรับแต่งซอฟต์แวร์ในระดับ Kernel ของ Windows ให้ตอบสนองต่อแพ็กเก็ตได้ทันที แต่หากอุปกรณ์ฮาร์ดแวร์ต้นทางและสายสัญญาณมีคุณภาพต่ำ (เช่น เกิดสัญญาณรบกวนในสาย หรือชิปประมวลผลบนการ์ดแลนไม่แรงพอ) การปรับแต่งก็อาจไม่สามารถแสดงผลได้ 100%

นี่คืออุปกรณ์ฮาร์ดแวร์ที่เราขอแนะนำให้ใช้งานร่วมกันเพื่อสร้างระบบ Network & Multi-tasking ที่สมบูรณ์แบบ:

### 1. สาย LAN คุณภาพสูงสำหรับการส่งข้อมูลแบบไร้ความสูญเสีย (No Packet Loss)
สาย LAN ระดับมาตรฐาน Cat 6 หรือ Cat 8 ที่มีการชีลด์ป้องกันสัญญาณรบกวนที่ดีเยี่ยม จะช่วยป้องกันอาการสัญญาณดรอปและลดความหน่วงในสายลงได้อย่างสมบูรณ์แบบ
* **สาย LAN UGREEN Cat 8 Ethernet Cable (ความเร็วสูงถึง 40Gbps):** เหมาะสำหรับการเชื่อมต่อจากเราเตอร์มายังเครื่องเล่นเกม/สตรีมมิ่ง เพื่อความเสถียรระดับสูงสุด
  👉 [ดูรายละเอียดอุปกรณ์หรือสั่งซื้อได้ที่นี่](https://shopee.co.th/search?keyword=ugreen%20cat%208%20ethernet%20cable)

### 2. Wi-Fi 6E / Wi-Fi 7 Gaming Router ยุคใหม่
สำหรับผู้ที่ไม่สามารถเดินสาย LAN ได้โดยตรง ควรเลือกใช้เราเตอร์ที่มีเทคโนโลยี QoS (Quality of Service) ระดับเกมมิ่งเพื่อช่วยจัดสรรลำดับความสำคัญของแพ็กเก็ตเกมแยกจากอุปกรณ์มือถือเครื่องอื่นในบ้าน
* **ASUS ROG Rapture Series (Gaming Router):** สุดยอดเราเตอร์ที่มีฟังก์ชันจัดสัญญานเกมเป็นที่หนึ่ง ทำงานร่วมกับการตั้งค่า MMCSS ได้อย่างลงตัว
  👉 [ดูรายละเอียดอุปกรณ์หรือสั่งซื้อได้ที่นี่](https://shopee.co.th/search?keyword=asus%20rog%20rapture%20router)

### 3. การ์ดจอและ External Capture Card สำหรับลดโหลด CPU
สำหรับสตรีมเมอร์แบบ 2 เครื่องพีซี (Dual-PC Setup) หรือ 1 เครื่องประสิทธิภาพสูง การส่งต่อการประมวลผลภาพสตรีมไปยังการ์ดแคปเจอร์เป็นสิ่งจำเป็น เพื่อปล่อยให้ CPU ไปประมวลผลเกมได้อย่างเต็มที่
* **Elgato HD60 X / 4K X Capture Card:** อุปกรณ์ช่วยประมวลผลภาพวิดีโอภายนอก ลดภาระ CPU และสตรีมได้อย่างลื่นไหลไร้รอยต่อ
  👉 [ดูรายละเอียดอุปกรณ์หรือสั่งซื้อได้ที่นี่](https://shopee.co.th/search?keyword=elgato%20capture%20card)