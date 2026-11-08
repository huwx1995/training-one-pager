# 第三方组件与许可说明

核对日期：2026-11-06。本文区分 Python 依赖、外部工具、模型及系统资源。许可原文见 `third_party/licenses/`，文件来源及摘要见 `third_party/license-manifest.json`。

本源码目录包含程序、说明、构建脚本和许可文本，不包含二进制或模型权重。Mac 内测安装版已自带下列选定运行组件和语音模型。安装包的配套上游源码及摘要清单见发行文件和 `packaging/macos/upstream-sources.json`。

## Python 依赖

版本依据当前验证环境；`requirements-release.txt` 固定运行依赖，`requirements-dev.txt` 另外列出测试依赖。固定版本文件不是带哈希的完整构建锁文件。

| 组件 | 版本 | 许可及已收集内容 |
| --- | --- | --- |
| Pillow | 12.3.0 | MIT-CMU；收集安装分发包完整 LICENSE，含其附带组件声明 |
| python-docx | 1.2.0 | MIT；已收集 LICENSE |
| python-pptx | 1.0.2 | MIT；已收集 LICENSE |
| pypdf | 6.10.0 | BSD-3-Clause；已收集 LICENSE |
| PyMuPDF / MuPDF | 1.28.2 / 1.28.2 | AGPL v3 或 Artifex 商业许可；已收集包内双许可声明及标准 AGPL v3 全文 |
| openpyxl | 3.1.5 | MIT；从该版本官方 PyPI 源码分发包收集 LICENCE.rst |
| xlrd | 2.0.2 | BSD；已收集 LICENSE |
| lxml | 6.1.1 | BSD-3-Clause 等；已收集 LICENSE.txt 及 LICENSES.txt；后者引用的底层库及额外文件需按实际安装包补齐 |
| et_xmlfile | 2.0.0 | MIT，部分代码涉及 Python 许可；已从该版本 PyPI 源码包收集 LICENCE.rst、LICENCE.python、AUTHORS.txt |
| XlsxWriter | 3.2.9 | BSD-2-Clause；已收集 LICENSE.txt |
| typing_extensions | 4.16.0 | PSF-2.0；已收集完整 LICENSE，属于运行间接依赖 |
| ReportLab | 4.4.9 | BSD 类许可；仅测试使用，已收集主 LICENSE；若分发整个包，还需检查其附带字体许可 |
| charset-normalizer | 3.5.2 | MIT；仅测试依赖链使用，已收集 LICENSE |

保留第三方原有版权、许可和免责声明。组件名称、原作者姓名及许可中的联系信息属于上游公开声明，不是本项目客户资料，不应为了删除个人信息而破坏应保留的版权通知。

## PyMuPDF 的发行路线

