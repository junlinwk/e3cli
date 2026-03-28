<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey?logo=apple&logoColor=white" alt="Platform">
  <img src="https://img.shields.io/github/license/junlinwk/e3cli?color=green" alt="License">
  <img src="https://img.shields.io/github/v/tag/junlinwk/e3cli?label=version&color=orange" alt="Version">
</p>

<h1 align="center">e3cli</h1>

<p align="center">
  <b>Moodle 自動化 CLI 工具 — 支援任何 Moodle 平台</b><br>
  同步課程、下載教材、提交作業、查看公告 — 全部在終端機完成。
</p>

<p align="center">
  <a href="#安裝">安裝</a> &bull;
  <a href="#快速開始">快速開始</a> &bull;
  <a href="#指令說明">指令</a> &bull;
  <a href="#互動模式">互動模式</a> &bull;
  <a href="#安全性">安全性</a> &bull;
  <a href="#claude-code-整合">Claude Code</a> &bull;
  <a href="./README.md">English</a>
</p>

---

> **正確用法：** 寫完作業後懶得開網頁，直接用 CLI 上傳。
>
> ~~**錯誤用法：** 給 Claude Code 自動拉新的 E3 作業，做完上傳，省時省力。（不建議這麼做）~~

## 功能

- **登入** — Moodle Web Service API 認證，帳密加密儲存
- **課程** — 按學期分組列出修課清單，查看課程簡介
- **作業** — 查看作業描述、截止日期、繳交狀態、附件
- **下載** — 批次下載課程教材（預設只抓當期）
- **提交 / 編輯** — 上傳、提交、重新上傳（覆蓋）作業
- **公告** — 查看課程公告內容
- **成員** — 列出課程成員（教師與學生）
- **訊息** — 發送 Moodle 站內訊息給課程成員
- **同步** — 一個指令拉取所有新內容（教材 + 作業狀態）
- **排程** — 基於 cron 的自動同步
- **互動介面** — 完整方向鍵互動介面 (`e3cli i`)
- **雙語** — 完整中文/英文支援
- **多校支援** — 支援任何 Moodle 平台（可設定學期格式）

## 支援平台

| 平台 | 架構 | 狀態 |
|------|------|------|
| macOS | Apple Silicon (ARM64) | :white_check_mark: 支援 |
| macOS | Intel (x86_64) | :white_check_mark: 支援 |
| Linux | x86_64 | :white_check_mark: 支援 |
| Linux | ARM64 | :white_check_mark: 支援 |

需要 **Python 3.11+**。

---

## 安裝

### Homebrew（推薦）

```bash
brew tap junlinwk/e3cli
brew install e3cli
```

### pipx

```bash
pipx install git+https://github.com/junlinwk/e3cli.git
```

### pip

```bash
pip install git+https://github.com/junlinwk/e3cli.git
```

### 從原始碼安裝

```bash
git clone https://github.com/junlinwk/e3cli.git
cd e3cli
pip install -e ".[dev]"
```

> 安裝完成後，`e3cli` 即可作為系統指令使用。

### 更新

| 安裝方式 | 更新指令 |
|---------|---------|
| Homebrew | `brew update && brew upgrade e3cli` |
| pipx (GitHub) | `pipx install git+https://github.com/junlinwk/e3cli.git --force` |
| pipx (PyPI) | `pipx upgrade e3cli` |
| pip (PyPI) | `pip install e3cli --upgrade` |

---

## 快速開始

```bash
# 1. 登入（首次使用會啟動互動式引導）
e3cli login --save

# 2. 列出修課清單
e3cli courses

# 3. 下載當期教材
e3cli download

# 4. 查看作業與截止日期
e3cli assignments

# 5. 提交作業
e3cli submit <作業ID> homework.pdf

# 6. 啟動互動模式
e3cli i
```

---

## 指令說明

### `e3cli login`

登入 Moodle 帳號並儲存 API token。

```bash
e3cli login                    # 互動式輸入
e3cli login -u <學號>           # 指定帳號
e3cli login --save             # 加密儲存帳密，下次自動登入
e3cli login --refresh          # 用已儲存的帳密重新取得 token
```

### `e3cli logout`

安全清除所有已儲存的認證資料。

```bash
e3cli logout
```

### `e3cli courses`

按學期分組列出修課清單。

```bash
e3cli courses                  # 只顯示當期
e3cli courses --all            # 所有學期
e3cli courses --semester 1142  # 指定學期
```

