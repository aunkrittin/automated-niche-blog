---
title: "ปลดล็อกประสิทธิภาพ CPU: การบริหารจัดการ Core Parking และ CPU Affinity ในระดับ Kernel"
date: 2026-07-06T05:11:08.844815+07:00
tags: ["Optimization", "Tech"]
draft: false
---

## ปลดล็อกประสิทธิภาพ CPU: การบริหารจัดการ Core Parking และ CPU Affinity ในระดับ Kernel

ในการพัฒนาและปรับแต่งระบบที่มีความต้องการประสิทธิภาพสูง โดยเฉพาะอย่างยิ่ง Game Server หรือ Real-time Application สิ่งสำคัญที่สุดคือการใช้ทรัพยากร CPU ให้เกิดประโยชน์สูงสุด หลายครั้งที่เราพบว่าแม้จะมี CPU สเปคสูง แต่แอปพลิเคชันกลับทำงานได้ไม่เต็มประสิทธิภาพ นั่นอาจเป็นเพราะการบริหารจัดการ Core Parking และ CPU Affinity ที่ยังไม่เหมาะสมในระดับลึก ซึ่งบทความนี้จะพาคุณไปเจาะลึกถึงกลไกเหล่านี้ในระดับ Kernel

### Core Parking: เมื่อ Kernel อยากประหยัดพลังงาน

Core Parking คือกลไกที่ระบบปฏิบัติการใช้ในการประหยัดพลังงานและลดความร้อนของ CPU โดยการ "จอด" หรือปิดการทำงานของคอร์ CPU ที่ไม่ได้ถูกใช้งานในช่วงเวลานั้นๆ เมื่อมีความต้องการประมวลผลเพิ่มขึ้น ระบบจะ "ปลุก" คอร์เหล่านั้นให้กลับมาทำงานอีกครั้ง

**ทำไม Core Parking ถึงเป็นปัญหาสำหรับ High-Performance Apps?**

แม้จะมีประโยชน์ด้านการประหยัดพลังงาน แต่สำหรับแอปพลิเคชันที่ต้องการ Latency ต่ำและ Throughput สูง เช่น Game Server ที่ต้องประมวลผล Physics, AI, และ Network Packet ตลอดเวลา การที่คอร์ CPU ถูกจอดและต้องใช้เวลาในการปลุกขึ้นมาใหม่ อาจทำให้เกิด Micro-stutter, Increased Latency หรือ Jitter ได้ ยิ่งไปกว่านั้น การโยกย้าย Workload ไปมาระหว่างคอร์ที่แอคทีฟกับคอร์ที่ถูกปลุกใหม่ ยังเพิ่ม Overhead ในการ Context Switching และ Cache Miss ได้อีกด้วย

**การจัดการ Core Parking ในระดับระบบปฏิบัติการ**

*   **Windows:**
    โดยทั่วไป Windows จะจัดการ Core Parking ผ่าน Power Plan คุณสามารถปรับแต่งได้ใน Control Panel หรือผ่านคำสั่ง `powercfg` เพื่อตั้งค่า Power Plan เป็น `High Performance` ซึ่งมักจะลดการจอดคอร์ลง แต่ไม่ได้ยกเลิกทั้งหมด การปรับใน Registry ยังสามารถทำได้ละเอียดกว่า แต่ต้องระมัดระวัง
    ```cmd
    powercfg /list
    powercfg /setactive <GUID_OF_HIGH_PERFORMANCE_PLAN>
    ```
    สำหรับ Registry Editor (regedit.exe) ให้ไปที่ `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Power\PowerSettings\54533251-82ca-49d6-b0b4-dfcf2366c290\0cc5b647-c1df-4637-891a-edc335ee7fcc` และเปลี่ยนค่า `Attributes` จาก `1` เป็น `0` เพื่อให้ตัวเลือก "Processor performance core parking min cores" ปรากฏใน Power Options (ต้องทำขั้นตอนนี้เพื่อให้เห็นตัวเลือกใน GUI) จากนั้นสามารถตั้งค่า Minimum Processor State เป็น 100% ได้

