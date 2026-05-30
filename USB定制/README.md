# USB 定制说明

## 概述

本目录包含三种格式的 USB 端口映射配置，适用于不同场景。

> **当前 EFI 使用的是 USBMap.kext（已通过 USBMapInjectorEdit 转换为 Tahoe 兼容格式）。**
> GitHub 仓库中的文件为转换前的原始版本，EFI 中的版本已添加 `usb-port-number` 和 `usb-port-type` 键。

## 三种格式对比

| 格式 | 需要额外驱动 | ACPI 需求 | macOS 兼容性 | 推荐度 |
|------|------------|----------|-------------|--------|
| **USBMap.kext** | ❌ 不需要 | SSDT-EC-USBX | ✅ Big Sur ~ Tahoe | ⭐ 推荐 |
| **USBPorts.kext** | ❌ 不需要 | SSDT-EC | ✅ 全版本 | ✅ 可用 |
| **UTBMap.kext** | ✅ 需要 USBToolBox.kext | SSDT-EC-USBX | ⚠️ Tahoe WIP | ❌ 不推荐 |

## 1. USBMap.kext（推荐）

- 使用 macOS 原生 `AppleUSBHostMergeProperties` 驱动注入端口映射
- 不依赖任何第三方驱动，兼容性最好
- 需要修复 USB 供电（ACPI 添加 SSDT-EC-USBX）
- **已在 Tahoe (macOS 26) 上验证正常工作**

### Tahoe 兼容性

从 macOS Tahoe 开始，USBMap.kext 需要额外的键：
- `usb-port-number`（对应 `port`）
- `usb-port-type`（对应 `UsbConnector`）

当前 EFI 中的 USBMap.kext 已通过 CorpNewt/USBMap 的 `USBMapInjectorEdit` 转换脚本添加了这些键。仓库中的原始文件不包含这些键。

## 2. USBPorts.kext

- 使用 `AppleUSBMergeNub` 格式（较旧但稳定）
- 无需修复 USB 供电（内置电源管理配置）
- ACPI 需要 SSDT-EC（而非 SSDT-EC-USBX）
- 仅在外接雷电扩展坞配置中提供

## 3. UTBMap.kext（不推荐）

- 需要配合 USBToolBox.kext 使用
- USBToolBox 项目已基本停止维护（最后更新 2023 年）
- Tahoe 支持为 WIP 状态（不稳定）
- 需要修复 USB 供电（ACPI 添加 SSDT-EC-USBX）

## 场景说明

| 场景 | 目录 | 控制器 |
|------|------|--------|
| 不接雷电扩展坞 | `不接雷电扩展坞/` | XHC + TBDU.XHC（2 个） |
| 外接雷电扩展坞 | `外接雷电扩展坞/` | XHC + TBDU.XHC + 扩展坞 Hub（3 个） |

两个场景中 MacBookPro16,1 和 MacBookPro16,4 的端口映射相同。

## USB 控制器说明

| 控制器 | PCI 地址 | 说明 |
|--------|---------|------|
| `_SB.PCI0.XHC` | 0:20:0 | 主 USB 控制器（7 个端口） |
| `_SB.PCI0.RP21.PXSX.TBDU.XHC` | 6:0:0 | 雷电口 USB 功能（2 个 Type-C 端口） |
| `65:0:0` | 动态分配 | 雷电扩展坞 USB Hub（仅外接扩展坞时出现） |
