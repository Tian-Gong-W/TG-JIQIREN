import os
import shutil
import zipfile
import subprocess
import asyncio
import time
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel

import database
from core.scraper import TelegramScraper
from core.inviter import TelegramInviter
from core.sender import TelegramMassSender, SpintaxParser
from core.cloner import ChannelCloner
from core.interceptor import KeywordInterceptor
from core.account_actions import AccountActionManager
from core.broadcaster import GroupAutoPoster
from core.contacts_stories import ContactsAndStoriesManager

try:
    from telethon import TelegramClient
    import socks
    from opentele.td import TDesktop
    from opentele.api import UseCurrentSession
except ImportError:
    pass

app = FastAPI(title="Telegram 一体化自动化运营控制台")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_DIR = os.path.join(BASE_DIR, "accounts")
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

for d in [ACCOUNTS_DIR, SESSIONS_DIR, EXPORTS_DIR, UPLOADS_DIR]:
    os.makedirs(d, exist_ok=True)

DEFAULT_API_ID = 2040
DEFAULT_API_HASH = "b18441a1ff607e10a989891a5462e627"

# 全局任务与监听器状态
ACTIVE_INTERCEPTOR = None
ACTIVE_POSTER = None

# ================================
# 辅助函数：获取客户端实例
# ================================
def get_client_for_account(acc_name: str) -> TelegramClient:
    acc_path = os.path.join(ACCOUNTS_DIR, acc_name)
    proxy_params = None
    proxy_file = os.path.join(acc_path, "proxy.txt")
    if os.path.exists(proxy_file):
        with open(proxy_file, "r", encoding="utf-8") as f:
            p_str = f.read().strip()
            if p_str:
                p_clean = p_str.replace("socks5://", "").replace("http://", "")
                parts = p_clean.split(":")
                if len(parts) >= 2:
                    proxy_params = (socks.SOCKS5, parts[0], int(parts[1]))

    spath = os.path.join(SESSIONS_DIR, acc_name)
    return TelegramClient(spath, DEFAULT_API_ID, DEFAULT_API_HASH, proxy=proxy_params)

async def get_all_active_clients() -> List[TelegramClient]:
    clients = []
    if not os.path.exists(ACCOUNTS_DIR):
        return clients

    for acc_name in os.listdir(ACCOUNTS_DIR):
        acc_path = os.path.join(ACCOUNTS_DIR, acc_name)
        if os.path.isdir(acc_path):
            try:
                c = get_client_for_account(acc_name)
                await c.start()
                clients.append(c)
            except Exception as e:
                print(f"[!] 启动账号 [{acc_name}] 失败: {e}")
    return clients

# ================================
# 1. 仪表盘统计 API
# ================================
@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    db_stats = database.get_database_stats()
    
    # 计算账号总数
    acc_count = len([d for d in os.listdir(ACCOUNTS_DIR) if os.path.isdir(os.path.join(ACCOUNTS_DIR, d))]) if os.path.exists(ACCOUNTS_DIR) else 0
    
    # 计算截获商机数
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM intercepted_leads;")
    leads_count = cursor.fetchone()[0]
    conn.close()

    return {
        "accounts_count": acc_count,
        "total_users": db_stats["total_users"],
        "active_chatters": db_stats["active_chatters"],
        "premium_users": db_stats["premium_users"],
        "intercepted_leads": leads_count,
        "sources_count": db_stats["sources_count"]
    }

# ================================
# 2. 账号资产与管理 API
# ================================
@app.get("/api/accounts")
async def list_accounts():
    accounts = []
    if not os.path.exists(ACCOUNTS_DIR):
        return accounts

    for name in os.listdir(ACCOUNTS_DIR):
        acc_path = os.path.join(ACCOUNTS_DIR, name)
        if os.path.isdir(acc_path):
            tdata_path = os.path.join(acc_path, "tdata")
            has_tdata = os.path.exists(tdata_path)
            
            proxy_file = os.path.join(acc_path, "proxy.txt")
            proxy_info = ""
            if os.path.exists(proxy_file):
                with open(proxy_file, "r", encoding="utf-8") as f:
                    proxy_info = f.read().strip()

            accounts.append({
                "name": name,
                "has_tdata": has_tdata,
                "proxy": proxy_info or "未绑定代理"
            })
    return accounts

