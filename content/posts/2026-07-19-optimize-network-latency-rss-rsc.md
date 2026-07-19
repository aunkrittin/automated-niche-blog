---
title: "ถอดรหัส Receive Side Scaling (RSS) และ Receive Segment Coalescing (RSC): จัดสรรคอร์ CPU ประมวลผลแพ็กเก็ตเน็ตเวิร์กเพื่อลด Latency และป้องกัน Packet Loss ขั้นสุด"
date: 2026-07-19T04:15:50.301649+00:00
tags: ["Optimization", "Tech"]
draft: false
---

# ถอดรหัส Receive Side Scaling (RSS) และ Receive Segment Coalescing (RSC): จัดสรรคอร์ CPU ประมวลผลแพ็กเก็ตเน็ตเวิร์กเพื่อลด Latency และป้องกัน Packet Loss ขั้นสุด

ในโลกของระบบเครือข่ายความเร็วสูง (High-Speed Networking) และการพัฒนา Game Server ที่ต้องรองรับผู้เล่นหลักหมื่นคนพร้อมกัน ปัญหาคอขวดที่เหล่านักพัฒนาและวิศวกรระบบมักจะพบเจอไม่ใช่แบนด์วิดท์ของระบบเครือข่ายไม่พอ แต่คือ **"CPU Core 0 ประมวลผลไม่ทันจนเกิด Packet Loss"** 

เมื่อการ์ดแลน (NIC) รับข้อมูลเข้ามาในระดับกิกะบิต (Gbps) แต่ละวินาทีจะมีแพ็กเก็ตขนาดเล็กจำนวนมหาศาลหลั่งไหลเข้ามา หากปราศจากการปรับแต่งโครงสร้างการประมวลผลที่ดี แพ็กเก็ตทั้งหมดจะถูกส่งไปให้ CPU เพียงคอร์เดียวจัดการผ่านกลไก Interrupt Request (IRQ) ส่งผลให้เกิดปรากฏการณ์ **Core 0 Bottleneck** ค่า Latency พุ่งสูง และเกิด Packet Drop ในที่สุด

บทความเชิงลึกนี้จะพาคุณไปเจาะลึกสองเทคโนโลยีสำคัญระดับฮาร์ดแวร์และเคอร์เนล ได้แก่ **Receive Side Scaling (RSS)** และ **Receive Segment Coalescing (RSC)** เพื่อช่วยให้คุณสามารถจัดสรรคอร์ CPU ประมวลผลแพ็กเก็ตได้อย่างมีประสิทธิภาพสูงสุด

---

## 1. ปัญหาคอขวดที่ซ่อนอยู่: ทำไม Gigabit Network ถึงทำ CPU แทบพัง?

ตามปกติเมื่อแพ็กเก็ตเดินทางมาถึงการ์ดเน็ตเวิร์ก (NIC) การ์ดจะส่งสัญญาณขัดจังหวะที่เรียกว่า **Hardware Interrupt (IRQ)** ไปยัง CPU เพื่อบอกให้ระบบปฏิบัติการมารับข้อมูลไปประมวลผลต่อในระดับซอฟต์แวร์ (เรียกว่า SoftIRQ ใน Linux หรือ DPC - Deferred Procedure Call ใน Windows)

```
[ Network Packet ] ──> [ NIC ] ──> [ IRQ Line ] ──> [ CPU Core 0 Only! (Bottleneck) ]
```

โดยดีฟอลต์ ระบบปฏิบัติการมักจะโยนงาน IRQ และ DPC/SoftIRQ เหล่านี้ไปที่ **CPU Core 0** เสมอ หากเซิร์ฟเวอร์ของคุณต้องรับส่งข้อมูลระดับ 10 Gbps+ หรือประมวลผลแพ็กเก็ต UDP ขนาดเล็กจำนวนมากจากผู้เล่นเกม (High PPS - Packets Per Second) Core 0 จะทำงานแตะ 100% ทันที ขณะที่คอร์อื่นๆ (Core 1-31) นั่งว่างงาน นี่คือสาเหตุหลักที่ทำให้เกิด Latency Spikes (อาการปิงแกว่ง) และ Packet Loss แม้ว่า CPU Usage โดยรวมของเครื่องจะแสดงผลแค่ 5% ก็ตาม