### `e3cli assignments`

查看作業，含描述、截止日期、繳交狀態、附件數量。按緊急度排序（未繳最近到期在上，已過期在中，已繳交在下）。

```bash
e3cli assignments                  # 當期
e3cli assignments --due-soon 7     # 7 天內到期
e3cli assignments --all            # 所有學期
e3cli assignments --detail <ID>    # 查看完整描述與附件
```

### `e3cli download`

下載課程教材（預設只下載當期）。

```bash
e3cli download                     # 當期課程（預設）
e3cli download --all               # 所有學期
e3cli download --course "OS"       # 模糊比對課程名稱
e3cli download --select            # 互動式選擇課程
```

檔案預設儲存在 `~/e3-downloads/<課程>/<章節>/`，已下載的檔案會自動跳過。

### `e3cli submit`

上傳並提交作業。

```bash
e3cli submit <作業ID> file1.pdf file2.zip
e3cli submit <作業ID> report.pdf --text "一些備註"
e3cli submit <作業ID> late-hw.pdf --force     # 過期仍可強制提交
```

對同一作業重新提交會覆蓋之前的繳交。

### `e3cli announcements`

查看課程公告。

```bash
e3cli announcements -c "OS"                # 列出公告
e3cli announcements -c "OS" --detail <ID>  # 查看完整內容與附件
```

### `e3cli members`

列出課程成員，含角色與 email。

```bash
e3cli members -c "OS"          # 教師在前
```

### `e3cli message`

發送 Moodle 站內訊息（對方是否收到 email 取決於其通知設定）。

```bash
e3cli message <用戶ID> "你好"     # 直接發送
e3cli message <用戶ID>            # 互動式多行輸入
```

### `e3cli sync`

一鍵拉取所有新教材並更新作業狀態。

```bash
e3cli sync                     # 當期課程（預設）
e3cli sync --all               # 所有學期
e3cli sync --course "OS"       # 指定課程
e3cli sync --quiet             # 安靜模式（適用排程）
```

### `e3cli schedule`

管理基於 crontab 的自動同步。

```bash
e3cli schedule enable                  # 預設每 60 分鐘
e3cli schedule enable --interval 30    # 每 30 分鐘
e3cli schedule disable                 # 停用
e3cli schedule status                  # 查看目前狀態
```

### `e3cli setup`

重新執行互動式設定引導（語言、Moodle 網址、學期格式、別名、下載目錄、登入）。

```bash
e3cli setup
```

### `e3cli version`

```bash
e3cli version
```

---

## 互動模式

輸入 `e3cli i` 啟動完整的方向鍵互動介面：

```
╭──────────────── e3cli v0.5.0 ────────────────╮
│  王小明  |  114學年第2學期  |  6 courses      │
╰──────────────────────────────────────────────╯

────────────────── 主選單 ──────────────────────
❯ 選擇課程 (114學年第2學期)
  選擇課程 (所有學期)
  作業
  同步課程
  離開

↑↓ navigate  →/Enter select  ← back  / search
────────────────────────────────────────────────
```

### 操作方式

| 按鍵 | 功能 |
|------|------|
| `↑` `↓` | 移動選取 |
| `→` / `Enter` | 進入選項 |
| `←` / `Esc` | 返回上一層 |
| `/` 或直接打字 | 搜尋/篩選 |
| `q` | 離開/返回 |

### 課程選單

進入課程後可使用：
- **課程簡介** — 查看課程描述
- **教材** — 瀏覽與下載檔案（顯示下載狀態）
- **作業** — 查看描述、附件、繳交狀態；提交或重新上傳
- **公告** — 閱讀課程公告
- **成員** — 查看成員列表，直接發送訊息
- **成績** — 查看成績項目

### 作業詳情

選擇作業後可看到：
- 完整描述（HTML 轉文字）
- 附件列表可下載
- 目前已繳交的檔案
- 提交 (`s`) 或 編輯/重新上傳 (`e`)，支援 Tab 自動補全
- 檔案選擇器中可用 `!` 進入終端模式

### 檔案選擇器

提交或重新上傳作業時：
- 顯示當前目錄與檔案列表
- **Tab 補全**檔案路徑（跟 shell 一樣）
- **`!指令`** 執行 shell 指令（如 `!ls -la`）
- **`!`** 單獨輸入進入互動終端模式（輸入 `exit` 返回）
- 上傳前有確認提示

