import os
import sys
import asyncio
from typing import List
from telethon import TelegramClient

import database
from core.inviter import TelegramInviter
from core.sender import TelegramMassSender, SpintaxParser

DEFAULT_API_ID = 2040
DEFAULT_API_HASH = "b18441a1ff607e10a989891a5462e627"

async def init_client_pool(session_names: List[str]) -> List[TelegramClient]:
    """初始化并连接账号池"""
    session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")
    os.makedirs(session_dir, exist_ok=True)
    
    clients = []
    for name in session_names:
        spath = os.path.join(session_dir, name)
        c = TelegramClient(spath, DEFAULT_API_ID, DEFAULT_API_HASH)
        await c.start()
        me = await c.get_me()
        print(f"  [+] 账号 [{name}] 连接成功: {me.first_name} (@{me.username or '无用户名'})")
        clients.append(c)
    return clients

async def main():
    print("=" * 60)
    print("  Telegram 营销推广与矩阵执行终端 (Step 2 演示版)")
    print("=" * 60)

    # 1. 导入工作账号
    acc_input = input("请输入参与作业的 Session 账号名称（多个用逗号隔开，默认 default_worker）: ").strip() or "default_worker"
    session_names = [a.strip() for a in acc_input.split(",") if a.strip()]

    print(f"\n[*] 正在登录 {len(session_names)} 个工作账号...")
    clients = await init_client_pool(session_names)

    while True:
        print("\n" + "-" * 40)
        print("请选择营销任务:")
        print(" [1] 多账号矩阵【批量拉人进群】(自动轮询 + 熔断换号)")
        print(" [2] 多账号【Spintax 私信群发】(智能话术混淆 + 防风控)")
        print(" [3] 测试 Spintax 话术生成效果")
        print(" [4] 查看当前本地受众池数据")
        print(" [0] 退出")
        print("-" * 40)

        choice = input("请输入选项编号 (0-4): ").strip()

        if choice == "0":
            break

        elif choice == "1":
            target_group = input("请输入您要拉入的目标群组链接 (如 t.me/my_group): ").strip()
            if not target_group:
                continue

            tag_filter = input("按标签筛选受众 (直接回车表示全部，或输入 active_chatter 仅拉活跃者): ").strip()
            max_limit = int(input("本次拉取最大目标数 (默认 100): ").strip() or 100)
            max_per_acc = int(input("每个账号单轮最大拉人数 (默认 15): ").strip() or 15)

            users = database.query_collected_users(tag=tag_filter or None, only_active=True, limit=max_limit)
            if not users:
                print("❌ 数据库中没有符合条件的受众数据，请先运行 run_scraper.py 进行采集！")
                continue

            inviter = TelegramInviter(clients, min_delay=20, max_delay=45, max_per_account=max_per_acc)
            await inviter.execute_batch_invite(target_group, users)

        elif choice == "2":
            print("\n请输入群发话术模板 (支持 Spintax 语法，如 {您好|Hi} {name}...)")
            template = input("话术模板: ").strip()
            if not template:
                print("话术不能为空！")
                continue

            tag_filter = input("按标签筛选受众 (直接回车表示全部，或输入 active_chatter 仅私信活跃者): ").strip()
            max_limit = int(input("本次群发最大目标数 (默认 50): ").strip() or 50)
            max_per_acc = int(input("每个账号单轮最大私信数 (默认 20): ").strip() or 20)

            users = database.query_collected_users(tag=tag_filter or None, limit=max_limit)
            if not users:
                print("❌ 数据库中没有符合条件的受众数据，请先运行 run_scraper.py 进行采集！")
                continue

            sender = TelegramMassSender(clients, min_delay=20, max_delay=40, max_per_account=max_per_acc)
            await sender.send_mass_dm(users, template)

        elif choice == "3":
            sample_template = input("输入测试模板 (默认: {您好|Hi|Hello} {name}，对{项目|业务}感兴趣吗？{random_emoji}): ").strip() or "{您好|Hi|Hello} {name}，对{项目|业务}感兴趣吗？{random_emoji}"
            mock_user = {"first_name": "张总", "username": "zhang_vip"}
            print("\n🎲 随机生成 5 组不同变体展示:")
            for i in range(5):
                out = SpintaxParser.parse(sample_template, mock_user)
                print(f"  变体 {i+1}: {out}")

        elif choice == "4":
            stats = database.get_database_stats()
            print("\n📊 数据库受众统计:")
            for k, v in stats.items():
                print(f"  • {k}: {v}")

    for c in clients:
        await c.disconnect()
    print("\n已退出营销终端。")

if __name__ == "__main__":
    asyncio.run(main())
