# Yoga-9-15IMH5-Hackintosh

Lenovo Yoga 9 15IMH5 macOS (Tahoe/Sequoia/Ventura) Hackintosh 配置。

## 硬件信息

| 组件 | 规格 |
|------|------|
| **CPU** | Intel Core i9-10980HK（8 核 16 线程，2.4 GHz / 5.3 GHz） |
| **芯片组** | HM470 (Comet Lake-H) |
| **型号** | MacBookPro16,1 |
| **内存** | 16 GB |
| **WiFi** | Intel AX201 (Wireless-AC AX201, PCI ID 0x06F08086) |
| **蓝牙** | Intel AX201 Bluetooth (USB VID=0x8087, PID=0x0026, hw_variant=0x13/HrP, hw_platform=0x37) |
| **声卡** | Realtek ALC298（layout-id 98） |
| **触摸板** | I2C HID |
| **独显** | NVIDIA GTX 1650 Max-Q（已通过 SSDT-dGPU-Off 禁用） |

## ACPI SSDT 列表

| SSDT | 用途 |
|------|------|
| SSDT-PLUG | XCPM CPU 电源管理，影响变频和功耗 |
| SSDT-EC-USBX-LAPTOP | EC 修复 + USB 电源属性（Dortania 官方要求） |
| SSDT-AWAC | 400 系列芯片组 AWAC 时钟修复，macOS 必需 |
| SSDT-dGPU-Off | 禁用 NVIDIA 独显，节省电源+避免冲突 |
| SSDT-PNLF | 背光控制，配合 WhateverGreen |
| SSDT-XOSI | I2C 触控板需要（配合 _OSI → XOSI 重命名补丁） |
| SSDT-ECRW | YogaSMC EC 读写访问，风扇/传感器/电池通知必需 |
| SSDT-RCSM | YogaSMC 翻盖模式控制（Read Clamshell Mode），IdeaVPC 功能依赖 |
| SSDT-Brightness | 亮度键 EC→ACPI 标准通知，配合 BrightnessKeys |
| SSDT-SBUS-MCHC | SBUS + MCHC 设备注入（合并版） |

### ACPI Patch 列表

| 重命名 | 用途 |
|--------|------|
| `_OSI → XOSI` | OS 检测欺骗，触控板+亮度键依赖 |
| `_Q1C → XQ1C` | 亮度键（Fn+F12 亮度增） |
| `_Q1D → XQ1D` | 亮度键（Fn+F11 亮度减） |
| `_Q52 → XQ52` | 翻盖模式 EC 事件 |

### 亮度键方案

Lenovo Yoga 9 15IMH5 的 EC 亮度键通知链路存在两个阻断点（SWBL 标志位 + DIDX OpRegion 未初始化），导致 BrightnessKeys.kext 单独使用时无法收到通知。

解决方案：SSDT-Brightness + BrightnessKeys.kext 配合使用：

```
Fn+F11/F12 → EC 触发 _Q1C/_Q1D
  ↓
SSDT-Brightness (Darwin 分支) → Notify(DD1F, 0x86/0x87)
  ↓
BrightnessKeys 收到 → 派发 F15/F14 键盘事件
  ↓
macOS 系统调节亮度
```

- **SSDT-Brightness**：覆盖 `_Q1C`/`_Q1D`，绕过 SWBL/DIDX 阻断，发送 ACPI 标准亮度通知
- **BrightnessKeys**：接收 ACPI 通知并转为 macOS 键盘事件
- `_Q1C → XQ1C` 和 `_Q1D → XQ1D` 重命名补丁必须保留（避免方法冲突 + Windows 兼容性）
- SSDT-Brightness 使用 `_OSI("Darwin")` 检查，Windows 下调用原始 `XQ1C()`/`XQ1D()`

## Kext 列表

