## Yoga-9-15IMH5-Hackintosh
### 编辑最小Intel Wi-Fi驱动程序
#### 为了减少开机的启动时间，我们可能需要通过删除AirportItlwm.kext中的冗余固件来减小AirportItlwm.kext的大小。在本指南中，它将帮助您仅保留Intel WiFi卡使用的固件。
```shell
git clone --depth=1 https://github.com/OpenIntelWireless/itlwm.git
cd itlwm git
git clone --depth=1 https://github.com/acidanthera/MacKernelSDK.git
```
#### 打开IORegistryExplorer应用程序，并搜索itlwm。在AirportItlwm下，检查IOModel属性中加载的固件。
