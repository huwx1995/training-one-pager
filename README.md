# 培训一纸通

> ⚠️ **系统要求：Mac 版需要 macOS 14 或更新版本及 Apple 芯片（M 系列）；Windows 版需要 Windows 10/11 64 位及 Intel/AMD 处理器。**

把培训文档或录音整理成一页摘要，逐条保留原文出处，支持人工核对、编辑和导出。

**当前状态：内测版本，采用 AGPL v3（AGPL-3.0-only）。** [GitHub 仓库](https://github.com/huwx1995/training-one-pager)提供源码。[Mac 完整版 v0.1.0-beta.3](https://github.com/huwx1995/training-one-pager/releases/tag/v0.1.0-beta.3)和 [Windows 完整版 v0.1.0-beta.4](https://github.com/huwx1995/training-one-pager/releases/tag/v0.1.0-beta.4)均内置语音模型，请按电脑系统下载。

## 能做什么

- 解析 PPT/PPTX、DOC/DOCX、PDF、TXT、XLS/XLSX；支持本地录音转写及按时间回放。
- 核对解析结果，人工确认文字脱敏和图片遮挡。
- 选择无需密钥的本地规则草稿，或配置自己的模型服务生成内容。
- 编辑摘要与框架图，核对出处，导出 PDF、PNG、Word、Markdown 或 JSON；具体导出受当前版式及单页检查限制。

本地规则对复杂语义的理解有限。自动解析、脱敏、转写和模型生成结果都需要人工核对。

## Mac 内测安装

从上方 Mac 版本页面下载 `macOS-arm64-full.dmg` 完整版安装包，将“培训一纸通”拖入“应用程序”，再双击打开。工作台会自动在默认浏览器中打开，结束后请在应用控制窗口点击“退出”。

安装包自带 Python、音频工具、本地 OCR 和语音模型。旧 DOC/PPT 仍需 LibreOffice 或先另存为新格式。目标 macOS 14 及以上，当前仅在开发 Mac 验证；未做 Developer ID 签名及公证，首次打开可能被系统拦截。核实文件来源后按系统“隐私与安全性”提示处理，不要关闭全局安全保护。

安装版数据位于用户“资源库/Application Support/TrainingOnePager”，可在控制窗口打开。源码版仍使用项目目录的 `uploads/`。构建与验证见 [Mac 构建说明](packaging/macos/README.md)。

## Windows 内测安装

从上方 Windows 版本页面下载 `windows-x64-full.zip` 完整版。解压整个压缩包，打开 `TrainingOnePager` 文件夹，双击 `TrainingOnePager.exe`；请保留同目录下的 `_internal` 和 `sources` 文件夹。Windows 版已在普通 Windows 电脑上完成试用；构建和自动检查见 [Windows 构建说明](packaging/windows/README.md)。

## 从源码启动

目前以 Python 3.12 验证。Mac/Linux 在项目目录打开终端：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-release.txt
.venv/bin/python server.py
```

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-release.txt
.\.venv\Scripts\python.exe server.py
```

打开终端显示的本机地址，默认是 `http://127.0.0.1:8000`。使用期间保留终端，结束时按 Ctrl+C。Mac 可在依赖安装完成后使用 `启动一纸通.command`，默认从 8011 端口启动。

## 第一次体验

上传 `samples/虚构培训材料.txt` → 本地解析并核对 → 确认脱敏 → 选择“本地规则” → 填写生成要求 → 生成后核对出处 → 编辑并导出。

如需模型生成，在“模型设置”里选择平台，填写自己的 API Key，点击“测试并使用”。模型服务可能收费；工具不提供共享密钥。

## 功能依赖

| 功能 | 附加条件 |
| --- | --- |
| 旧版 DOC/PPT | 本机安装 LibreOffice，或先自行另存为 DOCX/PPTX |
| 录音转写 | FFmpeg、ffprobe、whisper-cli；首次下载约 547 MiB 的语音模型 |
| 图片文字识别 | Mac 使用系统 Vision；其他系统需要可用的中文 Tesseract |
| 中文 Word 导出 | 本机安装可用中文字体；系统自带字体或自行安装 Noto Sans CJK SC 等 |

这些外部程序、语音模型和字体没有随源码目录附带；Mac 完整版已内置音频工具、OCR 和语音模型，LibreOffice 和字体不随包提供。

本次 Mac 构建所用 Python 运行时包含一条特定根证书的拒绝信任策略，因此安装包保留了相应的公开证书策略文件；其用途和验证方法见 [Mac 构建说明](packaging/macos/README.md)。该文件不是密钥，也不用于关闭 HTTPS 验证。

## 数据与隐私

文档解析和录音转写在本机执行。使用远程大模型生成、问答或连接测试会发起网络请求；生成及问答会发送人工确认脱敏后的文字。请先阅读[数据说明](docs/隐私与数据说明.md)。

更多操作见[使用说明](docs/使用说明.md)。组件来源和发行待办见[第三方许可说明](THIRD_PARTY_NOTICES.md)。

## 开发检查

安装 Python 3.12 和 Node.js 或 Deno 后：

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
sh scripts/check.sh
```

Windows 可使用虚拟环境 Python 执行 `-m unittest discover -s tests -q` 和 `scripts/smoke_local.py`，再用 Node.js 对前端脚本逐项执行 `--check`；完整 shell 脚本需要兼容环境。

## 许可证

本项目原创代码按 **GNU Affero General Public License version 3 only**（`AGPL-3.0-only`）提供，完整条款见 [LICENSE](LICENSE)。允许使用、修改和商业使用；分发、修改及通过网络提供修改版时，须遵守相应的许可、声明和对应源码提供要求。软件按原样提供，不作担保，具体以许可证为准。

第三方组件保留各自版权及许可，见 [第三方许可说明](THIRD_PARTY_NOTICES.md)。本项目的许可不替代第三方许可。提供源码的具体要求及当前状态见 [源码获取说明](docs/源码获取说明.md)。

使用者上传的材料、录音、API Key 及个人配置不应纳入源码分发；它们不会仅因使用本软件就成为按本项目许可证公开的内容。安装包内实际组件的许可和对应源码材料仍需在打包时补齐。