| kext | 来源 | 用途 |
|------|------|------|
| Lilu | 源码编译 | 核心框架（必须第一位加载） |
| VirtualSMC | 上游 release | SMC 模拟 |
| SMCProcessor | 上游 release | CPU 温度监控（VirtualSMC 插件） |
| SMCBatteryManager | 上游 release | 电池状态（VirtualSMC 插件） |
| WhateverGreen | 上游 release | 显卡驱动 |
| AppleALC | 源码编译（最小化） | 声卡驱动 |
| RestrictEvents | 上游 release | 系统事件限制 |
| BrightnessKeys | 上游 release | ACPI 亮度通知→键盘事件 |
| ECEnabler | 上游 release | EC 电池支持 |
| YogaSMC | 源码编译 | Yoga 特性支持（Fn键、风扇、翻盖模式） |
| NVMeFix | 上游 release | NVMe 电源管理 |
| VoodooPS2Controller | 上游 release | 键盘驱动 |
| VoodooI2C + VoodooI2CHID | 上游 release | I2C 触摸板 |
| AMFIPass | OCLP payloads | AMFI 签名绕过 |
| IOSkywalkFamily | OCLP payloads | Skywalk 网络栈（Sequoia/Tahoe） |
| IO80211FamilyLegacy | OCLP payloads | WiFi API 兼容层（Sequoia/Tahoe） |
| AirportItlwm | 源码编译（最小化） | Intel WiFi |
| IntelBluetoothFirmware | 源码编译（最小化） | Intel 蓝牙固件加载 |
| IntelBTPatcher | 源码编译（最小化） | Intel 蓝牙运行时补丁 |
| BlueToolFixup | 上游 release | 蓝牙修复（Monterey+） |
| HoRNDIS | 上游 release | USB 网络共享 |
| USBMap | 上游 release | USB 端口映射 |

> 已移除 SMCSuperIO（无 Super I/O 芯片，detectDevice() 空转）和 SMCLightSensor（无光线传感器）。

> **关键依赖**：Lilu 必须第一位加载；VirtualSMC 插件在其后；IOSkywalkFamily → IO80211FamilyLegacy → AirportItlwm 为 Intel WiFi 依赖链。AirportItlwm 子类化 IO80211Controller（IO80211FamilyLegacy 定义），编译时强依赖，AirPortBrcmNIC.kext 作为其插件需存在，无法精简。

## 关键配置

### apfs_aligned.efi（Tahoe FV2 Bug 规避）

- macOS Tahoe 的 APFS UEFI 驱动存在 FileVault 2 软件解密 Bug（acidanthera/bugtracker #2499）
- apfs_aligned.efi 来自 macOS Sequoia，不包含此 Bug
- 配置：`UEFI.APFS.EnableJumpstart = false` + 手动加载 apfs_aligned.efi
- 即使不使用 FileVault，Tahoe 升级安装可能自动启用 FV2，建议始终使用此方案

### YogaSMC SSDT 补丁

