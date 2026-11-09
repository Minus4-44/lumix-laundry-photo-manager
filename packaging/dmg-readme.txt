LUMIX 洗衣机管理器 · macOS 0.12.1（Apple 芯片）
=================================================

安装
----
1. 把左侧的 “LUMIX Photo Manager.app” 拖到右侧的 Applications（应用程序）文件夹。
2. 首次打开：在“应用程序”里右键点击图标 → “打开”，再点“打开”确认。
   （本版本未做 Apple 开发者签名与公证，直接双击会被系统拦截一次；确认后以后可正常双击。）

   如果仍提示“已损坏，无法打开”，请在“终端”执行：
   xattr -dr com.apple.quarantine "/Applications/LUMIX Photo Manager.app"

运行要求
--------
- macOS 11 或更高，仅支持 Apple 芯片（M1/M2/M3/M4 等 arm64）。
- 无需安装 Python；人脸模型已内置（YuNet + SFace，OpenCV Zoo）。
- 首次使用需在“管理照片库”里选择或新建照片库文件夹；macOS 会请求文件夹访问授权，请允许。
- 设置与缩略图缓存位置：~/Library/Application Support/Pianji
- Photoshop 关联：在“设置”里填 /Applications/Adobe Photoshop 2026/Adobe Photoshop 2026.app
  （点“选择 Photoshop.app”时用文件夹选择窗口选整个 .app 即可；未安装会留空。）

与 Windows 版的差异
-------------------
- 窗口开合淡入淡出使用 Windows 原生动画，macOS 上改用系统默认显示方式。
- 整库删除在 macOS 上通过“移到废纸篓”实现，可从废纸篓还原。
- 其余选片、导入、人脸分组、修图阶段与成片关联流程与 Windows 版一致。

第三方许可
----------
见应用内 licenses/ 与 THIRD-PARTY-NOTICES.md；人脸模型许可见 models/ 内 LICENSE 文件。
由 Edison-0315 制作；LUMIX 字标仅用于个人设计展示，与 Panasonic / LUMIX 无官方隶属关系。
