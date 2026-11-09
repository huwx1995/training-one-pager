# Windows 完整版测试压缩包

这套文件以已发布的 Mac `v0.1.0-beta.3` 应用源码为基础，制作 Windows 10/11 x64 完整版。目标是一个 ZIP：解压整个 `TrainingOnePager` 文件夹，双击其中的 `TrainingOnePager.exe`，语音模型、音频工具和中文 OCR 均随包提供。只提供完整版；旧版 DOC/PPT 仍需 LibreOffice 或先另存为 DOCX/PPTX。

当前交付物是**构建准备文件**，还不是可运行的 Windows 程序。PyInstaller 必须在 Windows 上运行。仓库里的 `Build Windows complete test ZIP` GitHub Actions 使用 Windows 2022 构建机，人工触发后只上传临时测试 Artifact，不自动发布 Release。先检查构建及合成材料测试，再请普通 Windows 10/11 电脑试用；测试通过后才能向朋友分发。

构建流程：校验审查清单 → 安装 Python 依赖 → 运行回归测试 → 下载并校验固定上游源码、语音模型和 OCR 数据 → 编译 Windows FFmpeg、whisper.cpp 和 Tesseract → PyInstaller 冻结程序 → 把模型及项目源码放入完整包 → 用合成材料检查启动、解析、导出、音频工具、OCR、TLS 和退出 → 上传 ZIP、源码包和 SHA256 校验值。

源码审查清单位于 `reviewed-files.json`，列表中的字节摘要必须与构建源码一致。`.gitattributes` 保持跨系统换行字节一致。不要为了让构建通过而跳过清单检查。构建日志或测试文件不包含真实用户材料和 API Key。

Windows EXE 尚未签名，下载后的系统安全提示需要用户核实来源；不能要求关闭全局安全保护。应用只监听本机回环地址。压缩包应整体解压，不能只复制 EXE。首次测试请使用虚构材料。

构建完成后还需在普通 Windows 电脑核对：打开/退出、DOCX/PPTX/PDF/XLSX、录音转写、图片 OCR、Word/图片/PDF 导出、本人输入的 API Key 连接。GitHub Windows 2022 测试通过不能代替真实电脑验收。