SSDT-RCSM 来自 [YogaSMC/SSDTSample](https://github.com/zhen-zen/YogaSMC/tree/master/YogaSMC/SSDTSample)，实现 Clamshell Mode（翻盖模式）控制。当 `RCSM = 1` 时，`_Q52` 翻盖 EC 事件被静默忽略，屏幕不会因翻盖而唤醒。**必须保留**。

YogaSMC SSDTSample 中仅 SSDT-ECRW 和 SSDT-RCSM 适用于此设备，其余（SSDT-THINK/WMIS/YVPC）因 EC 布局或 DSDT 不匹配不适用。

## 自动构建

GitHub Actions 每周一自动检查上游更新并构建。详见 `.github/workflows/build-kexts.yml`。

## 目录结构

```
├── config/device-config.json   # 设备配置（PCI ID、codec、patches）
├── patches/                    # 源码补丁（SSDT、AppleALC、IntelBT）
│   └── ssdt/                   # ACPI SSDT 补丁（.aml）
├── scripts/                    # 构建脚本（最小化、下载、更新检查）
├── acpi/                       # 原始 ACPI 表转储（参考用）
├── BIOS/                       # BIOS 相关文件
└── USB定制/                    # USB 端口映射
```

## Intel AX201 蓝牙配置详解

### 硬件参数（ioreg 实测值）

| 参数 | 值 | 说明 |
|------|-----|------|
| USB VID | 0x8087 (32903) | Intel |
| USB PID | 0x0026 (38) | AX201 Bluetooth |
| hw_variant | 0x13 (19) | HrP (Harrison Peak) = AX201 |
| hw_platform | 0x37 (55) | Gen3 平台 |
| hw_revision | 0x10 (16) | 硬件修订版 |
| fw_variant | 0x06 (bootloader) / 0x23 (operational) | 冷启动=bootloader, 热重启=operational |
| 固件名 | ibt-19-16-0.sfi | 基于 hw_variant + hw_revision + fw_revision |
| 固件名格式 | ibt-{hw_variant}-{hw_revision}-{fw_revision}.sfi | Gen2 风格（hw_variant >= 0x11） |

### macOS Tahoe 蓝牙必需配置

| 项目 | 值 | 说明 |
|------|-----|------|
| IntelBluetoothFirmware.kext | v2.5.0+ | 固件加载（未精简版，需包含 ibt-19-* 固件） |
| IntelBTPatcher.kext | v2.5.0+ | 运行时补丁（修复 LE Scan 崩溃） |
| BlueToolFixup.kext | v2.7.2+ | 替代 IntelBluetoothInjector（Monterey+ 必需） |
| IntelBluetoothInjector.kext | **不要使用** | Monterey+ 不需要，会导致冲突 |
| boot-args | `-amfipassbeta -ibtcompatbeta` | `-ibtcompatbeta` 让 IntelBTPatcher 在 beta macOS 上加载（Dortania 官方推荐）；`-amfipassbeta` 让 AMFIPass 在 beta macOS 上加载 |
| NVRAM bluetoothInternalControllerInfo | 16字节全零 | bluetoothd 识别内部蓝牙控制器必需 |
| NVRAM bluetoothExternalDongleFailed | 0x00 | 防止回退到 BCM_4350C2 虚拟芯片 |

### 蓝牙不工作的根本原因

**NVRAM 缺少 `bluetoothInternalControllerInfo` 和 `bluetoothExternalDongleFailed`**。

`bluetoothd` 启动流程：
1. 查找 USB 蓝牙设备 → 找到 Intel AX201 (VID=0x8087, PID=0x0026)
2. 检查 `bluetoothInternalControllerInfo` → **缺失时**判定 "Internal controller info missing"
3. 检查 `bluetoothExternalDongleFailed` → **缺失时**判定 "External dongle not found"
4. 回退到 BCM_4350C2 虚拟芯片 → 蓝牙无法工作

修复：在 config.plist 的 NVRAM Add (7C436110-AB2A-4BBB-A880-FE41995C9F82) 中添加：
```xml
<key>bluetoothExternalDongleFailed</key>
<data>AA==</data>
<key>bluetoothInternalControllerInfo</key>
<data>AAAAAAAAAAAAAAAAAAA=</data>
```

### 排查过程中走过的弯路

1. **精简版固件缺失（假问题）**：`minimize-intelbt.py` 的 `firmware_prefix` 为 `"ibt-18-"`，但 AX201 对应 `ibt-19-*`。实际上 AX201 在 bootloader 模式下固件会被重新上传，operational 模式下固件已加载，都不影响蓝牙是否工作。

2. **修改 IntelBluetoothFirmware 源码（非必要）**：`IntelBluetoothOpsGen3::setup()` 中有 TODO workaround bug，当 `INTEL_HW_PLATFORM != 0x37` 时直接 `return true` 不设置 `loadedFirmwareName`。但实际测试发现 AX201 走的是 legacy bootloader 路径（`actLen=10=sizeof(IntelVersion)`），不经过 TLV/Gen3 路径。`loadedFirmwareName` 为空不影响蓝牙工作。

3. **误加 IntelBluetoothInjector（方向性错误）**：macOS Monterey+ 明确不需要 IntelBluetoothInjector，需要的是 `BlueToolFixup.kext`。两者同时启用会冲突。