官方提供 AGPL 与商业授权两条路线：[官方许可页](https://pymupdf.io/licensing)、[官方文档](https://pymupdf.readthedocs.io/en/latest/about.html)。

保留当前依赖并走开源路线时，需要按适用 AGPL 条件提供对应源码、保留声明，并评估整个组合程序的许可。仅公开仓库或声明 MIT，不会自动满足所有义务。本项目原创代码已选用 AGPL-3.0-only，完整条款见 [LICENSE](LICENSE)。

如果希望保留专有代码，应核对并获得适用商业授权，或另行替换依赖；替换会影响 PDF 定位、渲染及图片处理能力，需要单独实施和验证。商业使用本身不是 AGPL 的禁止事项。

标准许可全文是帮助核对的参考材料，不能代替实际使用组件版本的版权和其他附带声明。安装包制作时还需补齐 PyMuPDF/MuPDF 构建对应的第三方库许可材料和源码提供方式。

## 外部工具与语音模型

| 项目 | 上游许可信息 | 当前状态及发行前待办 |
| --- | --- | --- |
| FFmpeg / ffprobe | 通常为 LGPL-2.1-or-later；启用部分选项后可能为 GPL；含 nonfree 选项的构建可能不能再分发 | Mac 内测版已内置独立构建的 8.1.2，配置、哈希和对应源码配套提供；其他系统尚未打包 |
| whisper.cpp / whisper-cli | MIT | Mac 内测版已内置 1.7.6 静态构建，保留该版本及其合入组件声明；Accelerate 由系统提供 |
| Whisper 模型 | 当前模型托管仓库标注 MIT；原始 Whisper 项目也提供 MIT 许可 | 发行使用 `ggml-large-v3-turbo-q5_0.bin`，模型卡列出约 547 MiB，SHA-1 为 `e050f7970618a659205450ad97eb95a18d69c9ee`；已收集原始 Whisper LICENSE，来源已锁定为 `5359861c739e955e79d9a303bcbc70fb988958b1`，保留原始 Whisper MIT 许可；详见 `packaging/macos/speech-model.json` |
| LibreOffice | MPL-2.0 及多种第三方许可 | 当前调用独立安装程序；随包分发前需按所选版本检查完整 LICENSE 和第三方材料 |
| Tesseract | Apache-2.0 | 当前调用本机可用程序；若随包提供，需另行收集该版本、Leptonica、语言数据及其他实际依赖许可 |
| macOS Vision / 系统框架 | Apple 系统条款 | 由系统提供，当前不复制系统框架进源码目录 |
| 中文字体 | 因具体字体而异 | 使用本机已安装字体，不随源码分发字体文件；若将来内置 Noto 或其他字体，需收集对应字体许可 |
| Python 运行环境及其库 | Python 及其实际构建依赖各自许可 | 源码版要求自行安装；Mac 内测版已内置 3.12.14，相关声明见本次构建补充及归档 |

FFmpeg 的 LGPL/GPL 条件由实际构建决定，不能把开发机可执行文件直接当成许可已审核的安装包组件。[FFmpeg 官方说明](https://ffmpeg.org/legal.html)

whisper.cpp 代码许可与模型许可分别核对。[whisper.cpp LICENSE](https://github.com/ggml-org/whisper.cpp/blob/master/LICENSE)、[模型卡与文件校验值](https://huggingface.co/ggerganov/whisper.cpp/blob/main/README.md)、[Whisper LICENSE](https://github.com/openai/whisper/blob/main/LICENSE)

其他工具依据：[LibreOffice 许可](https://www.libreoffice.org/licenses/)、[Tesseract 文档](https://tesseract-ocr.github.io/tessdoc/)。

## 后续公开发行事项

项目已选用 AGPL-3.0-only；公开版权署名信息、真实源码下载入口、其他目标系统验证，以及未来新增字体或额外语言数据的分发确认，仍需在相应发行之前完成。本清单保留这些具体缺口，不宣称已获得商业授权。

## Mac 0.1.0-beta.2 内测构建补充

- 使用 Python 3.12.14，已归档 PSF 许可；其静态或运行依赖中的 OpenSSL 3.5.8、bzip2 1.0.8、liblzma/xz 5.4.3、Expat 2.8.3、mpdecimal 4.0.0 及 SQLite 许可/声明一并保留。Apple 系统动态库由系统提供，没有复制到应用。
- PyInstaller 6.22.3 的 bootloader 适用其 GPL 许可及分发例外，完整 COPYING 已收集；证书包 certifi 2026.10.23 的 MPL 许可已收集。打包工具本身仍保留其各自许可。
- lxml 所用 libxml2 2.14.6 与 libxslt 1.1.43 的版权声明已补齐。Pillow 的完整 LICENSE 包含其轮子内多种图像库和字体处理库声明。
- MuPDF 1.28.2 官方完整源码包的 34 份许可/声明文件已归档，包含其第三方和嵌入字体声明；其中也有未在本构建启用的上游可选组件，保留声明不表示应用使用全部组件。
- FFmpeg 8.1.2 从固定源码构建，未启用 GPL、nonfree、网络或自动探测选项；许可证为 LGPL-2.1-or-later 及其各文件适用的条款。配置见 build_tools.py，对应完整源码包与安装包配套提供。
- whisper.cpp 1.7.6 采用静态 CPU/Accelerate 构建，未启用 Metal/OpenMP。该版本 LICENSE、miniaudio 及 stb_vorbis 许可已归档，对应源码包一并提供。
- 当前未内置 LibreOffice、Tesseract 或系统字体文件；Mac 完整版包含上表所列语音模型。后续若增加或更换组件，需要重新核对其版本与许可。

这些记录用于本次受控内测发行，不代表已完成 Developer ID 签名、公证、独立法律审定或所有目标系统验证。正式公开发行时应保持对应安装包、源码和构建清单成套可获取，并填写真实可用的下载位置。