*   **Linux:**
    Linux มีกลไกการจัดการพลังงานที่คล้ายกันผ่าน `cpufreq` subsystem และ Governors ต่างๆ (เช่น `ondemand`, `performance`) สำหรับ Game Server หรือ Workload ที่ต้องการประสิทธิภาพสูงสุด มักจะตั้งค่า Governor เป็น `performance` ให้กับทุกคอร์
    ```bash
    # ตรวจสอบ governor ปัจจุบัน
    cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

    # ตั้งค่า governor เป็น performance (อาจต้องใช้ sudo หรือสิทธิ์ root)
    for i in $(seq 0 $(($(nproc) - 1))); do
        echo "performance" | sudo tee /sys/devices/system/cpu/cpu$i/cpufreq/scaling_governor
    done
    ```
    แต่ในระดับ Kernel ที่ลึกกว่านั้น การใช้ `isolcpus` ใน Kernel Boot Parameter จะช่วยให้คุณสามารถกันคอร์ CPU บางคอร์ออกจาก Scheduler ทั่วไปได้ ซึ่งหมายความว่า Kernel จะไม่ใช้คอร์เหล่านั้นสำหรับงานทั่วไป และจะไม่พยายามจอดคอร์เหล่านั้นด้วย เหมาะสำหรับการรัน Thread สำคัญแบบ Dedicated
    ```
    # เพิ่ม "isolcpus=2,3" ในไฟล์ /etc/default/grub (GRUB_CMDLINE_LINUX_DEFAULT)
    # หลังจากนั้นรัน: sudo update-grub
    # รีบูตเครื่อง
    ```
    ในตัวอย่างนี้ คอร์ 2 และ 3 จะถูกกันไว้ไม่ให้ Scheduler ทั่วไปใช้ ทำให้เราสามารถใช้ CPU Affinity ในการผูก Thread สำคัญเข้ากับคอร์เหล่านี้ได้อย่างมีประสิทธิภาพโดยไม่ถูกรบกวน

### CPU Affinity: ผูก Workload กับคอร์เฉพาะทาง

CPU Affinity คือความสามารถในการ "ผูก" กระบวนการ (Process) หรือเธรด (Thread) หนึ่งๆ เข้ากับคอร์ CPU ที่เฉพาะเจาะจง (หรือกลุ่มของคอร์) แทนที่จะปล่อยให้ Kernel Scheduler เป็นผู้กำหนดว่าจะรันงานนั้นบนคอร์ใด

**ความสำคัญของ CPU Affinity**

*   **Cache Locality:** เมื่อเธรดทำงานบนคอร์เดิมซ้ำๆ ข้อมูลที่เธรดนั้นต้องการจะอยู่ใน CPU Cache ของคอร์นั้นๆ ทำให้การเข้าถึงข้อมูลเร็วขึ้นอย่างมหาศาล การย้ายเธรดไปมาระหว่างคอร์บ่อยๆ (Cache Miss) ทำให้ต้องโหลดข้อมูลจาก Main Memory ซึ่งช้ากว่ามาก
*   **ลด Overhead การ Context Switching:** เมื่อเธรดถูกผูกกับคอร์ใดคอร์หนึ่ง Kernel ไม่จำเป็นต้องเสียเวลาในการตัดสินใจว่าจะรันเธรดนี้ที่ไหน ลดภาระของ Scheduler
*   **ประสิทธิภาพที่คาดการณ์ได้:** ช่วยให้แอปพลิเคชันที่มี Critical Path สามารถรันบนคอร์ที่มีทรัพยากรเฉพาะ ลดการรบกวนจากเธรดอื่นๆ
*   **การแยก Workload:** สำหรับ Game Server คุณอาจต้องการแยกเธรด Network I/O, Game Logic และ Physics Engine ไปยังคอร์ที่แตกต่างกัน เพื่อไม่ให้เกิดการแย่งชิงทรัพยากร

