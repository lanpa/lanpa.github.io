---
title: "從鎖定的 Samsung SSD 中救回資料"
date: 2024-06-13
summary: "Step-by-step guide to recover data from an SSD"
tags: ["laptop", "repair", "hardware"]
source_hash : "sha256:05639afa393d28b0e7a4e1e9ac50ff03"
ai_translated: true
---

> _注意：本文由 AI 自動翻譯，可能有誤譯，請以原文為準。_

我遇到了一個 Samsung SSD 的韌體錯誤。有一天我的 MacBook 在開機時突然顯示了一個帶有問號的資料夾。在網路上搜尋後，發現這是由硬碟故障引起的，以下是我救回資料的過程。

## 症狀
- 無法開機
- 無法掛載為外接硬碟
- 在 Mac 和 Windows 中會卡住，但在 `lsblk` Linux 下可以
- 可以使用 `dd` 指令，但速度約為 30MB/s，比正常的 NVMe SSD 慢得多
- 可以顯示 smartctl 數據：（它只撐了 26TBW！！！）

<p align="center">
    <img src="/images/fixing/image-2.png" alt="alt text" style="border:1px solid #ccc;" />
</p>

## 解決方案
1. 由於我知道檔案系統的檔案表位於磁碟開頭，我讓 dd 指令執行了幾個 GB 後停止。 `sudo dd /dev/sdb /dev/sdc`，其中 `sdb` 是故障的 SSD，而 `sdc` 是新的 SSD。
2. 在 Mac 上載入 sdc。它立即掛載為外接磁碟，且資料夾結構恢復了。
3. 我讓程式執行了一整晚。起床後應該就完全準備好了。
4. 運氣不好。在大約 500 GB 後速度變得極慢。不過，更多的資料被救回來了。
5. 進入另一個研究階段——我找到了一個名為 `ddrescue`。

## ddrescue

- ddrescue 旨在透過跳過不可讀的磁區並優先處理 *可讀的磁區*，從故障硬碟中救回資料。
- 它會建立一個對照檔來 *追蹤磁碟的哪些部分已複製*，以及哪些部分需要進一步嘗試。
- 該工具會多次重試有問題的區域，增加救回更多資料的機會。
- 在處理壞軌時，ddrescue 比 dd 運作得更快，因為它能避免卡在錯誤上。
- 我使用的指令： `sudo ddrescue /dev/sdb /dev/sdc rescue.log`。進度儲存在日誌檔中，因此你可以隨時中斷並重新開始。有時速度會突然提升。
- 執行 ddrescue 後，我能夠掛載救回的 SSD 並存取大部分檔案。

<p align="center">
    <img src="/images/fixing/image-1.png" alt="alt text" style="border:1px solid #ccc;" />
</p>


## 反思
1. 即使是 SSD 也要做備份


## 參考資料
![alt text](/images/fixing/image-4.png)
![alt text](/images/fixing/image-3.png)