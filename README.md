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
2. 在“资料与事实”上传 `.docx` 或文字型 `.pdf`，确认解析片段和来源位置。
3. 点击“从已解析资料提取事实与要求”，人工修改事实确认值。
4. 在“要求与目录”编辑编制要求和章节目录，按目录创建章节。
5. 在“章节工作区”编辑正文或调用 `deepseek-flash` 生成当前章节，人工版本会保留在历史版本中。
6. 运行确定性检查，在“检查与导出”下载可编辑的 `技术标审核稿.docx`。

所有项目、原文件、数据库和导出文件默认保存在 `backend/data/`，刷新页面后仍可继续编辑。导出文件明确标记为审核稿。

## 验证

```powershell
python -m pytest backend/tests -q
npm --prefix frontend run test -- --run
npm --prefix frontend run build
```

## 当前边界

已接入：DOCX 段落/表格和文字型 PDF 的基础解析、出处定位、项目事实与要求持久化、建筑/市政目录骨架、章节版本、DeepSeek 结构化生成、确定性检查和可编辑 DOCX 导出。

明确未接入或未验证：扫描 PDF/OCR、向量检索、规范现行性自动核验、专业工程计算、语义质量审查、实际 Word/WPS 分页统计、多人协作和权限。扫描件会保留原文件并标记为“待处理”；未核验规范不会自动当作现行依据；页数显示“未验证”。模型生成内容和工程结论必须由专业人员复核。

历史案例和规范资料通过“案例规范”页面登记，规范初始状态为“待核验”。跨项目资料不会自动成为当前项目事实。
