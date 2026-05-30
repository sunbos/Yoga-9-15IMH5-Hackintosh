# USBMap.kext / USBPorts.kext Info.plist 格式对比分析

## 收集到的样本

### 样本1: 本项目 USBPorts.kext (MacBookPro16,1)
- **来源**: /Users/sunbo/docs/Yoga-9-15IMH5-Hackintosh/USB定制/外接雷电扩展坞/MacBookPro16,1/USBPorts.kext
- **驱动类型**: com.apple.driver.AppleUSBMergeNub
- **IOProviderClass**: AppleIntelCNLUSBXHCI
- **匹配方式**: IOPCIPrimaryMatch (0x06ed8086)

### 样本2: YOGA920-Hackintosh USBPorts.kext (MacBookPro15,2)
- **来源**: bioqxu/YOGA920-Hackintosh 仓库
- **驱动类型**: com.apple.driver.AppleUSBMergeNub
- **IOProviderClass**: AppleUSBXHCISPTLP
- **匹配方式**: IOPCIPrimaryMatch (0x9d2f8086)

### 样本3: lenovo-yoga-920-hackintosh USBPorts.kext (MacBookPro15,2)
- **来源**: cephasara/lenovo-yoga-920-hackintosh 仓库
- **驱动类型**: com.apple.driver.AppleUSBMergeNub
- **IOProviderClass**: AppleUSBXHCISPTLP
- **匹配方式**: IOPCIPrimaryMatch (0x9d2f8086)

### 样本4: Nucintosh USBPorts.kext (iMac19,1)
- **来源**: zearp/Nucintosh 仓库
- **驱动类型**: com.apple.driver.AppleUSBHostMergeProperties
- **IOProviderClass**: AppleUSBHostController
- **匹配方式**: IOParentMatch > IOPropertyMatch > pcidebug

### 样本5: MSI-B360M USBMap.kext (iMac19,1)
- **来源**: GeQ1an/MSI-B360M-MORTAR-HACKINTOSH-OPENCORE-EFI 仓库
- **驱动类型**: com.apple.driver.AppleUSBHostMergeProperties
- **IOProviderClass**: AppleUSBHostController
- **匹配方式**: IOParentMatch > IOPropertyMatch > pcidebug

### 样本6: NUC8i7BEH USBPorts.kext (Macmini8,1)
- **来源**: corenel/NUC8i7BEH-macOS 仓库
- **驱动类型**: com.apple.driver.AppleUSBMergeNub
- **IOProviderClass**: AppleIntelCNLUSBXHCI
- **匹配方式**: IOPCIPrimaryMatch (0x9ded8086)

## 格式对比分析

### 1. 顶层属性对比

| 属性 | 样本1-3,6 (MergeNub) | 样本4-5 (HostMerge) |
|------|---------------------|---------------------|
| CFBundleDevelopmentRegion | English | English |
| CFBundleGetInfoString | 1.0 Copyright © 2018-2020 Headsoft... | v1.1 |
| CFBundleIdentifier | com.Headsoft.USBPorts | com.dhinakg.USBToolBox.map |
| CFBundleInfoDictionaryVersion | 6.0 | 6.0 |
| CFBundleName | USBPorts | UTBMap |
| CFBundlePackageType | KEXT | KEXT |
| CFBundleShortVersionString | 1.0 | 1.1 |
| CFBundleSignature | ???? | ???? |
| CFBundleVersion | 1.0 | 1.1 |
| IOKitPersonalities | ✓ | ✓ |
| OSBundleRequired | Root | Root |

### 2. IOKitPersonalities 结构对比

#### AppleUSBMergeNub 格式 (样本1-3,6)
```xml
<key>IOKitPersonalities</key>
<dict>
    <key>MacBookPro16,1-XHC</key>  <!-- 命名格式: 型号-控制器 -->
    <dict>
        <key>CFBundleIdentifier</key>
        <string>com.apple.driver.AppleUSBMergeNub</string>
        <key>IOClass</key>
        <string>AppleUSBMergeNub</string>
        <key>IONameMatch</key>
        <string>XHC</string>
        <key>IOPCIPrimaryMatch</key>
        <string>0x06ed8086</string>  <!-- PCI 设备 ID -->
        <key>IOProbeScore</key>
        <integer>5000</integer>
        <key>IOProviderClass</key>
        <string>AppleIntelCNLUSBXHCI</string>
        <key>IOProviderMergeProperties</key>
        <dict>
            <!-- USB 端口定义 -->
        </dict>
        <key>model</key>
        <string>MacBookPro16,1</string>
    </dict>
</dict>
```

