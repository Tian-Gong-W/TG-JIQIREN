import os
import sys
import asyncio
from telethon import TelegramClient

import database
from core.cloner import ChannelCloner
from core.interceptor import KeywordInterceptor

DEFAULT_API_ID = 2040
DEFAULT_API_HASH = "b18441a1ff607e10a989891a5462e627"

async def main():
    print("=" * 60)
    print("  Telegram PRO 高级模块工具集 (Step 3 演示版)")
    print("=" * 60)

    # 1. 登录工作账号
    session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")
    os.makedirs(session_dir, exist_ok=True)
    session_name = input("请输入执行 PRO 任务的 Session 账号名称 (默认: pro_worker): ").strip() or "pro_worker"
    session_path = os.path.join(session_dir, session_name)

    client = TelegramClient(session_path, DEFAULT_API_ID, DEFAULT_API_HASH)
    await client.start()
    me = await client.get_me()
    print(f"\n[+] 账号连接成功: {me.first_name} (@{me.username or '无用户名'}, ID: {me.id})")

    while True:
        print("\n" + "-" * 40)
        print("请选择 PRO 任务:")
        print(" [1] 频道/群组内容【一键克隆搬运】(正序无痕搬运 + 去水印替换)")
        print(" [2] 全天候群组【关键词实时监听与商机拦截】(毫秒级推送至销售群)")
        print(" [3] 查看历史截获的商机线索记录")
        print(" [0] 退出")
        print("-" * 40)

        choice = input("请输入选项编号 (0-3): ").strip()

        if choice == "0":
            break

        elif choice == "1":
            src = input("请输入【源频道】链接或 @username (例如 @source_channel): ").strip()
            dst = input("请输入【目标频道】链接或 @username (需具备发帖权限): ").strip()
            if not src or not dst:
                continue

            limit = int(input("搬运历史消息上限条数 (默认 200): ").strip() or 200)
            start_id = int(input("起始消息 ID (默认从头开始为 0): ").strip() or 0)
            
            replace_old = input("需要替换的旧广告/用户名 (选填，无则直接回车): ").strip()
            replace_new = input("替换为您的新广告/用户名 (选填): ").strip() if replace_old else ""

            rules = {replace_old: replace_new} if replace_old else None

            cloner = ChannelCloner(client, min_delay=3.0, max_delay=7.0)
            await cloner.clone_channel_content(
                source_channel_link=src,
                target_channel_link=dst,
                limit=limit,
                start_from_msg_id=start_id,
                replace_rules=rules
            )

        elif choice == "2":
            kw_input = input("请输入监控的意向关键词（多个用逗号隔开，例如：求购,买,多少钱,需要,找）: ").strip()
            if not kw_input:
                kw_input = "求购,买,多少钱,需要,找,推荐"
            keywords = [k.strip() for k in kw_input.split(",") if k.strip()]

            exclude_input = input("请输入排除干扰词（选填，多个用逗号隔开，如：已出,招聘,广告）: ").strip()
            exclude_words = [e.strip() for e in exclude_input.split(",") if e.strip()] if exclude_input else []

            forward_target = input("请输入商机接收目标 (例如您的客服号 @my_service 或销售群链接): ").strip()

            group_input = input("请输入指定监控的群组（多个逗号隔开，留空则监听该账号加入的所有群）: ").strip()
            monitored_groups = [g.strip() for g in group_input.split(",") if g.strip()] if group_input else None

            interceptor = KeywordInterceptor(
                client=client,
                keywords=keywords,
                exclude_words=exclude_words,
                forward_target_peer=forward_target or None
            )

            try:
                await interceptor.start_listening(target_groups=monitored_groups)
            except (KeyboardInterrupt, SystemExit):
                print("\n[!] 用户手动停止监听。")

        elif choice == "3":
            conn = database.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM intercepted_leads ORDER BY created_at DESC LIMIT 20;")
            leads = cursor.fetchall()
            conn.close()

            if not leads:
                print("\n暂无截获的商机线索记录。")
            else:
                print(f"\n📋 最近截获的 {len(leads)} 条商机线索:")
                for l in leads:
                    print(f"  • [{l['created_at']}] [{l['matched_keyword']}] {l['sender_name']} (@{l['sender_username'] or '无'}): {l['message_text'][:60]}...")

    await client.disconnect()
    print("\n已退出 PRO 工具终端。")

if __name__ == "__main__":
    asyncio.run(main())