@app.post("/api/accounts/import")
async def import_account(
    file: UploadFile = File(...),
    account_name: str = Form(...),
    proxy: Optional[str] = Form(None)
):
    target_folder = os.path.join(ACCOUNTS_DIR, account_name)
    if os.path.exists(target_folder):
        raise HTTPException(status_code=400, detail="该账号名称已存在，请换一个名称")

    os.makedirs(target_folder, exist_ok=True)
    temp_file = os.path.join(target_folder, file.filename)

    with open(temp_file, "wb") as f:
        content = await file.read()
        f.write(content)

    if file.filename.endswith(".zip"):
        with zipfile.ZipFile(temp_file, 'r') as zip_ref:
            zip_ref.extractall(target_folder)
        os.remove(temp_file)

        inner_tdata = os.path.join(target_folder, "tdata")
        if not os.path.exists(inner_tdata):
            if os.path.exists(os.path.join(target_folder, "key_datas")):
                temp_tdata = os.path.join(target_folder, "_tdata")
                os.makedirs(temp_tdata, exist_ok=True)
                for item in os.listdir(target_folder):
                    if item != "_tdata":
                        shutil.move(os.path.join(target_folder, item), os.path.join(temp_tdata, item))
                os.rename(temp_tdata, inner_tdata)

    if proxy:
        with open(os.path.join(target_folder, "proxy.txt"), "w", encoding="utf-8") as f:
            f.write(proxy.strip())

    return {"status": "success", "message": f"账号 [{account_name}] 导入就绪"}

