import asyncio
import random
import time
from typing import List, Dict, Optional, Any
from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetDiscussionMessageRequest
from telethon.errors import FloodWaitError, ChatWriteForbiddenError

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.sender import SpintaxParser

class GroupAutoPoster:
    """群聊自动定时广播与推流引擎"""

    def __init__(
        self,
        client: TelegramClient,
        target_groups: List[str],
        spintax_template: str,
        interval_minutes: int = 60,
        min_group_delay: float = 15.0,
        max_group_delay: float = 35.0,
        media_file: Optional[str] = None
    ):
        self.client = client
        self.target_groups = target_groups
        self.spintax_template = spintax_template
        self.interval_minutes = interval_minutes
        self.min_group_delay = min_group_delay
        self.max_group_delay = max_group_delay
        self.media_file = media_file
        self.is_running = False

    async def start_broadcasting(self):
        """启动定时循环广播任务"""
        self.is_running = True
        round_count = 0

        print(f"[*] 启动群聊自动定时推流任务: 目标群组 {len(self.target_groups)} 个 | 循环间隔: {self.interval_minutes} 分钟")

        while self.is_running:
            round_count += 1
            print(f"\n📢 开始第 {round_count} 轮广播推流...")

            for idx, g in enumerate(self.target_groups, start=1):
                if not self.is_running:
                    break

                try:
                    entity = await self.client.get_entity(g)
                    group_title = getattr(entity, 'title', g)
                    
                    # 动态生成 Spintax 消息
                    msg_text = SpintaxParser.parse(self.spintax_template)

                    if self.media_file and os.path.exists(self.media_file):
                        await self.client.send_file(entity, self.media_file, caption=msg_text)
                    else:
                        await self.client.send_message(entity, msg_text)

                    print(f"  [{idx}/{len(self.target_groups)}] ✅ 成功发送至群: {group_title}")

                except ChatWriteForbiddenError:
                    print(f"  [{idx}/{len(self.target_groups)}] 🚫 群组被全员禁言或仅管理员可发帖: {g}")
                except FloodWaitError as e:
                    print(f"  [!] 触发限流，休眠 {e.seconds} 秒...")
                    await asyncio.sleep(e.seconds + 2)
                except Exception as err:
                    print(f"  [{idx}/{len(self.target_groups)}] ❌ 发送失败 ({g}): {err}")

                delay = random.uniform(self.min_group_delay, self.max_group_delay)
                await asyncio.sleep(delay)

            print(f"\n💤 第 {round_count} 轮推流完成，等待 {self.interval_minutes} 分钟后开始下一轮...")
            await asyncio.sleep(self.interval_minutes * 60)


class ChannelAutoCommenter:
    """频道新帖自动抢评与引流评论引擎"""

    def __init__(
        self,
        client: TelegramClient,
        monitored_channels: List[str],
        comment_template: str,
        delay_seconds: float = 3.0
    ):
        self.client = client
        self.monitored_channels = monitored_channels
        self.comment_template = comment_template
        self.delay_seconds = delay_seconds

    async def start_monitoring(self):
        """挂机监听频道新消息并自动在讨论组评论"""
        channel_entities = []
        for ch in self.monitored_channels:
            try:
                ent = await self.client.get_entity(ch)
                channel_entities.append(ent)
                print(f"  ✓ 成功挂载频道新帖监听: {getattr(ent, 'title', ch)}")
            except Exception as e:
                print(f"  ✗ 无法解析频道 ({ch}): {e}")

        if not channel_entities:
            print("❌ 没有有效的监听频道。")
            return

        @self.client.on(events.NewMessage(chats=channel_entities))
        async def new_post_handler(event):
            # 只处理频道广播消息
            if not event.is_channel or event.is_group:
                return

            print(f"\n🔔 捕获到频道发布新帖 (ID: {event.id})，准备自动抢评...")
            if self.delay_seconds > 0:
                await asyncio.sleep(self.delay_seconds)

            try:
                # 动态解析 Spintax 引流评论文案
                comment_text = SpintaxParser.parse(self.comment_template)

                # 获取对应的讨论组消息 ID 并回复
                discussion = await self.client(GetDiscussionMessageRequest(
                    peer=event.peer_id,
                    msg_id=event.id
                ))
                
                # 在讨论组中作为评论回复
                await self.client.send_message(
                    entity=discussion.messages[0].peer_id,
                    message=comment_text,
                    reply_to=discussion.messages[0].id
                )
                print(f"  ✅ 成功在评论区抢发评论: \"{comment_text[:50]}...\"")

            except Exception as err:
                print(f"  ❌ 评论发布失败: {err}")

        print("\n[✓] 频道新帖自动抢评监听已启动 (按 Ctrl+C 停止)...")
        await self.client.run_until_disconnected()