---

## 2. Receive Side Scaling (RSS): ปลดล็อกการประมวลผลแบบ Multicore

**Receive Side Scaling (RSS)** คือเทคโนโลยีระดับฮาร์ดแวร์บน NIC ที่เข้ามาแก้ปัญหานี้โดยตรง แทนที่จะส่ง IRQ ทั้งหมดไปที่ CPU คอร์เดียว RSS จะกระจายแพ็กเก็ตเน็ตเวิร์กที่ได้รับเข้ามาไปยังคอร์ CPU หลายๆ คอร์แบบขนานกัน

```
                      ┌──> [ Hardware Queue 0 ] ──> [ CPU Core 2 ]
[ Incoming Packets ] ─┼──> [ Hardware Queue 1 ] ──> [ CPU Core 3 ]
                      ├──> [ Hardware Queue 2 ] ──> [ CPU Core 4 ]
                      └──> [ Hardware Queue 3 ] ──> [ CPU Core 5 ]
```

### กลไกการทำงานของ RSS:
1. **Hashing (Toeplitz Function):** เมื่อแพ็กเก็ตมาถึง NIC จะทำการแฮชข้อมูลหัวข้อ (Header) ของแพ็กเก็ต โดยทั่วไปจะใช้ค่า **4-Tuple** (Source IP, Destination IP, Source Port, Destination Port) เพื่อให้แน่ใจว่าแพ็กเก็ตที่อยู่ใน Connection เดียวกัน (Flow เดียวกัน) จะถูกส่งไปประมวลผลบน CPU คอร์เดียวกันเสมอ ป้องกันปัญหาการสลับลำดับของแพ็กเก็ต (Out-of-order Packets)
2. **Indirection Table:** ผลลัพธ์จากการแฮชจะถูกนำมาเทียบกับตารางดัชนี (Indirection Table) เพื่อชี้ไปที่คิวฮาร์ดแวร์ (Hardware Queue) เฉพาะตัว
3. **MSI-X (Message Signaled Interrupts-Extended):** แต่ละคิวฮาร์ดแวร์จะมีเส้นทาง Interrupt (MSI-X Vector) แยกเป็นของตัวเอง ทำให้สามารถยิง Interrupt ไปหา CPU คอร์ที่กำหนดไว้ล่วงหน้าได้อย่างแม่นยำ

---

## 3. Receive Segment Coalescing (RSC): ยุบรวมแพ็กเก็ตเพื่อลด Context Switching

หาก RSS คือการกระจายงาน **Receive Segment Coalescing (RSC)** (หรือที่ในฝั่ง Linux เรียกว่า **LRO - Large Receive Offload**) คือการ **"รวมร่างแพ็กเก็ต"** ก่อนส่งให้ CPU

ในระบบเครือข่าย TCP เมื่อมีการส่งไฟล์ขนาดใหญ่ ข้อมูลจะถูกซอยย่อยออกเป็นแพ็กเก็ตขนาดเล็กตามค่า MTU (ปกติคือ 1500 bytes) หากระบบต้องประมวลผล Header ของทุกๆ แพ็กเก็ต CPU จะต้องทำงานหนักมากจาก Context Switching

```
[ Small Packet 1 ] \
[ Small Packet 2 ]  ──> [ NIC with RSC Enabled ] ──> [ Combined Large Packet ] ──> [ OS Stack ]
[ Small Packet 3 ] /                                    (Process Header Only Once!)
```

### กลไกการทำงานของ RSC:
เมื่อ NIC ได้รับแพ็กเก็ต TCP ที่เป็นซีเควนซ์เดียวกัน มันจะไม่ยิง Interrupt ทันที แต่จะรวมแพ็กเก็ตเหล่านั้นเข้าด้วยกันเป็นเซกเมนต์ขนาดใหญ่ (สูงสุด 64KB) ในระดับฮาร์ดแวร์ แล้วค่อยส่งต่อให้ระบบปฏิบัติการประมวลผล Network Stack เพียงครั้งเดียว ช่วยลดภาระการทำงานของ CPU ลงได้มหาศาล (ลดลงได้ถึง 30-50%)

