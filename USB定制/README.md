# 使用USB定制说明
## 1.UTBMap.kext 
#### 需要UTBMap.kext + USBToolBox.kext组合才可以使用USB定制，需要修复USB供电
#### 因为这台电脑需要仿冒EC，所以如果想要使用UTBMap.kext的话，就需要ACPI添加SSDT-EC-USBX，Kernel添加UTBMap.kext + USBToolBox.kext
## 2.USBMap.kext 
#### 可以使用直接使用的USB定制，需要修复USB供电
#### 因为这台电脑需要仿冒EC，所以如果想要使用USBMap.kext的话，就需要ACPI添加SSDT-EC-USBX，Kernel添加USBMap.kext
## 3.USBPort.kext 
#### 可以使用直接使用的USB定制，无需修复USB供电
#### 因为这台电脑需要仿冒EC，所以如果想要使用USBPort.kext的话，就需要ACPI添加SSDT-EC，Kernel添加USBPort.kext

### 三种组合都是可以的看个人喜好
