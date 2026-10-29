# 全境封锁2 · 每日定向掉落

一个纯静态的掉落查询站：每天北京时间 16:05 自动抓取 prototrack.gg 的数据，
生成 JSON 提交回仓库，Cloudflare Pages 自动重新部署。**没有后端、没有数据库、没有服务器。**

## 它能干什么

- **今日**：5 个恶化任务的定向掉落 + 2 个每日缓存，中文名、阵营、出现次数、上次出现日期、★重点标记
- **历史**：按天翻，看过去每天是什么
- **查询**：输入中文或英文名，看这件东西历史上哪天出现过
- 手机优先，深色/浅色自动跟随系统（右上角可手动切）

## 部署（一次性，约 20 分钟）

### 1. 建仓库

在 GitHub 建一个**公开**仓库，把本目录所有文件推上去：

`bash
git init
git add .
git commit -m "init"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
`

### 2. 打开 Actions

仓库页面 → **Actions** 标签 → 第一次会让你点「I understand my workflows, go ahead and enable them」。
然后可以点 **daily-loot → Run workflow** 手动跑一次，验证能出数据。

### 3. 接 Cloudflare Pages

1. 打开 https://dash.cloudflare.com/ → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
2. 授权 GitHub，选中刚才的仓库
3. 构建设置：**全部留空**
   - Framework preset：None
   - Build command：（留空）
   - Build output directory：/
4. 点 **Save and Deploy**

几十秒后给你一个 xxx.pages.dev 的地址，发群里就能用。

## 日常维护

| 想做的事 | 怎么做 |
|---|---|
| 改某个中文名 | 改 scripts/names.json（格式 {"英文名":"中文名"}），推送，等 Actions 重跑或手动跑一次 |
| 补中文名表 | 改 scripts/names.py 里的字典，带 ※ 的表示译名未确认，界面会标出来 |
| 手动更新一次 | Actions → daily-loot → Run workflow |
| 补抓历史 | 把命令临时改成 python scripts/fetch.py --days 30，或在本地跑 |

## 本地预览

`bash
python -m http.server 8000
:: 浏览器打开 http://127.0.0.1:8000
`

抓数据（仓库里已有数据时不需要）：

`bash
python scripts/fetch.py            # 抓今天
python scripts/fetch.py --days 30  # 补最近 30 天，每天间隔 2 秒
`

## 出问题怎么办

- **页面一直显示昨天**：Actions 挂了。去 Actions 看红色那条，通常是源站临时抽风，第二天会自己恢复。
- **名字显示（待补全）**：源站出了新的品牌/套装，把英文名和中文名加进 scripts/names.json 即可。
- **整站改版解析失败**：fetch.py 解析不出任务会直接报错退出，**不会写入空数据**，线上还是旧数据，不会白屏。
- **想停掉自动更新**：删掉或注释 .github/workflows/daily.yml 里的 schedule。

## 声明

数据来自 prototrack.gg（社区站，只读）。本站是玩家自制的查询工具，
与 Massive Entertainment / Ubisoft 无关，游戏素材版权归原方所有。