---

## 設定檔

位置：`~/.e3cli/config.toml`

```toml
[moodle]
url = "https://e3p.nycu.edu.tw"
service = "moodle_mobile_app"

[storage]
download_dir = "~/e3-downloads"

[schedule]
interval_minutes = 60
notify = true

[general]
lang = "zh"              # "zh" 或 "en"，省略則自動偵測
semester_format = "nycu"  # "nycu", "western", "none"
alias = ""                # 自訂指令名稱（如 "moodle"）
```

### 學期格式

| 格式 | 適用學校 | 範例 |
|------|---------|------|
| `nycu`（預設） | 陽明交大、台大等台灣大學 | `1142` = 114學年第2學期 |
| `western` | 西曆年制學校 | `2025` |
| `none` | 任何學校（不過濾） | 所有課程視為當期 |

首次執行時自動建立。可手動編輯，或執行 `e3cli setup` 重新設定。

---

## 安全性

### 帳密儲存機制

e3cli 使用 **PBKDF2-HMAC-SHA256** 金鑰衍生搭配完整性驗證來保護帳密：

```
~/.e3cli/
  key               # 256-bit 隨機加密金鑰   (chmod 600)
  credentials.enc   # 加密後的帳號密碼       (chmod 600)
  token             # Moodle API token       (chmod 600)
```

| 措施 | 說明 |
|------|------|
| 加密 | PBKDF2-HMAC-SHA256（10 萬次迭代）+ XOR 串流加密 |
| 完整性 | 每次讀取時驗證 HMAC-SHA256 |
| 檔案權限 | `chmod 600` — 僅擁有者可讀寫 |
| 密碼輸入 | `getpass` — 不會出現在 shell 歷史記錄或 CLI 參數中 |
| 登出 | `e3cli logout` 先覆寫為零再刪除 |
| 金鑰分離 | 加密金鑰與加密資料分開儲存 |

### 不會儲存的東西

- :x: 不會在磁碟上存明文密碼
- :x: 不會把帳密寫進 `config.toml`
- :x: 不會存在環境變數中
- :x: 不會出現在 shell 歷史記錄中

### 建議

- `e3cli login --save` 只在信任的機器上使用
- 在共用電腦上用完後執行 `e3cli logout`
- `~/.e3cli/` 目錄已加入 `.gitignore` — 永遠不要 commit 它

---

## Claude Code 整合

本專案提供 `CLAUDE.md` 文件，教 [Claude Code](https://claude.ai/code) 如何使用 e3cli 作為自動化助手。當 Claude Code 在此專案目錄下運行時，它可以：

- 同步並檢查新作業 (`e3cli sync`)
- 讀取作業描述與已下載的教材
- 協助完成作業（需人工審查）
- 提交完成的作業 (`e3cli submit`)

詳見 [`CLAUDE.md`](./CLAUDE.md) 和 [`e3cli/agent_prompt.md`](./e3cli/agent_prompt.md)。

> **注意：** Claude Code 在提交作業前一定會先詢問確認。

---

## 本地資料

| 路徑 | 用途 |
|------|------|
| `~/.e3cli/config.toml` | 使用者設定 |
| `~/.e3cli/token` | Moodle API token (chmod 600) |
| `~/.e3cli/key` | 加密金鑰 (chmod 600) |
| `~/.e3cli/credentials.enc` | 加密後的帳密 (chmod 600) |
| `~/.e3cli/data/e3cli.db` | SQLite 追蹤資料庫 |
| `~/e3-downloads/` | 下載的課程教材 |

---

## 開發

```bash
git clone https://github.com/junlinwk/e3cli.git
cd e3cli
make dev       # pip install -e ".[dev]"
make lint      # ruff check
make test      # pytest
make build     # python -m build
```

## 未來規劃

- [x] 方向鍵互動介面
- [x] 學期過濾（預設當期）
- [x] 多校 Moodle 支援
- [x] 作業描述與附件
- [x] 課程公告
- [x] 課程成員與訊息
- [x] 編輯/重新提交作業
- [ ] AI 教材自動摘要
- [ ] AI 輔助作業撰寫
- [ ] 智慧截止日期通知與優先排序
- [ ] 桌面通知（Linux `notify-send`、macOS `osascript`）
- [ ] 平行下載加速

---

## 授權

[MIT](./LICENSE)
