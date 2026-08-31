import os
import sys
import asyncio
from telethon import TelegramClient

from core.account_actions import AccountActionManager
from core.broadcaster import GroupAutoPoster, ChannelAutoCommenter
from core.contacts_stories import ContactsAndStoriesManager

DEFAULT_API_ID = 2040
DEFAULT_API_HASH = "b18441a1ff607e10a989891a5462e627"

async def main():
    print("=" * 60)
    print("  Telegram 运维增强与群聊广播终端 (Operations Runner)")
    print("=" * 60)

    # 1. 登录工作账号
    session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")
    os.makedirs(session_dir, exist_ok=True)
    session_name = input("请输入执行操作的 Session 账号名称 (默认: op_worker): ").strip() or "op_worker"
    session_path = os.path.join(session_dir, session_name)

    client = TelegramClient(session_path, DEFAULT_API_ID, DEFAULT_API_HASH)
    await client.start()
    me = await client.get_me()
    print(f"\n[+] 账号连接成功: {me.first_name} (@{me.username or '无用户名'}, ID: {me.id})")

    action_mgr = AccountActionManager(client)
    contact_story_mgr = ContactsAndStoriesManager(client)

    while True:
        print("\n" + "-" * 40)
        print("请选择运维/广播任务:")
        print(" [1] 批量【退出无用群组与频道】(释放 500 个上限配额)")
        print(" [2] @SpamBot【账号风控状态与解封时间检测】")
        print(" [3] 群聊【自动定时循环推流广播】")
        print(" [4] 频道新帖【自动抢评与引流评论】")
        print(" [5] 通讯录【批量清空当前全部联系人】")
        print(" [6] 动态故事【发布 24 小时公开 Stories】")
        print(" [0] 退出")
        print("-" * 40)

        choice = input("请输入选项编号 (0-6): ").strip()

        if choice == "0":
            break

        elif choice == "1":
            confirm = input("⚠️ 确认退出当前账号加入的非自建群组/频道？(y/n): ").strip().lower()
            if confirm == 'y':
                await action_mgr.batch_leave_chats()

        elif choice == "2":
            res = await action_mgr.check_spambot_status()
            print(f"📊 检测结果: {res['detail']}")

        elif choice == "3":
            groups_input = input("请输入待广播的群组（多个逗号隔开，如 @grp1,@grp2）: ").strip()
            if not groups_input:
                continue
            groups = [g.strip() for g in groups_input.split(",") if g.strip()]

            template = input("请输入广播话术 (支持 Spintax，如 {您好|Hi} 提供{项目|服务}...): ").strip()
            if not template:
                continue

            interval = int(input("循环广播间隔时间 (单位: 分钟，默认 60): ").strip() or 60)
            media = input("可选图片/海报文件路径 (选填，直接回车不带图): ").strip()

            poster = GroupAutoPoster(
                client=client,
                target_groups=groups,
                spintax_template=template,
                interval_minutes=interval,
                media_file=media or None
            )
            try:
                await poster.start_broadcasting()
            except (KeyboardInterrupt, SystemExit):
                print("\n[!] 广播已手动停止。")

        elif choice == "4":
            channels_input = input("请输入监控的频道（多个逗号隔开，如 @chan1,@chan2）: ").strip()
            if not channels_input:
                continue
            channels = [c.strip() for c in channels_input.split(",") if c.strip()]

            comment_text = input("请输入自动抢评话术 (支持 Spintax 模板): ").strip()
            if not comment_text:
                continue

            commenter = ChannelAutoCommenter(client, channels, comment_text)
            try:
                await commenter.start_monitoring()
            except (KeyboardInterrupt, SystemExit):
                print("\n[!] 抢评监听已手动停止。")

        elif choice == "5":
            confirm = input("⚠️ 确认清空当前账号的全部联系人？(y/n): ").strip().lower()
            if confirm == 'y':
                await contact_story_mgr.clear_all_contacts()

        elif choice == "6":
            media_path = input("请输入要发布为故事的图片/视频路径: ").strip()
            if not media_path:
                continue
            caption = input("故事文案/描述 (选填): ").strip()
            await contact_story_mgr.publish_story(media_path, caption=caption)

    await client.disconnect()
    print("\n已退出运维终端。")

if __name__ == "__main__":
    asyncio.run(main())