**การจัดการ CPU Affinity ในระดับระบบปฏิบัติการและ Kernel**

*   **Windows:**
    *   **Task Manager:** สามารถตั้งค่า Affinity ให้กับ Process ได้จากแท็บ `Details` (คลิกขวาที่ Process -> Set Affinity)
    *   **Command Line:** ใช้ `start` command พร้อม Option `/affinity`
        ```cmd
        start /affinity 0x4 "path\to\YourGameServer.exe"
        ```
        `0x4` คือ Bitmask สำหรับคอร์ที่ 2 (00000100 binary) หากต้องการคอร์ 0 และ 1 จะเป็น `0x3` (00000011 binary)
    *   **Programmatic API:** สำหรับนักพัฒนา C++ หรือ .NET สามารถใช้ฟังก์ชัน `SetProcessAffinityMask` หรือ `SetThreadAffinityMask` เพื่อผูก Process/Thread กับคอร์เฉพาะเจาะจงได้โดยตรงในโค้ด นี่คือการเรียก System Call ไปยัง Kernel โดยตรง
        ```cpp
        // ตัวอย่าง C++ สำหรับ SetProcessAffinityMask
        #include <windows.h>
        #include <iostream>

        int main() {
            HANDLE hProcess = GetCurrentProcess();
            // ผูก Process กับ CPU Core 0 และ Core 1 (0x00000003 ในรูปแบบ Bitmask)
            DWORD_PTR affinityMask = 0x00000003;
            if (SetProcessAffinityMask(hProcess, affinityMask)) {
                std::cout << "Process affinity set to cores 0 and 1." << std::endl;
            } else {
                std::cerr << "Failed to set process affinity mask. Error: " << GetLastError() << std::endl;
            }
            // ... รัน Game Server Logic
            return 0;
        }
        ```

*   **Linux:**
    *   **`taskset` Command:** เป็นเครื่องมือที่นิยมใช้ในการตั้งค่า CPU Affinity ให้กับ Process หรือรันคำสั่งด้วย Affinity ที่กำหนด
        ```bash
        # รันโปรแกรม 'your_game_server' บน CPU Core 2 และ Core 3 (ใช้ Bitmask 0xC หรือ 1100 binary)
        taskset 0xC ./your_game_server

        # ตั้งค่า Affinity ให้กับ Process ที่รันอยู่แล้ว (PID 12345) บน Core 0 และ Core 1
        taskset -p 0x3 12345

        # ตรวจสอบ Affinity ของ Process (PID 12345)
        taskset -p 12345
        ```
    *   **Programmatic API:** ใน C/C++ สำหรับ Linux สามารถใช้ `sched_setaffinity` และ `sched_getaffinity` System Calls เพื่อจัดการ Affinity ของเธรดหรือกระบวนการได้อย่างละเอียด นี่คือการเรียก Kernel โดยตรง
        ```c
        // ตัวอย่าง C สำหรับ sched_setaffinity
        #define _GNU_SOURCE
        #include <sched.h>
        #include <stdio.h>
        #include <stdlib.h>
        #include <unistd.h>

        int main() {
            cpu_set_t cpuset;
            CPU_ZERO(&cpuset); // เคลียร์เซ็ต CPU
            CPU_SET(0, &cpuset); // เพิ่ม CPU Core 0 เข้าไปในเซ็ต
            CPU_SET(1, &cpuset); // เพิ่ม CPU Core 1 เข้าไปในเซ็ต

            // ตั้งค่า Affinity สำหรับเธรดปัจจุบัน (PID 0 หมายถึงเธรดของตัวเอง)
            if (sched_setaffinity(0, sizeof(cpu_set_t), &cpuset) == -1) {
                perror("sched_setaffinity failed");
                exit(EXIT_FAILURE);
            }

            printf("Thread affinity set to CPU Core 0 and 1.\n");
            // ... รัน Game Server Logic
            sleep(100); // จำลองการทำงาน
            return 0;
        }
        ```
    *   **`cgroup` (cpuset subsystem):** สำหรับสภาพแวดล้อมที่ซับซ้อนขึ้น เช่น Containerization (Docker, Kubernetes) หรือการจัดการทรัพยากรสำหรับผู้ใช้หลายคน `cgroup` ใน Linux ให้ความสามารถในการสร้าง CPU Set ที่ผูกกลุ่มของ Process เข้ากับกลุ่มของคอร์ CPU ได้อย่างละเอียด ทำให้การแยกทรัพยากรทำได้เป็นระบบมากขึ้น