#### AppleUSBHostMergeProperties 格式 (样本4-5)
```xml
<key>IOKitPersonalities</key>
<dict>
    <key>_SB.PCI0.XHC</key>  <!-- 命名格式: ACPI 路径 -->
    <dict>
        <key>CFBundleIdentifier</key>
        <string>com.apple.driver.AppleUSBHostMergeProperties</string>
        <key>IOClass</key>
        <string>AppleUSBHostMergeProperties</string>
        <key>IOParentMatch</key>  <!-- 使用 IOParentMatch 而非 IOPCIPrimaryMatch -->
        <dict>
            <key>IOPropertyMatch</key>
            <dict>
                <key>pcidebug</key>
                <string>0:20:0</string>  <!-- PCI 地址格式 -->
            </dict>
        </dict>
        <key>IOProviderClass</key>
        <string>AppleUSBHostController</string>
        <key>IOProviderMergeProperties</key>
        <dict>
            <!-- USB 端口定义 -->
        </dict>
        <key>model</key>
        <string>iMac19,1</string>
    </dict>
</dict>
```

### 3. 关键差异总结

#### 驱动类型差异
- **AppleUSBMergeNub**: 传统格式，兼容性好，支持 macOS 10.x - 14.x
- **AppleUSBHostMergeProperties**: 现代格式，macOS 15 (Tahoe) 推荐使用

#### 匹配方式差异
- **IOPCIPrimaryMatch**: 直接匹配 PCI 设备 ID (如 0x06ed8086)
- **IOParentMatch + pcidebug**: 通过 PCI 地址匹配 (如 0:20:0)

#### IOProviderClass 差异
- **AppleUSBMergeNub 格式**: 使用具体的控制器类 (如 AppleIntelCNLUSBXHCI, AppleUSBXHCISPTLP)
- **AppleUSBHostMergeProperties 格式**: 使用通用的 AppleUSBHostController

#### 端口定义差异
- **AppleUSBMergeNub 格式**: 端口包含 `name` 字段
- **AppleUSBHostMergeProperties 格式**: 端口通常不包含 `name` 字段

### 4. OSBundleRequired 和 CFBundleSignature

所有样本都包含：
- **OSBundleRequired**: Root (必需，确保 kext 在启动时加载)
- **CFBundleSignature**: ???? (标准占位符)

### 5. macOS Tahoe 兼容性

根据 Hackintool 源码分析，macOS Tahoe 需要：
1. 使用 AppleUSBHostMergeProperties 替代 AppleUSBMergeNub
2. 添加 usb-port-number 和 usb-port-type 字段
3. 保持向后兼容性

## 建议

1. **兼容性优先**: 使用 AppleUSBMergeNub 格式，兼容性最好
2. **Tahoe 支持**: 如需支持 macOS 15，考虑使用 AppleUSBHostMergeProperties 格式
3. **混合方案**: 可以同时包含两种格式的 personality，确保最大兼容性

## 详细样本数据

