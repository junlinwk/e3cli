<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey?logo=apple&logoColor=white" alt="Platform">
  <img src="https://img.shields.io/github/license/junlinwk/e3cli?color=green" alt="License">
  <img src="https://img.shields.io/github/v/tag/junlinwk/e3cli?label=version&color=orange" alt="Version">
</p>

<h1 align="center">e3cli</h1>

<p align="center">
  <b>NYCU E3 Moodle 自動化 CLI 工具</b><br>
  同步課程、下載教材、提交作業 — 全部在終端機完成。
</p>

<p align="center">
  <a href="#安裝">安裝</a> &bull;
  <a href="#快速開始">快速開始</a> &bull;
  <a href="#指令說明">指令</a> &bull;
  <a href="#安全性">安全性</a> &bull;
  <a href="./README.md">English</a>
</p>

---

> **正確用法：** 寫完作業後懶得開網頁，直接用 CLI 上傳。
>
> ~~**錯誤用法：** 給 Claude Code 自動拉新的 E3 作業，做完上傳，省時省力。（不建議這麼做）~~

## 功能

- **登入** — Moodle Web Service API 認證，帳密加密儲存
- **課程** — 列出所有修課清單
- **作業** — 查看作業、截止日期、提交狀態
- **下載** — 批次下載課程教材，自動跳過已下載檔案
- **提交** — 直接從 CLI 上傳並提交作業
- **同步** — 一個指令拉取所有新內容（教材 + 作業狀態）
- **排程** — 基於 cron 的自動同步
- **雙語** — 完整中文/英文支援

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

# 3. 下載所有教材
e3cli download --all

# 4. 查看作業與截止日期
e3cli assignments

# 5. 提交作業
e3cli submit <作業ID> homework.pdf

# 6. 啟用自動同步（每小時）
e3cli schedule enable
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

以表格形式列出所有修課。

```bash
e3cli courses
```

### `e3cli assignments`

查看作業、截止日期與提交狀態。

```bash
e3cli assignments                  # 所有作業
e3cli assignments --due-soon 7     # 7 天內到期的作業
```

### `e3cli download`

下載課程教材到本地。

```bash
e3cli download --all               # 所有課程
e3cli download --course "OS"       # 指定課程（支援模糊比對）
```

檔案預設儲存在 `~/e3-downloads/<課程>/<章節>/`，已下載的檔案會自動跳過（透過 SQLite 追蹤）。

### `e3cli submit`

上傳並提交作業。

```bash
e3cli submit <作業ID> file1.pdf file2.zip
e3cli submit <作業ID> report.pdf --text "一些備註"
e3cli submit <作業ID> late-hw.pdf --force     # 過期仍可強制提交
```

### `e3cli sync`

一鍵拉取所有新教材並更新作業狀態。

```bash
e3cli sync                # 互動式輸出
e3cli sync --quiet        # 安靜模式（適用排程）
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

重新執行互動式設定引導（語言、Moodle 網址、下載目錄、登入）。

```bash
e3cli setup
```

### `e3cli version`

```bash
e3cli version
```

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
lang = "zh"    # "zh" 或 "en"，省略則自動偵測
```

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

- [ ] AI 教材自動摘要
- [ ] AI 輔助作業撰寫
- [ ] 智慧截止日期通知與優先排序
- [ ] 桌面通知（Linux `notify-send`、macOS `osascript`）
- [ ] 依學期篩選課程
- [ ] 平行下載加速

---

## 授權

[MIT](./LICENSE)
