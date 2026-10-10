# jobscan

定義搜索關鍵字（城市 / 職位 / 技能等），呼叫 [boss-agent-cli](https://github.com/can4hou6joeng4/boss-agent-cli) 與 [liepin-cli](https://github.com/Viy1204/liepin-cli) 搜索職位，並整理成一份 **HTML 表格報告**。

## 這個工具做什麼

1. 讀取 `config.yaml`（或命令列參數）定義的搜索關鍵字與篩選條件。
2. 呼叫各招聘平台 CLI 執行搜索，解析其 JSON 輸出。
3. 把多平台、多組關鍵字的結果彙整成一頁 HTML 表格報告。

## 關於兩個平台

- **BOSS 直聘（boss-agent-cli）**：求職者端，`boss search` 搜「職位」。預設啟用。
- **獵聘（liepin-cil，liepin-tech-2026）**：求職者端，`liepin-cli job search` 搜「職位」。預設啟用。使用 token 認證（`liepin-cli setup` 或環境變數 `LIEPIN_USER_TOKEN`），不需掃碼。

兩者都是求職者視角搜職位，報告會分別以 `BOSS` / `LIEPIN` 標籤標示來源平台。

## 安裝

### 1) 安裝兩個平台 CLI

```bash
# BOSS（需 Python 3.10+ 與 uv）
uv tool install boss-agent-cli
patchright install chromium        # 安裝瀏覽器內核（登入 / 匯出用）

# 獵聘（求職者端，liepin-tech-2026/liepin-cil，需 Python 3.11+）
git clone https://github.com/liepin-tech-2026/liepin-cil.git
uv tool install --from ./liepin-cil liepin-cli
# 或：cd liepin-cil && pip install -e ".[dev]"
```

確認可用：

```bash
jobscan check
```

### 2) 安裝 jobscan 本體

```bash
pip install -e .
# 或不安裝、直接以模組執行：python -m jobscan.cli ...
```

## 登入 / 認證

```bash
boss login          # BOSS 直聘掃碼（需有瀏覽器、能掃碼的環境）
liepin-cli setup    # 獵聘 token 認證（需可貼上 token 的互動式終端）
# 或非互動：export LIEPIN_USER_TOKEN="x-user-token-xxxxx"
```

> BOSS 登入態存於 `~/.boss-agent`；獵聘 token 存於 `~/.config/liepin-cli/config.json`。未認證時搜索會回報錯誤，報告中會以錯誤區塊顯示。

## 定義搜索關鍵字

### 方式一：設定檔 `config.yaml`

```yaml
searches:
  - query: "后端工程师"
    skills: ["Go", "Kubernetes"]
  - query: "前端工程师"
    skills: ["React", "TypeScript"]
filters:
  city: "深圳"
  salary: ""        # 如 "20-40K"
  experience: ""    # 如 "3-5年"
  education: ""     # 如 "本科"
  job_type: ""      # 全职/兼职/实习
limit: 20
providers:
  boss: { enabled: true }
  liepin: { enabled: true }
```

### 方式二：命令列參數（覆蓋設定檔）

```bash
jobscan run --query 后端工程师 --skill Go --skill K8s --city 深圳 --limit 15
```

## 執行

```bash
jobscan run                       # 用 config.yaml，輸出 reports/report.html
jobscan run -o reports/today.html # 指定輸出
jobscan run --provider boss       # 只跑 BOSS
jobscan run --json-out reports/raw.json   # 另存原始結果 JSON
```

打開 `reports/report.html` 即可看到依平台 / 關鍵字分組的職位表格（職位、公司、薪資、城市、經驗、學歷、技能）。

## 以樣本資料預覽報告（免登入）

想先看報告長相、不想真的連線搜索：

```bash
python examples/demo_report.py
# 產生 reports/sample_report.html
```

## 開發 / 測試

```bash
python -m pytest -q
```

## 免責

請遵守各招聘平台的使用條款與當地法律。工具會驅動瀏覽器並可能觸發平台風控；若遇風控請停止自動化並人工處理。