@app.post("/api/accounts/launch-desktop")
async def launch_desktop(account_name: str = Form(...), portable_exe_path: str = Form(...)):
    acc_path = os.path.join(ACCOUNTS_DIR, account_name)
    tdata_path = os.path.join(acc_path, "tdata")
    if not os.path.exists(tdata_path):
        raise HTTPException(status_code=404, detail="未找到该账号的 tdata 文件夹")
    if not os.path.exists(portable_exe_path):
        raise HTTPException(status_code=400, detail="指定的 Telegram.exe 便携版路径不存在")

    sandbox_exe = os.path.join(acc_path, "Telegram.exe")
    if not os.path.exists(sandbox_exe):
        shutil.copy2(portable_exe_path, sandbox_exe)

    try:
        subprocess.Popen([sandbox_exe, "-workdir", acc_path], cwd=acc_path)
        return {"status": "success", "message": f"已在独立沙箱中唤起账号 [{account_name}]"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")

@app.post("/api/accounts/get-code")
async def get_login_code(account_name: str = Form(...)):
    acc_path = os.path.join(ACCOUNTS_DIR, account_name)
    tdata_path = os.path.join(acc_path, "tdata")
    if not os.path.exists(tdata_path):
        raise HTTPException(status_code=404, detail="tdata 目录不存在")

    proxy_params = None
    proxy_file = os.path.join(acc_path, "proxy.txt")
    if os.path.exists(proxy_file):
        with open(proxy_file, "r", encoding="utf-8") as f:
            p_str = f.read().strip()
            if p_str:
                p_clean = p_str.replace("socks5://", "").replace("http://", "")
                parts = p_clean.split(":")
                if len(parts) >= 2:
                    proxy_params = (socks.SOCKS5, parts[0], int(parts[1]))

    try:
        tdesk = TDesktop(tdata_path)
        if not tdesk.isLoaded():
            raise HTTPException(status_code=400, detail="无法解析此 tdata 文件")

        session_path = os.path.join(SESSIONS_DIR, account_name)
        client = await tdesk.ToTelethon(session=session_path, flag=UseCurrentSession, proxy=proxy_params)
        await client.connect()

        if not await client.is_user_authorized():
            await client.disconnect()
            return {"status": "unauthorized", "message": "该账号会话已被服务端注销/踢下线"}

        messages = []
        async for message in client.iter_messages(777000, limit=5):
            messages.append({"date": str(message.date), "text": message.text})

        await client.disconnect()
        return {"status": "success", "messages": messages}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/accounts/check-spambot")
async def check_spambot(account_name: str = Form(...)):
    try:
        client = get_client_for_account(account_name)
        await client.start()
        mgr = AccountActionManager(client)
        res = await mgr.check_spambot_status()
        await client.disconnect()
        return res
    except Exception as e:
        return {"status": "error", "detail": f"查询失败: {str(e)}"}

@app.post("/api/accounts/batch-leave")
async def batch_leave_chats(account_name: str = Form(...)):
    try:
        client = get_client_for_account(account_name)
        await client.start()
        mgr = AccountActionManager(client)
        res = await mgr.batch_leave_chats()
        await client.disconnect()
        return {"status": "success", "stats": res}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# ================================
# 3. 受众采集与筛选 API
# ================================
@app.post("/api/scraper/start")
async def start_scraping(
    account_name: str = Form(...),
    target_link: str = Form(...),
    scrape_mode: str = Form(...),  # members, active_chatters, commenters
    limit: int = Form(1000),
    days_lookback: int = Form(7)
):
    try:
        client = get_client_for_account(account_name)
        await client.start()
        scraper = TelegramScraper(client)

        if scrape_mode == "members":
            results = await scraper.scrape_group_members(target_link, limit=limit)
        elif scrape_mode == "active_chatters":
            results = await scraper.scrape_active_chatters(target_link, days_lookback=days_lookback, max_messages=limit*3)
        elif scrape_mode == "commenters":
            results = await scraper.scrape_channel_commenters(target_link, recent_posts_count=30)
        else:
            await client.disconnect()
            raise HTTPException(status_code=400, detail="未知的采集模式")

        await client.disconnect()
        return {"status": "success", "count": len(results), "message": f"成功采集 {len(results)} 位目标受众"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"采集失败: {str(e)}")

@app.get("/api/scraper/users")
async def get_collected_users(
    tag: Optional[str] = None,
    only_active: bool = False,
    limit: int = 500
):
    users = database.query_collected_users(tag=tag, only_active=only_active, limit=limit)
    return users

@app.get("/api/scraper/export-csv")
async def export_csv():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(EXPORTS_DIR, f"telegram_leads_{timestamp}.csv")
    database.export_users_to_csv(filepath)
    return FileResponse(filepath, filename=f"telegram_leads_{timestamp}.csv", media_type="text/csv")

# ================================
# 4. 营销矩阵与拉群/群发 API
# ================================
@app.post("/api/inviter/start")
async def start_inviting(
    target_group: str = Form(...),
    tag_filter: Optional[str] = Form(None),
    max_limit: int = Form(100),
    max_per_account: int = Form(15)
):
    clients = await get_all_active_clients()
    if not clients:
        raise HTTPException(status_code=400, detail="当前没有任何已就绪的工作账号")

    users = database.query_collected_users(tag=tag_filter or None, only_active=True, limit=max_limit)
    if not users:
        raise HTTPException(status_code=400, detail="数据库中没有符合条件的受众数据，请先采集！")

    inviter = TelegramInviter(clients, min_delay=20, max_delay=45, max_per_account=max_per_account)
    stats = await inviter.execute_batch_invite(target_group, users)

    for c in clients:
        await c.disconnect()

    return {"status": "success", "stats": stats}

@app.post("/api/sender/preview-spintax")
async def preview_spintax(template: str = Form(...)):
    mock_user = {"first_name": "张总", "username": "zhang_vip"}
    variants = [SpintaxParser.parse(template, mock_user) for _ in range(5)]
    return {"variants": variants}

@app.post("/api/sender/start-dm")
async def start_mass_dm(
    template: str = Form(...),
    tag_filter: Optional[str] = Form(None),
    max_limit: int = Form(50),
    max_per_account: int = Form(20)
):
    clients = await get_all_active_clients()
    if not clients:
        raise HTTPException(status_code=400, detail="没有可用的工作账号")

    users = database.query_collected_users(tag=tag_filter or None, limit=max_limit)
    if not users:
        raise HTTPException(status_code=400, detail="受众数据池为空，请先采集受众")

    sender = TelegramMassSender(clients, min_delay=20, max_delay=40, max_per_account=max_per_account)
    stats = await sender.send_mass_dm(users, template)

    for c in clients:
        await c.disconnect()

    return {"status": "success", "stats": stats}

# ================================
# 5. PRO 高级工具 API
# ================================
@app.post("/api/pro/clone-channel")
async def clone_channel(
    account_name: str = Form(...),
    source_channel: str = Form(...),
    target_channel: str = Form(...),
    limit: int = Form(200),
    replace_old: Optional[str] = Form(None),
    replace_new: Optional[str] = Form(None)
):
    try:
        client = get_client_for_account(account_name)
        await client.start()
        
        rules = {replace_old: replace_new} if replace_old and replace_new else None
        cloner = ChannelCloner(client, min_delay=3.0, max_delay=7.0)
        stats = await cloner.clone_channel_content(
            source_channel_link=source_channel,
            target_channel_link=target_channel,
            limit=limit,
            replace_rules=rules
        )
        await client.disconnect()
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"克隆失败: {str(e)}")

@app.get("/api/pro/interceptor/leads")
async def get_intercepted_leads(limit: int = 50):
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM intercepted_leads ORDER BY created_at DESC LIMIT ?;", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# 挂载静态网页
app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "static"), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  🚀 Telegram 一体化自动化运营大控制台已就绪")
    print("  👉 请在浏览器中打开: http://127.0.0.1:8000")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000)