> ⚠️ **ข้อจำกัดสำคัญด้าน Game Server:** 
> RSC ออกแบบมาสำหรับโปรโตคอล **TCP** เท่านั้น และจุดประสงค์คือเพื่อเพิ่ม **Throughput** (ความเร็วในการรับส่งไฟล์) แต่การรอรวมเซกเมนต์อาจทำให้เกิด Latency เพิ่มขึ้นเล็กน้อย (Jitter) สำหรับ **Game Server ที่ใช้ UDP** เป็นหลัก หรือระบบที่ต้องการ Ultra-low Latency เรามักจะเลือก **เปิด RSS แต่ปิด RSC**

---

## 4. ปฏิบัติการปรับแต่ง (Hands-on Configuration Guide)

> [!WARNING]
> **ข้อควรระวังเพื่อความปลอดภัยสูงสุด (CRITICAL SAFETY WARNING):**
> 1. การปรับแต่งค่าคอนฟิกเน็ตเวิร์กและการ์ดแลนจะทำให้ระบบอินเทอร์เน็ตหลุดชั่วคราว (ประมาณ 2-5 วินาที) ห้ามทำขณะที่มีการใช้งานระบบ Production หรือขณะมีผู้เล่นเชื่อมต่ออยู่เด็ดขาด
> 2. โปรดสร้าง **System Restore Point** (สำหรับ Windows) หรือสำรองข้อมูลไฟล์คอนฟิก `/etc/network/interfaces` หรือ `/etc/sysconfig/network-scripts/` (สำหรับ Linux) ก่อนดำเนินการทุกครั้ง

---

### 4.1 วิธีการตั้งค่าในระบบปฏิบัติการ Windows (Windows Server / Windows 10 & 11)

เราจะใช้ PowerShell ในฐานะ Administrator ในการควบคุมและตั้งค่าขั้นสูง เนื่องจากหน้าต่าง GUI ของ Device Manager ไม่สามารถเข้าถึงรายละเอียดเชิงลึกได้ทั้งหมด

#### ขั้นตอนที่ 1: ตรวจสอบสถานะการทำงานปัจจุบันของ RSS

เปิด PowerShell (Admin) แล้วรันคำสั่ง:

```powershell
Get-NetAdapterRss | Format-Table Name, InterfaceDescription, Enabled, NumberOfReceiveQueues, Profile
```

คำสั่งนี้จะแสดงผลว่าการ์ดแลนใบใดเปิดใช้งาน RSS อยู่ และมีจำนวนฮาร์ดแวร์คิวเท่าไหร่

#### ขั้นตอนที่ 2: ตั้งค่าหลีกเลี่ยง CPU Core 0 (สลัดคอขวด)

ตามธรรมชาติของสถาปัตยกรรม Windows CPU Core 0 และ Core 1 มักถูกจับจองโดยเซอร์วิสของระบบปฏิบัติการ เราควรตั้งค่าให้ RSS ไปเริ่มต้นทำงานที่ **Core 2** เป็นต้นไป และหลีกเลี่ยง Hyperthreaded Cores (คอร์เสมือน) เพื่อประสิทธิภาพสูงสุด

สมมติว่าคุณต้องการตั้งค่าให้การ์ดแลนชื่อ "Ethernet" ทำการประมวลผล RSS โดยใช้ CPU 4 คอร์ เริ่มต้นที่คอร์ตัวที่ 2 (ไม่รวม Core 0 และ 1):

```powershell
Set-NetAdapterRss -Name "Ethernet" -BaseProcessorGroup 0 -BaseProcessorNumber 2 -MaxProcessors 4 -NumberOfReceiveQueues 4
```

*อธิบายพารามิเตอร์:*
* `-BaseProcessorNumber 2`: เริ่มต้นกระจายงานที่ CPU Core 2 (ข้าม Core 0, 1)
* `-MaxProcessors 4`: จำกัดให้ใช้ CPU สูงสุดไม่เกิน 4 คอร์ เพื่อหลีกเลี่ยงการแย่งทรัพยากรกับแอปพลิเคชันหลัก
* `-NumberOfReceiveQueues 4`: กำหนดจำนวน Queue ให้สัมพันธ์กับจำนวนคอร์

#### ขั้นตอนที่ 3: เปิด/ปิด RSC (ขึ้นอยู่กับรูปแบบการใช้งาน)

