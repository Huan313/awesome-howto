# C 盘空间不足时，怎样用系统入口清理？

一句话解法：先看分类和可用空间，只处理自己能确认用途的项目。

## 适用与准备

适用于 Windows 10／11 使用者。先保存工作，把仍需保留的文件备份到可打开的位置。清理前在“设置 → 系统 → 存储”记下系统盘可用空间。

## 基础档

1. 打开系统“存储”设置，等分类计算完成，先看临时文件、已安装应用和自己保存的文件各占多少。
2. 打开“临时文件”或系统可见的清理建议，逐项确认。遇到“下载”时先打开下载文件夹核对，回收站先确认没有需要还原的文件。
3. 只处理确认舍得删除的项目。卸载应用走系统“已安装的应用”，不要手动清空 Windows、Program Files 或整个用户应用数据目录。
4. 回到“存储”刷新可用空间，打开至少一个保留的业务文件。释放空间低于预期时，继续定位已知大文件或应用。

## 成功检查

有清理前后两次读数，关键文件能正常打开。存储感知会按开关和设置运行，启用前先核对回收站、下载与云文件选项。

## 证据与核验

- 需求线索为公开支持场景，用户普遍程度待验证。
- 官方依据：[Microsoft 存储感知](https://support.microsoft.com/zh-cn/windows/experience/storage-filemanagement/manage-drive-space-with-storage-sense) · [Windows 更新前释放空间](https://support.microsoft.com/zh-cn/windows/deployment/updates-lifecycle/free-up-space-for-windows-updates)。
- 2026-11-25 本地仅读取 Windows 版本和 C 盘可用量。未清理真实文件，未取得设备清理前后对照。
