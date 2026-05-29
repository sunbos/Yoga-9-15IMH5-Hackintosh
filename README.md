# Yoga-9-15IMH5-Hackintosh

Lenovo Yoga 9 15IMH5 macOS (Tahoe/Sequoia/Ventura) Hackintosh 配置。

## 硬件信息

| 组件 | 规格 |
|------|------|
| **CPU** | Intel Core i9-10980HK（8 核 16 线程，2.4 GHz / 5.3 GHz） |
| **型号** | MacBookPro16,1 |
| **内存** | 16 GB |
| **WiFi** | Intel AX201 |
| **蓝牙** | Intel Bluetooth（USB Product ID 0x0026） |
| **声卡** | Realtek ALC298（layout-id 98） |
| **触摸板** | I2C HID |

## Kext 列表

| kext | 来源 | 用途 |
|------|------|------|
| Lilu | 源码编译 | 核心框架 |
| AppleALC | 源码编译（最小化） | 声卡驱动 |
| AirportItlwm | 源码编译（最小化） | Intel WiFi |
| IntelBluetoothFirmware | 源码编译（最小化） | Intel 蓝牙固件加载 |
| IntelBTPatcher | 源码编译（最小化） | Intel 蓝牙运行时补丁 |
| YogaSMC | 源码编译 | Yoga 特性支持 |
| VirtualSMC | 上游 release | SMC 模拟 |
| WhateverGreen | 上游 release | 显卡驱动 |
| VoodooI2C + VoodooI2CHID | 上游 release | I2C 触摸板 |
| BlueToolFixup | 上游 release | 蓝牙修复 |
| ECEnabler | 上游 release | EC 电池支持 |
| NVMeFix | 上游 release | NVMe 电源管理 |
| RestrictEvents | 上游 release | 系统事件限制 |
| IO80211FamilyLegacy | OCLP payloads | WiFi API 兼容层（Sequoia/Tahoe） |
| IOSkywalkFamily | OCLP payloads | Skywalk 网络栈（Sequoia/Tahoe） |
| AMFIPass | OCLP payloads | AMFI 签名绕过 |

## 自动构建

GitHub Actions 每周一自动检查上游更新并构建。详见 `.github/workflows/build-kexts.yml`。

## 目录结构

```
├── config/device-config.json   # 设备配置（PCI ID、codec、patches）
├── patches/                    # 源码补丁
├── scripts/                    # 构建脚本（最小化、下载、更新检查）
├── BIOS/                       # BIOS 相关文件
└── USB定制/                    # USB 端口映射
```
