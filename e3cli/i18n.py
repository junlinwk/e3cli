"""
雙語支援 — 根據系統語言自動切換中文/英文。

使用者可透過環境變數 E3CLI_LANG=en 或 E3CLI_LANG=zh 手動指定。
"""

from __future__ import annotations

import locale
import os

_STRINGS: dict[str, dict[str, str]] = {
    # === CLI help ===
    "cli.help": {
        "zh": "NYCU E3 Moodle 自動化工具",
        "en": "NYCU E3 Moodle automation tool",
    },
    "cli.login": {"zh": "登入取得 token", "en": "Login and get token"},
    "cli.logout": {"zh": "清除認證資料", "en": "Clear credentials"},
    "cli.courses": {"zh": "列出修課清單", "en": "List enrolled courses"},
    "cli.assignments": {"zh": "列出作業與截止日期", "en": "List assignments and deadlines"},
    "cli.download": {"zh": "下載課程教材", "en": "Download course materials"},
    "cli.submit": {"zh": "提交作業", "en": "Submit assignment"},
    "cli.sync": {"zh": "全量同步", "en": "Full sync"},
    "cli.schedule": {"zh": "管理定時同步排程", "en": "Manage sync schedule"},
    "cli.setup": {"zh": "重新執行初始設定引導", "en": "Re-run setup wizard"},
    "cli.version": {"zh": "顯示版本", "en": "Show version"},

    # === Login ===
    "login.prompt_user": {"zh": "帳號", "en": "Username"},
    "login.prompt_pass": {"zh": "密碼: ", "en": "Password: "},
    "login.connecting": {"zh": "正在連線 {url} ...", "en": "Connecting to {url} ..."},
    "login.success": {"zh": "✓ 登入成功！Token 已儲存。", "en": "✓ Login successful! Token saved."},
    "login.success_saved": {
        "zh": "✓ 登入成功！Token 已儲存，帳密已加密保存。",
        "en": "✓ Login successful! Token saved, credentials encrypted.",
    },
    "login.hint_save": {
        "zh": "提示: 加上 --save 可記住帳密，下次用 --refresh 自動重新登入。",
        "en": "Tip: use --save to remember credentials, --refresh to auto-login next time.",
    },
    "login.no_saved": {
        "zh": "找不到已儲存的帳密，請先用 e3cli login --save 登入。",
        "en": "No saved credentials found. Run e3cli login --save first.",
    },
    "login.use_saved": {
        "zh": "使用已儲存的帳號 ({user}) 登入？",
        "en": "Login with saved account ({user})?",
    },
    "login.refreshing": {
        "zh": "使用已儲存的帳密重新取得 token ({user}) ...",
        "en": "Refreshing token with saved credentials ({user}) ...",
    },
    "login.opt_username": {"zh": "學號/帳號", "en": "Student ID / Username"},
    "login.opt_save": {"zh": "加密儲存帳密，下次自動登入", "en": "Save credentials (encrypted) for auto-login"},
    "login.opt_refresh": {"zh": "使用已儲存的帳密重新取得 token", "en": "Refresh token using saved credentials"},

    # === Logout ===
    "logout.done": {"zh": "✓ 所有認證資料已安全清除。", "en": "✓ All credentials securely erased."},

    # === Courses ===
    "courses.title": {"zh": "修課清單", "en": "Enrolled Courses"},
    "courses.col_id": {"zh": "ID", "en": "ID"},
    "courses.col_code": {"zh": "課程代碼", "en": "Code"},
    "courses.col_name": {"zh": "課程名稱", "en": "Course Name"},
    "courses.empty": {"zh": "找不到任何課程。", "en": "No courses found."},

    # === Assignments ===
    "assign.title": {"zh": "作業列表", "en": "Assignments"},
    "assign.col_course": {"zh": "課程", "en": "Course"},
    "assign.col_name": {"zh": "作業名稱", "en": "Assignment"},
    "assign.col_due": {"zh": "截止日期", "en": "Due Date"},
    "assign.col_status": {"zh": "狀態", "en": "Status"},
    "assign.no_deadline": {"zh": "無截止日", "en": "No deadline"},
    "assign.expired": {"zh": "已過期", "en": "Expired"},
    "assign.days_left": {"zh": "{n}天後", "en": "in {n} days"},
    "assign.empty": {"zh": "沒有符合條件的作業。", "en": "No matching assignments."},
    "assign.submitted": {"zh": "已繳交", "en": "Submitted"},
    "assign.draft_status": {"zh": "草稿", "en": "Draft"},
    "assign.not_submitted": {"zh": "未繳交", "en": "Not submitted"},
    "assign.reopened": {"zh": "重新開放", "en": "Reopened"},
    "assign.checking_status": {"zh": "正在查詢繳交狀態...", "en": "Checking submission status..."},
    "assign.opt_due_soon": {"zh": "只顯示 N 天內到期的作業", "en": "Show assignments due within N days"},

    # === Download ===
    "dl.need_flag": {"zh": "請指定 --course 或 --all", "en": "Specify --course or --all"},
    "dl.no_match": {"zh": "找不到符合 '{q}' 的課程", "en": "No course matching '{q}'"},
    "dl.no_new": {"zh": "沒有新檔案", "en": "No new files"},
    "dl.progress": {"zh": "下載中...", "en": "Downloading..."},
    "dl.done": {
        "zh": "✓ 完成！下載 {new} 個新檔案，略過 {skip} 個已存在的檔案。",
        "en": "✓ Done! Downloaded {new} new files, skipped {skip} existing.",
    },
    "dl.saved_to": {
        "zh": "教材儲存於: {path}",
        "en": "Materials saved to: {path}",
    },
    "dl.opt_course": {"zh": "只下載特定課程 (課程代碼或名稱的子字串)", "en": "Download specific course (substring match)"},
    "dl.opt_all": {"zh": "下載所有課程的教材", "en": "Download all course materials"},

    # === Submit ===
    "submit.not_found": {"zh": "檔案不存在: {f}", "en": "File not found: {f}"},
    "submit.checking": {"zh": "檢查作業 #{id} 狀態...", "en": "Checking assignment #{id} status..."},
    "submit.check_fail": {"zh": "✗ 無法取得作業資訊: {e}", "en": "✗ Cannot get assignment info: {e}"},
    "submit.past_due": {
        "zh": "✗ 作業已於 {dt} 截止。使用 --force 可強制提交。",
        "en": "✗ Assignment was due {dt}. Use --force to submit anyway.",
    },
    "submit.uploading": {"zh": "上傳 {n} 個檔案...", "en": "Uploading {n} file(s)..."},
    "submit.submitting": {"zh": "提交作業中...", "en": "Submitting..."},
    "submit.ok": {"zh": "✓ 作業提交成功！", "en": "✓ Assignment submitted!"},
    "submit.draft": {
        "zh": "⚠ 作業已儲存為草稿，可能需要到 Moodle 手動確認提交。",
        "en": "⚠ Saved as draft. You may need to confirm on Moodle.",
    },
    "submit.opt_text": {"zh": "線上文字內容 (可選)", "en": "Online text content (optional)"},
    "submit.opt_force": {"zh": "強制提交（即使已過截止日）", "en": "Force submit (even past deadline)"},

    # === Sync ===
    "sync.syncing": {"zh": "同步中 — {name}", "en": "Syncing — {name}"},
    "sync.new_assign": {"zh": "★ 新作業: [{course}] {name}", "en": "★ New: [{course}] {name}"},
    "sync.assign_fail": {"zh": "取得作業資訊失敗: {e}", "en": "Failed to get assignments: {e}"},
    "sync.done": {
        "zh": "✓ 同步完成 — {files} 個新檔案, {assigns} 個新作業",
        "en": "✓ Sync done — {files} new files, {assigns} new assignments",
    },
    "sync.opt_quiet": {"zh": "安靜模式（適用排程）", "en": "Quiet mode (for cron)"},

    # === Schedule ===
    "sched.enabled": {"zh": "✓ 已啟用定時同步，每 {m} 分鐘執行一次。", "en": "✓ Auto-sync enabled, every {m} minutes."},
    "sched.disabled": {"zh": "✓ 已停用定時同步。", "en": "✓ Auto-sync disabled."},
    "sched.status_on": {"zh": "✓ 排程已啟用", "en": "✓ Schedule active"},
    "sched.status_off": {
        "zh": "排程未啟用。使用 e3cli schedule enable 來啟用。",
        "en": "Schedule not active. Run e3cli schedule enable to activate.",
    },
    "sched.opt_interval": {"zh": "同步間隔 (分鐘)", "en": "Sync interval (minutes)"},

    # === Setup wizard ===
    "setup.welcome": {"zh": "首次使用，讓我們快速完成設定！", "en": "First time? Let's set things up!"},
    "setup.step_url": {"zh": "Moodle 網址", "en": "Moodle URL"},
    "setup.step_url_hint": {
        "zh": "預設為 NYCU E3 平台，直接按 Enter 使用預設值",
        "en": "Default is NYCU E3. Press Enter to use default.",
    },
    "setup.step_dir": {"zh": "教材下載目錄", "en": "Download directory"},
    "setup.step_dir_hint": {"zh": "課程教材會下載到這個資料夾", "en": "Course materials will be saved here"},
    "setup.step_save": {"zh": "儲存設定", "en": "Save config"},
    "setup.config_saved": {"zh": "✓ 設定已儲存至 {path}", "en": "✓ Config saved to {path}"},
    "setup.step_login": {"zh": "登入帳號", "en": "Login"},
    "setup.want_login": {"zh": "現在要登入嗎？", "en": "Login now?"},
    "setup.prompt_id": {"zh": "帳號 (學號)", "en": "Username (Student ID)"},
    "setup.want_save_creds": {"zh": "記住帳密？(加密儲存，下次自動登入)", "en": "Remember credentials? (encrypted, auto-login)"},
    "setup.login_fail_hint": {
        "zh": "沒關係，之後可以用 e3cli login 重新登入。",
        "en": "No worries, run e3cli login later.",
    },
    "setup.done_title": {"zh": "設定完成！", "en": "Setup complete!"},
    "setup.done_body": {
        "zh": (
            "接下來你可以：\n"
            "  [cyan]e3cli courses[/cyan]        列出修課清單\n"
            "  [cyan]e3cli assignments[/cyan]    查看作業與截止日期\n"
            "  [cyan]e3cli download --all[/cyan] 下載所有教材\n"
            "  [cyan]e3cli sync[/cyan]           一鍵同步所有內容\n"
            "  [cyan]e3cli --help[/cyan]         查看所有指令"
        ),
        "en": (
            "You can now:\n"
            "  [cyan]e3cli courses[/cyan]        List enrolled courses\n"
            "  [cyan]e3cli assignments[/cyan]    View assignments & deadlines\n"
            "  [cyan]e3cli download --all[/cyan] Download all materials\n"
            "  [cyan]e3cli sync[/cyan]           Sync everything\n"
            "  [cyan]e3cli --help[/cyan]         Show all commands"
        ),
    },

    # === Common ===
    "common.not_logged_in": {
        "zh": "尚未登入，請先執行 e3cli login",
        "en": "Not logged in. Run e3cli login first.",
    },
    "common.no_courses": {"zh": "沒有課程。", "en": "No courses."},

    # === Semester ===
    "sem.current": {"zh": "當期課程 ({sem})", "en": "Current semester ({sem})"},
    "sem.all_semesters": {"zh": "所有學期", "en": "All semesters"},
    "sem.other": {"zh": "其他", "en": "Other"},

    # === Interactive TUI ===
    "tui.title": {"zh": "E3 互動式介面", "en": "E3 Interactive"},
    "tui.main_menu": {"zh": "主選單", "en": "Main Menu"},
    "tui.select_course": {"zh": "選擇課程", "en": "Select course"},
    "tui.search_hint": {"zh": "輸入課程名稱或代碼搜尋，按 Enter 進入，q 返回", "en": "Type to search, Enter to select, q to go back"},
    "tui.course_menu": {"zh": "課程選單", "en": "Course Menu"},
    "tui.materials": {"zh": "教材", "en": "Materials"},
    "tui.assignments": {"zh": "作業", "en": "Assignments"},
    "tui.grades": {"zh": "成績", "en": "Grades"},
    "tui.download_all": {"zh": "下載所有教材", "en": "Download all materials"},
    "tui.back": {"zh": "返回", "en": "Back"},
    "tui.quit": {"zh": "離開", "en": "Quit"},
    "tui.enter_number": {"zh": "請輸入編號", "en": "Enter number"},
    "tui.invalid": {"zh": "無效的輸入", "en": "Invalid input"},
    "tui.no_grades": {"zh": "無法取得成績資料", "en": "Cannot retrieve grade data"},
    "tui.grade_item": {"zh": "項目", "en": "Item"},
    "tui.grade_value": {"zh": "成績", "en": "Grade"},
    "tui.grade_range": {"zh": "範圍", "en": "Range"},
    "tui.grade_pct": {"zh": "百分比", "en": "Percentage"},
    "tui.file_section": {"zh": "章節", "en": "Section"},
    "tui.file_name": {"zh": "檔名", "en": "Filename"},
    "tui.file_size": {"zh": "大小", "en": "Size"},
    "tui.select_download": {"zh": "輸入編號下載，a 全部下載，q 返回", "en": "Enter number to download, a for all, q to go back"},
    "tui.downloaded": {"zh": "✓ 已下載: {f}", "en": "✓ Downloaded: {f}"},
    "tui.submit_select": {"zh": "選擇要提交的作業", "en": "Select assignment to submit"},
    "tui.assign_detail": {"zh": "作業詳情", "en": "Assignment Detail"},
    "tui.assign_desc": {"zh": "作業描述", "en": "Description"},
    "tui.assign_attachments": {"zh": "附件", "en": "Attachments"},
    "tui.assign_no_desc": {"zh": "（無描述）", "en": "(No description)"},
    "tui.assign_no_attach": {"zh": "（無附件）", "en": "(No attachments)"},
    "tui.view_detail": {"zh": "輸入編號查看作業詳情，q 返回", "en": "Enter # to view detail, q to go back"},
    "tui.assign_submit": {"zh": "提交作業", "en": "Submit assignment"},
    "tui.assign_dl_attach": {"zh": "下載附件", "en": "Download attachments"},
    "tui.assign_dl_all_attach": {"zh": "下載所有附件", "en": "Download all attachments"},
    "tui.submit_file_prompt": {"zh": "輸入要上傳的檔案路徑", "en": "Enter file path to upload"},
    "tui.cwd": {"zh": "當前目錄: {path}", "en": "Current directory: {path}"},
    "tui.files_in_dir": {"zh": "目錄下的檔案:", "en": "Files in directory:"},
    "tui.more_files": {"zh": "... 還有 {n} 個檔案 (輸入檔名篩選)", "en": "... {n} more files (type to filter)"},
    "tui.shell_hint": {"zh": "! 開頭執行終端指令 (例: !ls)，單獨 ! 進入終端模式", "en": "Prefix ! to run shell (e.g. !ls), just ! for shell mode"},
    "tui.shell_mode": {"zh": "終端模式 — 輸入指令，輸入 exit 或按 Ctrl+D 返回 e3cli", "en": "Shell mode — type commands, type exit or Ctrl+D to return"},
    "tui.confirm_submit": {"zh": "確認提交 {f} 到 {a}？", "en": "Submit {f} to {a}?"},
    "tui.submit_cancelled": {"zh": "已取消提交", "en": "Submission cancelled"},
    "tui.press_enter": {"zh": "Enter/← 返回", "en": "Enter/← to go back"},
    "tui.new_assign_alert": {"zh": "🔔 有 {n} 個新作業！", "en": "🔔 {n} new assignment(s)!"},
    "tui.sync_courses": {"zh": "同步課程", "en": "Sync courses"},
    "tui.select_sync": {"zh": "選擇要同步的課程", "en": "Select courses to sync"},

    # === Download updated ===
    "dl.current_only": {
        "zh": "預設只下載當期課程。使用 --all 下載所有學期。",
        "en": "Downloading current semester only. Use --all for all semesters.",
    },
    "dl.select_prompt": {"zh": "選擇要下載的課程（輸入編號，逗號分隔）", "en": "Select courses to download (enter numbers, comma-separated)"},

    # === Sync updated ===
    "sync.current_only": {
        "zh": "預設只同步當期課程。使用 --all 同步所有學期。",
        "en": "Syncing current semester only. Use --all for all semesters.",
    },
    "sync.select_prompt": {"zh": "選擇要同步的課程（輸入編號，逗號分隔）", "en": "Select courses to sync (enter numbers, comma-separated)"},

    # === CLI new ===
    "cli.interactive": {"zh": "互動式介面", "en": "Interactive mode"},
    "cli.members": {"zh": "列出課程成員", "en": "List course members"},
    "cli.message": {"zh": "發送站內訊息", "en": "Send message"},
    "cli.announcements": {"zh": "查看公告", "en": "View announcements"},

    # === Course intro ===
    "course.intro": {"zh": "課程簡介", "en": "Course Intro"},
    "course.no_intro": {"zh": "（無課程簡介）", "en": "(No course intro)"},

    # === Members ===
    "members.title": {"zh": "課程成員", "en": "Course Members"},
    "members.col_name": {"zh": "姓名", "en": "Name"},
    "members.col_email": {"zh": "Email", "en": "Email"},
    "members.col_role": {"zh": "角色", "en": "Role"},
    "members.teacher": {"zh": "教師", "en": "Teacher"},
    "members.student": {"zh": "學生", "en": "Student"},
    "members.total": {"zh": "共 {n} 位成員", "en": "{n} members total"},
    "members.select_msg": {"zh": "輸入編號發送訊息，q 返回", "en": "Enter # to message, q to go back"},
    "members.opt_course": {"zh": "課程名稱（模糊匹配）", "en": "Course name (fuzzy match)"},

    # === Messages ===
    "msg.to": {"zh": "收件人: {name}", "en": "To: {name}"},
    "msg.content_prompt": {"zh": "訊息內容（空行結束）", "en": "Message content (empty line to finish)"},
    "msg.confirm": {"zh": "確認發送？", "en": "Confirm send?"},
    "msg.sent": {"zh": "✓ 訊息已發送", "en": "✓ Message sent"},
    "msg.failed": {"zh": "✗ 發送失敗: {e}", "en": "✗ Send failed: {e}"},
    "msg.cancelled": {"zh": "已取消", "en": "Cancelled"},
    "msg.opt_to": {"zh": "收件人 user ID", "en": "Recipient user ID"},
    "msg.opt_text": {"zh": "訊息內容", "en": "Message text"},

    # === Announcements ===
    "announce.title": {"zh": "公告", "en": "Announcements"},
    "announce.no_forum": {"zh": "找不到公告論壇", "en": "No announcement forum found"},
    "announce.empty": {"zh": "沒有公告", "en": "No announcements"},
    "announce.col_title": {"zh": "標題", "en": "Title"},
    "announce.col_author": {"zh": "發佈者", "en": "Author"},
    "announce.col_date": {"zh": "日期", "en": "Date"},
    "announce.view_detail": {"zh": "輸入編號查看內容，q 返回", "en": "Enter # to view, q to go back"},
    "announce.opt_course": {"zh": "課程名稱（模糊匹配）", "en": "Course name (fuzzy match)"},

    # === Profile ===
    "profile.title": {"zh": "帳號列表", "en": "Profiles"},
    "profile.col_name": {"zh": "名稱", "en": "Name"},
    "profile.col_user": {"zh": "帳號", "en": "Username"},
    "profile.active": {"zh": "目前使用: {name}", "en": "Active: {name}"},
    "profile.switched": {"zh": "✓ 已切換到 {name}", "en": "✓ Switched to {name}"},
    "profile.not_found": {"zh": "找不到 profile: {name}", "en": "Profile not found: {name}"},
    "profile.available": {"zh": "可用的 profiles", "en": "Available profiles"},
    "profile.empty": {"zh": "沒有儲存的帳號。使用 e3cli login --save 登入。", "en": "No profiles. Run e3cli login --save to create one."},
    "profile.confirm_remove": {"zh": "確認刪除 profile {name}？", "en": "Remove profile {name}?"},
    "profile.removed": {"zh": "✓ 已刪除 {name}", "en": "✓ Removed {name}"},
    "profile.select": {"zh": "選擇帳號", "en": "Select profile"},
    "profile.add_new": {"zh": "新增帳號", "en": "Add new profile"},
    "profile.edit": {"zh": "編輯帳號", "en": "Edit profile"},
    "profile.delete": {"zh": "刪除帳號", "en": "Delete profile"},
    "profile.switch": {"zh": "切換到此帳號", "en": "Switch to this profile"},
    "profile.manage": {"zh": "管理帳號: {name}", "en": "Manage profile: {name}"},
    "profile.edit_success": {"zh": "✓ 帳號 {name} 已更新", "en": "✓ Profile {name} updated"},
    "profile.confirm_delete": {"zh": "確定要刪除帳號 {name}？此操作無法復原。", "en": "Delete profile {name}? This cannot be undone."},
    "profile.deleted": {"zh": "✓ 已刪除帳號 {name}", "en": "✓ Profile {name} deleted"},
    "profile.cannot_delete_active": {"zh": "無法刪除目前使用中的帳號，請先切換到其他帳號。", "en": "Cannot delete the active profile. Switch to another profile first."},

    # === Edit submission ===
    "edit.title": {"zh": "編輯提交", "en": "Edit Submission"},
    "edit.current_files": {"zh": "目前已繳交的檔案:", "en": "Currently submitted files:"},
    "edit.no_files": {"zh": "（尚未繳交任何檔案）", "en": "(No files submitted yet)"},
    "edit.action_prompt": {"zh": "r=重新上傳覆蓋, q=返回", "en": "r=re-upload (overwrite), q=go back"},
    "edit.reupload": {"zh": "重新上傳（將覆蓋現有檔案）", "en": "Re-upload (will overwrite existing files)"},
    "edit.success": {"zh": "✓ 已重新提交", "en": "✓ Re-submitted successfully"},
}