### 样本1: 本项目 USBPorts.kext (MacBookPro16,1)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDevelopmentRegion</key>
	<string>English</string>
	<key>CFBundleGetInfoString</key>
	<string>1.0 Copyright © 2018-2020 Headsoft. All rights reserved.</string>
	<key>CFBundleIdentifier</key>
	<string>com.Headsoft.USBPorts</string>
	<key>CFBundleInfoDictionaryVersion</key>
	<string>6.0</string>
	<key>CFBundleName</key>
	<string>USBPorts</string>
	<key>CFBundlePackageType</key>
	<string>KEXT</string>
	<key>CFBundleShortVersionString</key>
	<string>1.0</string>
	<key>CFBundleSignature</key>
	<string>????</string>
	<key>CFBundleVersion</key>
	<string>1.0</string>
	<key>IOKitPersonalities</key>
	<dict>
		<key>MacBookPro16,1-XHC</key>
		<dict>
			<key>CFBundleIdentifier</key>
			<string>com.apple.driver.AppleUSBMergeNub</string>
			<key>IOClass</key>
			<string>AppleUSBMergeNub</string>
			<key>IONameMatch</key>
			<string>XHC</string>
			<key>IOPCIPrimaryMatch</key>
			<string>0x06ed8086</string>
			<key>IOProbeScore</key>
			<integer>5000</integer>
			<key>IOProviderClass</key>
			<string>AppleIntelCNLUSBXHCI</string>
			<key>IOProviderMergeProperties</key>
			<dict>
				<key>kUSBSleepPortCurrentLimit</key>
				<integer>2100</integer>
				<key>kUSBSleepPowerSupply</key>
				<integer>5100</integer>
				<key>kUSBWakePortCurrentLimit</key>
				<integer>2100</integer>
				<key>kUSBWakePowerSupply</key>
				<integer>5100</integer>
				<key>port-count</key>
				<data>
				EQAAAA==
				</data>
				<key>ports</key>
				<dict>
					<key>HS01</key>
					<dict>
						<key>UsbConnector</key>
						<integer>0</integer>
						<key>name</key>
						<string>HS01</string>
						<key>port</key>
						<data>
						AQAAAA==
						</data>
					</dict>
					<key>HS02</key>
					<dict>
						<key>UsbConnector</key>
						<integer>9</integer>
						<key>name</key>
						<string>HS02</string>
						<key>port</key>
						<data>
						BAAAAA==
						</data>
					</dict>
					<key>HS03</key>
					<dict>
						<key>UsbConnector</key>
						<integer>9</integer>
						<key>name</key>
						<string>HS03</string>
						<key>port</key>
						<data>
						BwAAAA==
						</data>
					</dict>
					<key>HS04</key>
					<dict>
						<key>UsbConnector</key>
						<integer>255</integer>
						<key>name</key>
						<string>HS04</string>
						<key>port</key>
						<data>
						CAAAAA==
						</data>
					</dict>
					<key>HS05</key>
					<dict>
						<key>UsbConnector</key>
						<integer>255</integer>
						<key>name</key>
						<string>HS05</string>
						<key>port</key>
						<data>
						CQAAAA==
						</data>
					</dict>
					<key>HS06</key>
					<dict>
						<key>UsbConnector</key>
						<integer>255</integer>
						<key>name</key>
						<string>HS06</string>
						<key>port</key>
						<data>
						DgAAAA==
						</data>
					</dict>
					<key>SS01</key>
					<dict>
						<key>UsbConnector</key>
						<integer>3</integer>
						<key>name</key>
						<string>SS01</string>
						<key>port</key>
						<data>
						EQAAAA==
						</data>
					</dict>
				</dict>
			</dict>
			<key>model</key>
			<string>MacBookPro16,1</string>
		</dict>
		<key>MacBookPro16,1-XHC-8086_15ec</key>
		<dict>
			<key>CFBundleIdentifier</key>
			<string>com.apple.driver.AppleUSBMergeNub</string>
			<key>IOClass</key>
			<string>AppleUSBMergeNub</string>
			<key>IONameMatch</key>
			<string>XHC</string>
			<key>IOPCIPrimaryMatch</key>
			<string>0x15ec8086</string>
			<key>IOProbeScore</key>
			<integer>5000</integer>
			<key>IOProviderClass</key>
			<string>AppleUSBXHCITR</string>
			<key>IOProviderMergeProperties</key>
			<dict>
				<key>kUSBSleepPortCurrentLimit</key>
				<integer>2100</integer>
				<key>kUSBSleepPowerSupply</key>
				<integer>5100</integer>
				<key>kUSBWakePortCurrentLimit</key>
				<integer>2100</integer>
				<key>kUSBWakePowerSupply</key>
				<integer>5100</integer>
				<key>port-count</key>
				<data>
				BAAAAA==
				</data>
				<key>ports</key>
				<dict>
					<key>SS01</key>
					<dict>
						<key>UsbConnector</key>
						<integer>9</integer>
						<key>name</key>
						<string>SS01</string>
						<key>port</key>
						<data>
						AwAAAA==
						</data>
					</dict>
					<key>SS02</key>
					<dict>
						<key>UsbConnector</key>
						<integer>9</integer>
						<key>name</key>
						<string>SS02</string>
						<key>port</key>
						<data>
						BAAAAA==
						</data>
					</dict>
				</dict>
			</dict>
			<key>model</key>
			<string>MacBookPro16,1</string>
		</dict>
	</dict>
	<key>OSBundleRequired</key>
	<string>Root</string>
