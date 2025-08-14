---
title: "Retrieve data from a locked out samsung SSD"
title_zh: "從故障的三星SSD恢復資料"
date: 2024-06-13
summary: "Step-by-step guide to recover data from an SSD"
tags: ["laptop", "repair", "hardware"]
---


I stumbled upon a Samsung SSD firmware bug. One day my MacBook suddenly showed a folder with a question mark while booting up. After searching through the Internet, it turns out that it was caused by a bad hard drive, so here's how I recovered my data.

## Symptoms
- Unable to boot
- Unable to mount as external drive
- Stuck in Mac and Windows, but able to `lsblk` under Linux
- Able to use the `dd` command, but the speed is ~30MB/second, which is way slower than a normal NVMe SSD
- Able to show smartctl data: (It only last for 26TBW!!!)

<p align="center">
    <img src="/images/fixing/image-2.png" alt="alt text" style="border:1px solid #ccc;" />
</p>

## Solution
1. Since I knew that the file table of the file system is at the beginning of the disk, I let the dd command run for several gigabytes and then stopped. `sudo dd /dev/sdb /dev/sdc`, where `sdb` is the bad SSD and `sdc` is the new SSD.
2. Loaded sdc on a Mac. It immediately mounted itself as an external disk, and the folder structure is back.
3. I let the program run for a whole night. It should be completely ready after waking up.
4. No luck. The speed became incredibly slow after around 500 GB. How ever, more data is recovered.
5. Here comes another research phase - I found a program called `ddrescue`.

## ddrescue

- ddrescue is designed to recover data from failing drives by skipping unreadable sectors and focusing on *readable ones first*.
- It creates a map file to *track which parts of the disk have been copied* and which need further attempts.
- The tool retries problematic areas multiple times, increasing the chance of recovering more data.
- ddrescue works faster than dd when dealing with bad sectors, as it avoids getting stuck on errors.
- The command I used: `sudo ddrescue /dev/sdb /dev/sdc rescue.log`. The progress is save in the log file, so you can interrupt at anytime and restart. Sometimes the speed bumps up.
- After running ddrescue, I was able to mount the recovered SSD and access most of my files.

<p align="center">
    <img src="/images/fixing/image-1.png" alt="alt text" style="border:1px solid #ccc;" />
</p>


## Reflection
1. Do backups, even with SSDs


## References
![alt text](/images/fixing/image-4.png)
![alt text](/images/fixing/image-3.png)