def _detect_lang() -> str:
    """偵測語言，優先順序：E3CLI_LANG 環境變數 > config.toml > 系統語言。"""
    # 1. 環境變數最優先
    env_lang = os.environ.get("E3CLI_LANG", "").lower()
    if env_lang in ("en", "zh"):
        return env_lang

    # 2. 讀取 config.toml 裡的 lang 設定
    try:
        from e3cli.config import CONFIG_FILE
        if CONFIG_FILE.exists():
            import tomllib
            with open(CONFIG_FILE, "rb") as f:
                data = tomllib.load(f)
            cfg_lang = data.get("general", {}).get("lang", "").lower()
            if cfg_lang in ("en", "zh"):
                return cfg_lang
    except Exception:
        pass

    # 3. 系統語言
    try:
        sys_lang = locale.getdefaultlocale()[0] or ""
    except Exception:
        sys_lang = ""

    if sys_lang.startswith("zh"):
        return "zh"
    return "en"


_current_lang: str | None = None


def get_lang() -> str:
    global _current_lang
    if _current_lang is None:
        _current_lang = _detect_lang()
    return _current_lang


def set_lang(lang: str) -> None:
    global _current_lang
    _current_lang = lang


def t(key: str, **kwargs) -> str:
    """取得翻譯字串，支援 format 變數。"""
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    lang = get_lang()
    text = entry.get(lang, entry.get("en", key))
    if kwargs:
        text = text.format(**kwargs)
    return text