</dict>
</plist>
```

### 样本4: Nucintosh USBPorts.kext (iMac19,1) - AppleUSBHostMergeProperties 格式
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDevelopmentRegion</key>
	<string>English</string>
	<key>CFBundleGetInfoString</key>
	<string>v1.1</string>
	<key>CFBundleIdentifier</key>
	<string>com.dhinakg.USBToolBox.map</string>
	<key>CFBundleInfoDictionaryVersion</key>
	<string>6.0</string>
	<key>CFBundleName</key>
	<string>UTBMap</string>
	<key>CFBundlePackageType</key>
	<string>KEXT</string>
	<key>CFBundleShortVersionString</key>
	<string>1.1</string>
	<key>CFBundleSignature</key>
	<string>????</string>
	<key>CFBundleVersion</key>
	<string>1.1</string>
	<key>IOKitPersonalities</key>
	<dict>
		<key>_SB.PCI0.RP05.PXSX.TBDU.XHC</key>
		<dict>
			<key>CFBundleIdentifier</key>
			<string>com.apple.driver.AppleUSBHostMergeProperties</string>
			<key>IOClass</key>
			<string>AppleUSBHostMergeProperties</string>
			<key>IOParentMatch</key>
			<dict>
				<key>IOPropertyMatch</key>
				<dict>
					<key>pcidebug</key>
					<string>58:0:0</string>
				</dict>
			</dict>
			<key>IOProviderClass</key>
			<string>AppleUSBHostController</string>
			<key>IOProviderMergeProperties</key>
			<dict>
				<key>port-count</key>
				<data>AwAAAA==</data>
				<key>ports</key>
				<dict>
					<key>HS01</key>
					<dict>
						<key>UsbConnector</key>
						<integer>9</integer>
						<key>port</key>
						<data>AQAAAA==</data>
					</dict>
					<key>SS01</key>
					<dict>
						<key>UsbConnector</key>
						<integer>9</integer>
						<key>port</key>
						<data>AwAAAA==</data>
					</dict>
				</dict>
			</dict>
			<key>model</key>
			<string>iMac19,1</string>
		</dict>
		<key>_SB.PCI0.XHC</key>
		<dict>
			<key>CFBundleIdentifier</key>
			<string>com.apple.driver.AppleUSBHostMergeProperties</string>
			<key>IOClass</key>
			<string>AppleUSBHostMergeProperties</string>
			<key>IOParentMatch</key>
			<dict>
				<key>IOPropertyMatch</key>
				<dict>
					<key>pcidebug</key>
					<string>0:20:0</string>
				</dict>
			</dict>
			<key>IOProviderClass</key>
			<string>AppleUSBHostController</string>
			<key>IOProviderMergeProperties</key>
			<dict>
				<key>port-count</key>
				<data>EAAAAA==</data>
				<key>ports</key>
				<dict>
					<key>HS01</key>
					<dict>
						<key>UsbConnector</key>
						<integer>3</integer>
						<key>port</key>
						<data>AQAAAA==</data>
					</dict>
					<key>HS02</key>
					<dict>
						<key>UsbConnector</key>
						<integer>3</integer>
						<key>port</key>
						<data>AgAAAA==</data>
					</dict>
					<key>HS03</key>
					<dict>
						<key>UsbConnector</key>
						<integer>3</integer>
						<key>port</key>
						<data>AwAAAA==</data>
					</dict>
					<key>HS04</key>
					<dict>
						<key>UsbConnector</key>
						<integer>3</integer>
						<key>port</key>
						<data>BAAAAA==</data>
					</dict>
					<key>HS05</key>
					<dict>
						<key>UsbConnector</key>
						<integer>255</integer>
						<key>port</key>
						<data>BQAAAA==</data>
					</dict>
					<key>HS06</key>
					<dict>
						<key>UsbConnector</key>
						<integer>255</integer>
						<key>port</key>
						<data>BgAAAA==</data>
					</dict>
					<key>HS07</key>
					<dict>
						<key>UsbConnector</key>
						<integer>255</integer>
						<key>port</key>
						<data>CgAAAA==</data>
					</dict>
					<key>SS01</key>
					<dict>
						<key>UsbConnector</key>
						<integer>3</integer>
						<key>port</key>
						<data>DQAAAA==</data>
					</dict>
					<key>SS02</key>
					<dict>
						<key>UsbConnector</key>
						<integer>3</integer>
						<key>port</key>
						<data>DgAAAA==</data>
					</dict>
					<key>SS03</key>
					<dict>
						<key>UsbConnector</key>
						<integer>3</integer>
						<key>port</key>
						<data>DwAAAA==</data>
					</dict>
					<key>SS04</key>
					<dict>
						<key>UsbConnector</key>
						<integer>3</integer>
						<key>port</key>
						<data>EAAAAA==</data>
					</dict>
				</dict>
			</dict>
			<key>model</key>
			<string>iMac19,1</string>
		</dict>
	</dict>
	<key>OSBundleRequired</key>
	<string>Root</string>
</dict>
</plist>
```
