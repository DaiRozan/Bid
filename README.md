# 建筑与市政工程技术标生成系统

这是一个 Windows 本地单用户工作台，覆盖建筑工程和市政工程的施工组织设计编制流程。当前产品界面直接使用真实资料模式：上传招标文件后解析、确认事实、编辑目录和章节，再调用配置好的 DeepSeek 生成单章，最后导出可编辑的 DOCX 审核稿。

## 启动

需要 Python 3.11+、Node.js 18+ 和 npm。首次运行会创建 `.venv`、安装后端依赖和前端依赖：

```powershell
Set-Location "C:\Users\18135\Desktop\投标"
Copy-Item .env.example .env
notepad .env
.\run.ps1
```

在 `.env` 中填写 `DEEPSEEK_API_KEY`。默认模型配置为 `https://api.deepseek.com` 与 `deepseek-flash`（对应 DeepSeek V4.1 Flash）；密钥只由后端读取，不会发送到浏览器。系统启动后打开 `http://127.0.0.1:5173`。

也可以分别启动后端和前端：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000
npm --prefix frontend run dev
```

## 使用路径

1. 新建项目并选择建筑工程或市政工程。
2. 在“资料与事实”上传完整 `.zip/.rar` 招标资料包，或单个 DOC/DOCX、文字型 PDF、XLS/XLSX、DWG/DXF；系统递归解包并保存来源层级。
3. 点击“从已解析资料提取事实与要求”，人工修改事实确认值。
4. 在“固定事实库”查看清单、原文和图纸复核结果；核对补疑，确认采用值，然后发布固定版本。原文、分组清单和图纸计算分别保存为 Markdown，完整 CAD 明细另存压缩 JSON 并纳入版本校验。
5. 在“要求与目录”编辑要求和目录、创建章节；在“章节工作区”编辑正文或调用 `deepseek-flash`。生成和重试只使用固定版本的事实及编制要求；项目事实由服务端引用插入，通用叙述从预设语句中选择。修改草稿不会静默改变已发布值。修改编制要求后也需重新发布。模型版本记录事实版本和引用。人工正文编辑仍可修改内容，须自行复核。
6. 运行确定性检查，在“检查与导出”下载可编辑的 `技术标审核稿.docx`。

数据位置由启动工作目录和 `.env` 决定。使用根目录的 `run.ps1` 时默认保存在项目根目录 `data/`，刷新页面后仍可继续编辑。固定版本在 `data/projects/<项目ID>/facts/v0001/` 等目录，发布后不应手动改写；校验不符将拒绝写作。导出文件标记为审核稿。

DWG 需要官方 [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter)，可配置 `ODA_CONVERTER_PATH`；也会检测 `C:\Program Files\ODA` 及当前用户 `%LOCALAPPDATA%\TechnicalBid\tools\oda\ODAFileConverter.exe`。DOC 需要 LibreOffice，可配置 `LIBREOFFICE_PATH`。RAR 使用 Windows 自带 `tar.exe`，不执行压缩包中的程序。Python 依赖由 `run.ps1` 安装。

清单按单位工程、分部、编码、名称、完整特征、单位和数量保存，空数量不补零。以最新明确补疑及清单为采用依据；补疑必须有明确目标和原文证据，日期不明确或目标不唯一时列待确认。图纸原文可逐项确认，图形测量仅用于复核，不能自动当作构件工程量。

图纸读取支持文字、属性、标注、嵌套块变换、闭合图形面积、长度、块实例统计，以及明确长宽高属性的体积计算。原图缺单位、含代理对象或施工范围/重复视图未核定时会列出限制，不推定尺寸或体积。此版本没有完成任意 DWG 的全专业语义识别和工程量自动核准。

## 验证

```powershell
python -m pytest backend/tests -q
npm --prefix frontend run test -- --run
npm --prefix frontend run build
```

真实资料验收（单独验收项目；保留原始 ZIP 不改写）：

```powershell
python -X utf8 scripts/verify_tender.py "招标资料包完整路径.zip" --project-code ACCEPTANCE-20261029 --name "项目名称"
```

可追加 `--reanalyze-materials --publish-test-snapshot --live-generation`，重新分析并验证验收版发布及真实模型生成。验收报告位于 `data/acceptance/验收报告.md`；测试发布不表示专业人员已确认项目资料。

## 当前边界

已接入：DOCX 段落/表格和文字型 PDF 的基础解析、出处定位、项目事实与要求持久化、建筑/市政目录骨架、章节版本、DeepSeek 结构化生成、确定性检查和可编辑 DOCX 导出。

明确未接入或未验证：扫描 PDF/OCR、向量检索、规范现行性自动核验、专业工程计算、语义质量审查、实际 Word/WPS 分页统计、多人协作和权限。扫描件会保留原文件并标记为“待处理”；未核验规范不会自动当作现行依据；页数显示“未验证”。模型生成内容和工程结论必须由专业人员复核。

历史案例和规范资料通过“案例规范”页面登记，规范初始状态为“待核验”。跨项目资料不会自动成为当前项目事实。