### แนวทางปฏิบัติสำหรับ Game Server และแอปพลิเคชันประสิทธิภาพสูง

1.  **ทำความเข้าใจโครงสร้าง CPU:** รู้ว่า CPU ของคุณมีกี่คอร์ กี่เธรด (รวม Hyper-threading) และคอร์ใดเป็นคอร์จริง คอร์ใดเป็น Logical Thread (HT) โดยทั่วไป การผูก Workload สำคัญกับ Physical Core จะให้ประสิทธิภาพดีกว่า เพราะไม่ต้องแชร์ทรัพยากรภายในคอร์เดียวกัน
2.  **ระบุ Workload Critical Path:** แยกแยะว่าส่วนใดของแอปพลิเคชันที่ต้องการประสิทธิภาพสูงสุด (เช่น Game Loop, Network Polling Thread, Physics Simulation)
3.  **ใช้ Core Parking Management:**
    *   **Windows:** ตั้งค่า Power Plan เป็น `High Performance` และพิจารณาปรับ Registry เพื่อควบคุม Core Parking โดยตรง
    *   **Linux:** ตั้งค่า `cpufreq governor` เป็น `performance` และ **พิจารณาใช้ `isolcpus` สำหรับคอร์ที่ต้องการความแน่นอนสูงสุด** เพื่อป้องกัน Kernel Scheduler รบกวน
4.  **ใช้ CPU Affinity อย่างชาญฉลาด:**
    *   **Dedicate Cores:** สำหรับ Workload ที่สำคัญมาก ให้ผูกเธรดเหล่านั้นกับคอร์ CPU ที่ถูก `isolcpus` ไว้ (ใน Linux) หรือคอร์ที่คุณมั่นใจว่ามีภาระงานน้อยที่สุด
    *   **Group Workloads:** หากมี Workload ที่ทำงานร่วมกันอย่างใกล้ชิดและใช้ข้อมูลชุดเดียวกัน ควรผูกไว้บนคอร์กลุ่มเดียวกันเพื่อเพิ่ม Cache Locality
    *   **Avoid Over-Affinity:** อย่าผูกทุกอย่างเข้ากับคอร์เฉพาะเจาะจง ปล่อยให้ระบบปฏิบัติการจัดการเธรดที่ไม่สำคัญเองบนคอร์ที่เหลือ เพื่อให้ระบบมีความยืดหยุ่น
    *   **Monitoring:** ใช้เครื่องมือเช่น `htop`, `perf`, `top` ใน Linux หรือ Performance Monitor ใน Windows เพื่อตรวจสอบการใช้งาน CPU, Context Switch และ Cache Misses หลังจากปรับแต่ง เพื่อดูว่าได้ผลลัพธ์ตามที่ต้องการหรือไม่

การบริหารจัดการ Core Parking และ CPU Affinity ในระดับ Kernel เป็นเทคนิคขั้นสูงที่ทรงพลังในการปลดล็อกประสิทธิภาพสูงสุดของ CPU สำหรับแอปพลิเคชันที่ต้องการความเร็วและความเสถียร โดยเฉพาะอย่างยิ่งในโลกของ Game Server ที่ทุก Microsecond มีความหมาย การลงทุนทำความเข้าใจและนำเทคนิคเหล่านี้ไปใช้ จะช่วยให้คุณสร้างสรรค์ระบบที่ตอบสนองได้รวดเร็วและมีประสิทธิภาพเหนือกว่าคู่แข่ง