สำหรับ **Web Server / File Server (เน้น Throughput):** แนะนำให้เปิดใช้งาน RSC เพื่อประหยัด CPU

```powershell
Enable-NetAdapterRsc -Name "Ethernet" -IPv4 -IPv6
```

สำหรับ **Game Server / Voice Server (เน้น Ultra-low Latency):** แนะนำให้ปิดใช้งาน RSC เพื่อลด Delay ในการรอรวมแพ็กเก็ต

```powershell
Disable-NetAdapterRsc -Name "Ethernet" -IPv4 -IPv6
```

---

### 4.2 วิธีการตั้งค่าในระบบปฏิบัติการ Linux (Ubuntu / Debian / RHEL)

ใน Linux เราจะควบคุมการทำงานของ RSS ผ่านการจัดสรร IRQ Affinity และใช้เครื่องมือ `ethtool`

#### ขั้นตอนที่ 1: ตรวจสอบช่องสัญญาณ (Channels) และคิวของการ์ดจอ

```bash
# ตรวจสอบว่าการ์ดแลน (เช่น eth0) รองรับ Multi-queue หรือไม่
sudo ethtool -l eth0
```

#### ขั้นตอนที่ 2: ตั้งค่าจำนวนคิวให้สัมพันธ์กับคอร์ CPU

หากระบบของคุณมี CPU 8 Cores คุณควรตั้งค่า Combined Queue เป็น 8 เพื่อให้เกิดการกระจายตัวแบบ 1:1

```bash
sudo ethtool -L eth0 combined 8
```

#### ขั้นตอนที่ 3: ตรวจสอบและจัดการ irqbalance

บริการ `irqbalance` ของ Linux ทำหน้าที่กระจาย IRQ อัตโนมัติ แต่อาจไม่เสถียรสำหรับแอปพลิเคชันที่ต้องการ Real-time Latency ต่ำ สำหรับเซิร์ฟเวอร์เกมระดับสูง แนะนำให้ปิด `irqbalance` แล้วทำ Manual Mapping

```bash
# ปิดบริการ irqbalance
sudo systemctl stop irqbalance
sudo systemctl disable irqbalance
```

จากนั้น ทำการผูกมัด IRQ ของการ์ดแลนไปยัง CPU คอร์ที่ต้องการโดยตรงผ่านสคริปต์นี้ (ตัวอย่างผูกมัดคิวของ eth0 ไปที่ CPU คอร์ตามที่กำหนด):

```bash
#!/bin/bash
# ค้นหา IRQ ของ eth0
IRQS=$(ls -d /sys/class/net/eth0/device/msi_irqs/* | awk -F/ '{print $NF}')
CORE=2 # เริ่มต้นที่ Core 2

for IRQ in $IRQS; do
    # แปลงเลขคอร์เป็น Hex Mask (เช่น Core 2 = 4, Core 3 = 8)
    MASK=$(printf "%x" $((1 << CORE)))
    echo "Mapping IRQ $IRQ to CPU Core $CORE (Mask: $MASK)"
    echo $MASK > /proc/irq/$IRQ/smp_affinity
    CORE=$((CORE + 1))
done
```

---

## 5. การวิเคราะห์ผลลัพธ์หลังการปรับแต่ง (Verification)

หลังการตั้งค่า คุณสามารถทำการทดสอบและสังเกตความเปลี่ยนแปลงของระบบได้ดังนี้:

1. **Performance Monitor (Windows):** เปิดโปรแกรม `Perfmon` แล้วเพิ่มเคาน์เตอร์ `Processor Information -> % DPC Time` และ `% Interrupt Time` สังเกตว่ากราฟจะกระจายตัวอย่างสม่ำเสมอในหลายคอร์ แทนที่จะไปกองกระจุกตัวอยู่ที่ Core 0 เพียงคอร์เดียว
2. **htop (Linux):** กด `htop` แล้วเปิดฟังก์ชันแสดงผล SoftIRQ คุณจะเห็นการประมวลผลในฝั่งเน็ตเวิร์กถูกเกลี่ยเฉลี่ยไปยังคอร์ต่างๆ (เช่น CPU2, CPU3, CPU4) อย่างเป็นระเบียบ
3. **ลดปัญหา Micro-stuttering:** ในฝั่งผู้ใช้งานหรือผู้เล่นเกม ค่าปิงจะมีความเสถียรมากขึ้นอย่างเห็นได้ชัด ค่าเบี่ยงเบนมาตรฐานของปิง (Jitter) จะลดลงอย่างมีนัยสำคัญ

