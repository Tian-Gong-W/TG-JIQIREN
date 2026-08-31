# Telegram 自动化全功能运营套件 (Complete Suite)

本项目是基于 Python 异步架构（Telethon / MTProto）构建的一站式 Telegram 自动化运营与营销套件。

## 完整工程目录结构
```text
tg_suite/
├── requirements.txt         # 依赖环境清单
├── database.py              # SQLite 数据库模型与受众/商机治理中枢
│
├── run_scraper.py           # 【模块 1】高精度受众采集与数据清洗交互终端
├── run_marketing.py         # 【模块 2】多账号矩阵轮换拉群与 Spintax 群发终端
├── run_pro_tools.py         # 【模块 3】PRO 工具（频道克隆 + 关键词商机实时拦截）
├── run_operations.py        # 【模块 4】日常运维（批量退群 + @SpamBot 查风控 + 群聊定时广播 + 抢评 + Stories）
│
├── core/
│   ├── scraper.py           # 群成员/发言活跃者/讨论组评论区采集引擎
│   ├── inviter.py           # 矩阵交叉轮询拉群引擎 (含熔断换号机制)
│   ├── sender.py            # Spintax 语法解析与多账号私信/自动应答引擎
│   ├── cloner.py            # 频道正序克隆搬运与水印清洗引擎
│   ├── interceptor.py       # 全网群组关键词实时监听与商机转发引擎
│   ├── account_actions.py   # 批量退群/退频道与 @SpamBot 自动风控查询
│   ├── broadcaster.py       # 群聊定时循环广播 (Auto-Poster) 与频道新帖自动抢评
│   └── contacts_stories.py  # 通讯录批量导入/清空与 Stories 动态故事发布
│
├── sessions/                # 账号会话文件存储目录
└── exports/                 # 采集结果 CSV 导出目录
```

## 四大核心交互终端运行指南

### 1. 数据采集与清洗终端 (`python run_scraper.py`)
* **全量群成员采集**：自动过滤机器人与注销账号。
* **活跃发言者提取（核心功能）**：回溯群内最近 N 天历史聊天记录，精准提取发过言的真实活跃客户，记录发言频次与最新消息摘要。
* **频道评论区抓取**：自动定位频道绑定的讨论组，提取在帖子下留言互动的用户。

### 2. 营销矩阵与多号轮换终端 (`python run_marketing.py`)
* **矩阵交叉轮询拉群**：多账号交替拉人进群，单号达到阈值（如 15 人）自动休眠并切换下一账号，彻底杜绝单号封禁。
* **Spintax 智能私信群发**：支持 `{您好|Hi|Hello}` 嵌套语法与 `{name}`、`{username}`、`{random_emoji}` 动态变量替换。

### 3. PRO 高级工具终端 (`python run_pro_tools.py`)
* **频道内容一键克隆**：正序完整搬运目标频道的历史图文、音视频与文件，无痕重发并正则替换原频道广告。
* **全天候关键词监听与商机拦截**：后台挂机监听数百个行业大群，命中求购、咨询关键词后毫秒级推送到您的销售群。

### 4. 日常运维与群聊广播终端 (`python run_operations.py`)
* **批量退群/退订频道**：一键退出非自建的无用群组，释放账号 500 个加群上限配额。
* **@SpamBot 风控状态检测**：自动向官方机器人发送查询，获取账号当前的限制状态与解封时间。
* **群聊自动定时循环广播**：按设定的时间周期（如每 60 分钟），自动向指定群聊列表轮播 Spintax 推广文案。
* **频道新帖抢评**：监听目标频道发布新帖，毫秒级在关联讨论组抢发第一条引流评论。
* **通讯录与 Stories 故事**：批量清空/导入联系人，自动发布 24 小时动态故事。

## API 认证与授权配置

控制台默认要求所有 `/api/*` 请求携带 Bearer API Key。系统支持两个角色：`TG_ADMIN_API_KEY` 可访问全部接口，`TG_OPERATOR_API_KEY` 仅可访问统计、账号列表、受众查询/导出、Spintax 预览和线索查看等低风险接口。账号导入、读取验证码、桌面端启动、批量退群、采集任务、拉群、私信和频道克隆均需要管理员密钥。

生产环境必须设置 `TG_ENV=production`、`TG_ADMIN_API_KEY`、`TG_API_ID` 和 `TG_API_HASH`。建议使用密码管理器或部署平台的 Secret 注入机制生成随机密钥，例如：

```bash
export TG_ENV=production
export TG_ADMIN_API_KEY="$(openssl rand -hex 32)"
export TG_OPERATOR_API_KEY="$(openssl rand -hex 32)"
export TG_API_ID="你的 Telegram API ID"
export TG_API_HASH="你的 Telegram API Hash"
python server.py
```

只有在隔离的本机开发环境中，才可以显式设置 `TG_AUTH_DISABLED=true` 旁路认证；该配置在 `TG_ENV=production` 时会被拒绝。前端首次调用 API 时会在当前浏览器会话中提示输入 API Key，并保存在 `sessionStorage`，关闭浏览器后自动清除。

不要把真实 API Key、Telegram session、TData、代理密码、数据库或 `.env` 文件提交到 Git。项目已通过 `.gitignore` 排除常见运行时和敏感文件。

## 快速使用说明

### 1. 安装依赖环境
```bash
pip install -r requirements.txt
```

### 2. 运行对应功能
根据您的任务目标直接运行对应的终端脚本即可。
