# USB 定制说明

## 目录结构

```
USB定制/
├── README.md
├── Pre-Tahoe/          ← macOS 11 (Big Sur) ~ macOS 15 (Sequoia)
│   ├── 不接雷电扩展坞/
│   │   ├── MacBookPro16,1/USBMap.kext
│   │   └── MacBookPro16,4/USBMap.kext
│   └── 外接雷电扩展坞/
│       ├── MacBookPro16,1/USBMap.kext + USBPorts.kext
│       └── MacBookPro16,4/USBMap.kext + USBPorts.kext
└── Tahoe+/             ← macOS 26 (Tahoe) 及以上
    ├── 不接雷电扩展坞/
    │   ├── MacBookPro16,1/USBMap.kext
    │   └── MacBookPro16,4/USBMap.kext
    └── 外接雷电扩展坞/
        ├── MacBookPro16,1/USBMap.kext + USBPorts.kext
        └── MacBookPro16,4/USBMap.kext + USBPorts.kext
```

## macOS 版本选择

| macOS 版本 | 使用目录 | 说明 |
|-----------|---------|------|
| Big Sur ~ Sequoia (11-15) | `Pre-Tahoe/` | 原始格式 |
| **Tahoe (26) 及以上** | **`Tahoe+/`** | 新增 `usb-port-number` 和 `usb-port-type` 键 |

> **Tahoe 版本说明：** 从 macOS Tahoe 开始，USB 子系统要求每个端口同时包含 `usb-port-number`（对应 `port`）和 `usb-port-type`（对应 `UsbConnector`）。Tahoe+ 目录中的文件已通过 [USBMapInjectorEdit](https://github.com/CorpNewt/USBMap/blob/master/USBMapInjectorEdit.command) 转换脚本添加了这些键。

## 三种 kext 格式

| 格式 | 需要额外驱动 | ACPI 需求 | 说明 |
|------|------------|----------|------|
| **USBMap.kext** | ❌ 不需要 | SSDT-EC-USBX | ⭐ 推荐，使用原生 AppleUSBHostMergeProperties |
| **USBPorts.kext** | ❌ 不需要 | SSDT-EC | 无需修复 USB 供电（仅外接扩展坞配置提供） |
| **UTBMap.kext** | ✅ USBToolBox.kext | SSDT-EC-USBX | ❌ 不推荐，USBToolBox 项目已停止维护 |

## 场景说明

| 场景 | 说明 | 控制器 |
|------|------|--------|
| **不接雷电扩展坞** | 笔记本本体 USB 端口 | XHC (0:20:0) + TBDU.XHC (6:0:0) |
| **外接雷电扩展坞** | 包含扩展坞 USB Hub | XHC + TBDU.XHC + 扩展坞 Hub (65:0:0) |

MacBookPro16,1 和 MacBookPro16,4 的端口映射相同。