---

## 6. อุปกรณ์ฮาร์ดแวร์แนะนำเพื่อเพิ่มประสิทธิภาพระบบเครือข่าย

การปรับแต่งซอฟต์แวร์และระบบปฏิบัติการจะไร้ผลทันที หากการ์ดเน็ตเวิร์ก (NIC) หรืออุปกรณ์ฮาร์ดแวร์ในระบบของคุณไม่รองรับฟีเจอร์ระดับสูงอย่าง RSS, RSC หรือ MSI-X เพื่อการทำงานที่มีประสิทธิภาพระดับสุดยอด เราขอแนะนำอุปกรณ์ฮาร์ดแวร์เหล่านี้ที่ได้รับการทดสอบแล้วว่ารองรับเทคโนโลยีเหล่านี้ 100%

*   **Intel X550-T2 10GbE PCI-e NIC:** สุดยอดการ์ดแลนระดับ Enterprise ที่รองรับ RSS แบบ Multi-queue เต็มรูปแบบ และมีเสถียรภาพในการจัดการคิวฮาร์ดแวร์ระดับเทพที่สุด
    *   [ดูรายละเอียดอุปกรณ์หรือสั่งซื้อได้ที่นี่](https://shopee.co.th/search?keyword=Intel+X550-T2)
*   **Intel i226-V 2.5GbE PCI-e Network Card:** สำหรับผู้ที่ต้องการอัปเกรดพีซีเครื่องหลักหรือเซิร์ฟเวอร์ขนาดเล็ก การ์ดรุ่นนี้รองรับ RSS และ MSI-X ช่วยแก้ปัญหาคอขวดบน Windows 11 ได้อย่างหมดจด
    *   [ดูรายละเอียดอุปกรณ์หรือสั่งซื้อได้ที่นี่](https://shopee.co.th/search?keyword=Intel+i226-V)
*   **สายแลน Link Cat8 SFTP Ultra-High Speed:** ลดโอกาสการเกิดคลื่นรบกวน (Cross-talk) และการสูญเสียของแพ็กเก็ตในสาย ซึ่งมักจะเป็นสาเหตุของ Packet Loss แฝงที่โปรแกรมเมอร์มักมองข้าม
    *   [ดูรายละเอียดอุปกรณ์หรือสั่งซื้อได้ที่นี่](https://shopee.co.th/search?keyword=Cat8+LAN+Cable)
*   **ASUS ROG Rapture GT-AX11000 Pro (Gaming Router):** เราเตอร์ที่มาพร้อมชิปประมวลผลประสิทธิภาพสูงและฟีเจอร์การจัดลำดับแพ็กเก็ต (Hardware QoS) ที่ทำงานสอดประสานกับระบบ RSS ของตัวรับได้เป็นอย่างดี
    *   [ดูรายละเอียดอุปกรณ์หรือสั่งซื้อได้ที่นี่](https://shopee.co.th/search?keyword=ASUS+ROG+GT-AX11000)

---

## สรุป

การทำความเข้าใจและเปิดใช้งาน **RSS** และ **RSC** อย่างถูกวิธี เปรียบเสมือนการขยายสะพานให้แพ็กเก็ตเน็ตเวิร์กเดินทางเข้าสู่หน่วยประมวลผลได้อย่างราบรื่นโดยไม่เกิดปัญหารถติดสะสมที่คอร์แรกคอร์เดียว การลงทุนในเชิงการปรับแต่งโค้ดร่วมกับการเลือกใช้ฮาร์ดแวร์ระดับคุณภาพ จะทำให้เกมเซิร์ฟเวอร์หรือซอฟต์แวร์เน็ตเวิร์กของคุณรีดประสิทธิภาพออกมาได้คุ้มค่าตัวเงินที่สุด ลดปัญหาคอขวดแฝงเร้นในระบบ และมอบประสบการณ์การใช้งานที่ลื่นไหลไร้การสะดุดอย่างแท้จริง