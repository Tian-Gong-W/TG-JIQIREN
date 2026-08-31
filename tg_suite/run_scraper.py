import os
import sys
import asyncio
from datetime import datetime
from telethon import TelegramClient

import database
from core.scraper import TelegramScraper

# 默认官方客户端 API ID 与 Hash (可替换为您自己的)
DEFAULT_API_ID = 2040
DEFAULT_API_HASH = "b18441a1ff607e10a989891a5462e627"

async def main():
    print("=" * 60)
    print("  Telegram 智能受众采集与数据筛选终端 (Step 1 演示版)")
    print("=" * 60)

    # 1. 账号会话配置
    session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")
    os.makedirs(session_dir, exist_ok=True)
    session_name = input("请输入用于采集的 Session 账号名称 (默认: default_scraper): ").strip() or "default_scraper"
    session_path = os.path.join(session_dir, session_name)

    client = TelegramClient(session_path, DEFAULT_API_ID, DEFAULT_API_HASH)
    await client.start()
    
    me = await client.get_me()
    print(f"\n[+] 账号连接成功! 当前登录账号: {me.first_name} (@{me.username or '无用户名'}, ID: {me.id})")

    scraper = TelegramScraper(client)

    while True:
        print("\n" + "-" * 40)
        print("请选择采集模式:")
        print(" [1] 采集全量群成员 (可过滤机器人)")
        print(" [2] 采集【近期发言活跃者】(极高价值，过滤死号)")
        print(" [3] 采集【频道评论区互动者】")
        print(" [4] 查看当前数据库统计与受众池")
        print(" [5] 导出当前受众数据为 CSV 文件")
        print(" [0] 退出")
        print("-" * 40)
        
        choice = input("请输入选项编号 (0-5): ").strip()
        
        if choice == "0":
            break

        elif choice == "1":
            target = input("请输入目标群组链接或 @username: ").strip()
            if not target:
                continue
            limit = int(input("请输入最大采集人数 (默认 1000): ").strip() or 1000)
            try:
                users = await scraper.scrape_group_members(target, limit=limit)
                print(f"✅ 采集完成，成功获取 {len(users)} 名群成员数据并写入本地数据库。")
            except Exception as e:
                print(f"❌ 采集出错: {e}")

        elif choice == "2":
            target = input("请输入目标群组链接或 @username: ").strip()
            if not target:
                continue
            days = int(input("请输入回溯天数 (默认 7 天): ").strip() or 7)
            try:
                chatters = await scraper.scrape_active_chatters(target, days_lookback=days)
                print(f"✅ 采集完成，成功获取 {len(chatters)} 位过去 {days} 天内真实发言的高价值活跃用户！")
            except Exception as e:
                print(f"❌ 采集出错: {e}")

        elif choice == "3":
            target = input("请输入目标公开频道链接或 @username: ").strip()
            if not target:
                continue
            try:
                commenters = await scraper.scrape_channel_commenters(target)
                print(f"✅ 采集完成，成功从讨论组获取 {len(commenters)} 位互动评论用户。")
            except Exception as e:
                print(f"❌ 采集出错: {e}")

        elif choice == "4":
            stats = database.get_database_stats()
            print("\n📊 数据库受众池统计:")
            print(f"  • 总用户数: {stats['total_users']}")
            print(f"  • 拥有 @username: {stats['with_username']}")
            print(f"  • 活跃发言者: {stats['active_chatters']}")
            print(f"  • Telegram Premium 会员: {stats['premium_users']}")
            print(f"  • 覆盖群组/频道来源: {stats['sources_count']}")

        elif choice == "5":
            exports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
            os.makedirs(exports_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(exports_dir, f"telegram_leads_{timestamp}.csv")
            
            database.export_users_to_csv(filename)
            print(f"✅ 导出成功！文件已保存至: {filename}")

    await client.disconnect()
    print("\n已安全退出。")

if __name__ == "__main__":
    asyncio.run(main())
