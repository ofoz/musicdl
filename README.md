<div align="center">

<img src="docs/logo.png" width="520" alt="musicdl · SoundFlow" />

# musicdl · SoundFlow

**多源并发搜索 · 在线即点即播 · 同步滚动歌词 · 歌单与收藏管理的本地音乐工作台**

一个开箱即用的本地 Web 音乐工作台：后端是 Flask，前端是零构建的原生 JS（Tailwind CDN），
`pip install` 后一条命令即可在浏览器里搜歌、试听、下载、整理歌单。

[![License](https://img.shields.io/badge/license-PolyForm--Noncommercial--1.0.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/backend-Flask-000000.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED.svg?logo=docker&logoColor=white)](docker-compose.yml)
[![WebUI](https://img.shields.io/badge/WebUI-zero--build-brightgreen.svg)](#-快速开始)

<a href="#-快速开始">快速开始</a> ·
<a href="#-功能特性">功能特性</a> ·
<a href="#-支持的音源">支持的音源</a> ·
<a href="#-http-api">HTTP API</a> ·
<a href="#-生产部署">生产部署</a>

</div>

---

> **关于本仓库**
> 本项目基于 [CharlesPikachu/musicdl](https://github.com/CharlesPikachu/musicdl) 二次开发。
> 上游提供了纯 Python 的抓取内核与 50+ 平台客户端；本分支在此之上重写了 WebUI（`musicdl/web/`），
> 并围绕「浏览器里直接听歌」重构了搜索、播放、歌单、收藏与下载的完整链路。
> 音源解析能力与版权归属仍属于上游，使用前请务必阅读 [免责声明](#-免责声明)。

## 📖 项目简介

三种使用形态，共用同一套音源内核：

| 形态 | 入口 | 适用场景 |
| :-- | :-- | :-- |
| **WebUI（推荐）** | `musicdl-web` / `python -m musicdl.web` | 浏览器内搜索、试听、拖进度、看歌词、管歌单 |
| 命令行 | `musicdl -m NeteaseMusicClient,QQMusicClient` | 终端交互式搜索与批量下载 |
| Python API | `from musicdl import musicdl` | 二次开发、数据采集、自动化脚本 |

WebUI 的前端只有三个静态文件（`index.html` / `style.css` / `app.js`），
没有 Node、没有打包步骤，改完刷新即生效。

## ✨ 功能特性

| 能力 | 说明 |
| :-- | :-- |
| **多源并发流式搜索** | 基于 SSE（Server-Sent Events）+ 线程池并发请求各音源，结果**逐源即时推送**，不必等待最慢的平台 |
| **在线即点即播** | 内置音频反向代理（`/api/stream/<token>`），统一处理防盗链（Referer / UA）与 CORS；支持 HTTP 206 Range，可任意拖动进度条 |
| **直链自愈** | 平台直链会过期，播放前按需重新解析（`/api/track/resolve`），并**坚持原平台身份**，不会把 QQ 歌单的曲目悄悄换成别的平台 |
| **同步滚动歌词** | LRC 逐行解析，当前行高亮 + 平滑居中滚动，上下渐隐遮罩，视口精准聚焦 5~6 行 |
| **歌单解析与托管** | 粘贴网易云 / QQ 歌单链接批量解析，库内原地重命名、立即播放、折叠查看，数据持久化在浏览器本地 |
| **收藏与「我的私藏」** | 列表行内一键收藏；右键（触屏长按 550ms）可收藏到指定歌单或新建歌单；默认落入「我的私藏」 |
| **跨设备二维码同步** | 前端用 `qrcode` 生成、`jsQR` 扫码，全离线无外部依赖；自动判断局域网 IP 或域名，手机扫码即合并双端歌单与偏好 |
| **下载与元数据补全** | 优先抓最高音质（无损 FLAC / 320k MP3），可转码目标格式；自动内嵌封面与 ID3v2 歌词；文件名按 RFC 5987/6266 编码，中文不乱码。**本仓库默认关闭**，需 `MUSICDL_ALLOW_DOWNLOAD=1` 启用 |
| **沉浸式播放器** | 桌面端单行同轴播放栏 + 全屏播放器（歌词 / 封面 / 音量竖排弹层），移动端纵向堆叠，播放键始终居中 |
| **明暗双主题** | `html.dark` 全量覆盖 + 首屏内联脚本防闪白，偏好写入 `localStorage` |
| **封面兜底** | 取不到封面时返回内置渐变 SVG，深/浅色下都可见，不留破图 |

## 🎧 支持的音源

WebUI 内置 12 个音源，可在页面内按「国内主流 / 聚合平台 / 海外与独立」分组勾选，默认激活 6 个：

| 分组 | 音源 | 客户端 | 默认 |
| :-- | :-- | :-- | :--: |
| 国内主流 | 网易云音乐 | `NeteaseMusicClient` | ✅ |
| 国内主流 | QQ 音乐 | `QQMusicClient` | ✅ |
| 国内主流 | 酷我音乐 | `KuwoMusicClient` | ✅ |
| 国内主流 | 酷狗音乐 | `KugouMusicClient` | ✅ |
| 国内主流 | 咪咕音乐 | `MiguMusicClient` | ✅ |
| 国内主流 | 波点音乐 | `BodianMusicClient` | ✅ |
| 国内主流 | 汽水音乐 | `SodaMusicClient` | — |
| 聚合平台 | MyFreeMP3 | `MyFreeMP3MusicClient` | — |
| 聚合平台 | 歌曲宝 | `GequbaoMusicClient` | — |
| 聚合平台 | GDStudio 聚合 | `GDStudioMusicClient` | — |
| 海外与独立 | Jamendo | `JamendoMusicClient` | — |
| 海外与独立 | SoundCloud | `SoundCloudMusicClient` | — |

> 搜索策略：**每个音源取 5 条**，单源 25 秒超时，先到的先展示。
> 命令行 / Python 侧沿用上游全部客户端（Apple Music、Spotify、TIDAL、Qobuz、YouTube Music、
> 喜马拉雅、蜻蜓 FM 等，注册表当前 57 个），完整清单见 [`musicdl/modules/`](musicdl/modules) 与[上游文档](https://musicdl.readthedocs.io/)。

## 🚀 快速开始

### 方式一：Docker Compose（推荐）

```bash
git clone https://github.com/ofoz/musicdl.git
cd musicdl
docker compose up -d --build     # 首次构建需拉取依赖，视网络情况约数分钟
docker compose ps                # 健康检查通过后即为 running (healthy)
```

打开 <http://127.0.0.1:5050> 即可。容器默认：

- 端口**只绑定宿主机 `127.0.0.1:5050`**，不直接暴露公网（需要外网访问请改端口映射或走反代）；
- 下载与缓存持久化到宿主机 `./downloads`；
- **前端静态资源挂载自宿主机 `./musicdl/web/static`**（只读），改动页面后 `git pull` 刷新即生效，无需重建镜像；后端 Python 改动仍需 rebuilt（见[更新版本](#4-更新版本)）；
- 镜像基于 `python:3.11-slim`，音频转码走 PyAV（自带 FFmpeg 库）；若要使用 Apple Music / TIDAL 等依赖外部命令的音源，需自行在镜像内补装 `ffmpeg` 等工具（见[上游安装文档](https://musicdl.readthedocs.io/)）；
- 时区 `Asia/Shanghai`，并自带 `HEALTHCHECK`（30 秒巡检一次首页）。

### 方式二：本地 Python 运行

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .

musicdl-web                        # 等价于 python -m musicdl.web
```

不想装包也可以直接跑：

```bash
python -m musicdl.web --host 127.0.0.1 --port 5050 --work-dir ./my_music --no-browser
```

### 启动参数

| 参数 | 默认值 | 说明 |
| :-- | :-- | :-- |
| `--host` | `127.0.0.1` | 监听地址。设为 `0.0.0.0` 可让手机 / 局域网访问（二维码同步需要） |
| `--port` | `5050` | 监听端口 |
| `--work-dir` | `./musicdl_web_downloads` | 下载与缓存目录，等价于环境变量 `MUSICDL_DOWNLOAD_DIR` |
| `--no-browser` | 关闭 | 禁止启动后自动打开系统浏览器 |

其他环境变量：`MUSICDL_DIRECT_URL_TTL`（默认 `900` 秒）——平台直链的有效期判定，过期即触发重新解析。

`MUSICDL_ALLOW_DOWNLOAD`（默认 `0`，即**关闭**）：下载总开关。关闭时页面不提供任何下载入口，服务端同时拒绝 `?download=1`、`?embed_lyric=1`、指定转码格式以及 `/api/download/local`——这几种请求都会让服务器逐字节中转音频、甚至整首进内存转码，等于把自己当免费下载器。关闭后仅放行「302 直达 CDN」的纯播放请求，服务端不承担音频带宽。

> 这只是限制本站不去做转码与中转，不是内容加密：浏览器只要在播放，音频就一定到过客户端，抓包或直接录流仍可获取。

## 🧭 使用指南

1. **搜索**：顶部输入歌名 / 歌手 / 专辑，按 <kbd>Enter</kbd>。搜索按钮会实时反映全局状态（检索中 → 已找到 N 首 → 搜索完成）。
2. **筛选音源**：搜索框下方切换音源胶囊，勾选即时生效，下次搜索沿用。
3. **播放**：点击行内 ▶ 试听。播放栏进度条可拖动、键盘 <kbd>←</kbd>/<kbd>→</kbd> 微调，<kbd>Space</kbd> 播放 / 暂停；点喇叭向上弹出竖排音量滑杆。
4. **歌词与全屏**：点播放栏的曲目信息或右侧展开按钮进入全屏播放器，歌词随播放逐行高亮、平滑居中；<kbd>Esc</kbd> 退出。
5. **下载（默认关闭）**：本仓库把 `MUSICDL_ALLOW_DOWNLOAD` 默认设为 `0`，页面不出现任何下载入口，顶部「格式」按钮也隐藏。开启后行内 ⤓ 可打开下载弹窗，选「原始音质 / MP3 / FLAC / WAV / M4A」，音频经代理直下（已内嵌封面与歌词），PC 端额外另存 `.lrc`。
6. **歌单**：顶部「我的歌单」→ 粘贴歌单链接导入；空态页的胶囊按钮可直接跳到该入口。
7. **收藏**：行内 ♡ 单击收藏（默认「我的私藏」），右键 / 长按选择其他歌单或新建。
8. **跨设备同步**：点顶部「二维码导出」生成同步码（自动识别局域网 IP 或域名），手机扫码后自动合并歌单与偏好。
9. **回到主页**：点左上角 Logo 一键关闭全屏、歌词与各类弹窗并复位，不打断正在播放的歌曲。
10. **主题**：Logo 旁的月亮 / 太阳按钮切换明暗，偏好本地持久化。

## 🏗️ 项目结构

```text
musicdl/
├── musicdl/
│   ├── musicdl.py            # 命令行 / Python API 入口（MusicClient）
│   ├── modules/
│   │   ├── sources/          # 各平台音源客户端 + 客户端注册表
│   │   ├── audiobooks/       # 有声书 / 播客（喜马拉雅、蜻蜓 FM…）
│   │   ├── common/           # 聚合站（GDStudio、TuneHub、MyFreeMP3…）
│   │   ├── thirdpartysites/  # 第三方下载站适配
│   │   └── utils/            # 请求、加解密、元数据等工具
│   └── web/
│       ├── server.py         # Flask：SSE 搜索 / Range 代理 / 歌单 / 收藏 / 同步 / 下载
│       ├── __init__.py       # musicdl-web 入口与参数解析
│       └── static/
│           ├── index.html    # 单页骨架（Tailwind CDN）
│           ├── style.css     # 主题、播放器、进度条、音量等定制样式
│           ├── app.js        # 全部交互逻辑与状态管理
│           └── libs/         # qrcode.min.js · jsQR.min.js（离线）
├── tests/                    # 端到端与回归脚本（见下）
├── docs/                     # 上游文档、截图与徽标
├── Dockerfile
└── docker-compose.yml
```

## 🔌 HTTP API

WebUI 与后端之间只通过下面这组接口交互，也可以直接拿来写脚本：

| 方法 | 路径 | 说明 |
| :-- | :-- | :-- |
| `GET` | `/` | WebUI 单页 |
| `GET` | `/api/sources` | 音源清单（id / 中文名 / 分组 / 是否默认） |
| `GET` | `/api/search/stream?q=&sources=` | **SSE** 流式搜索，事件为 `source_start` / `result` / `source_done` / `source_error` |
| `GET` | `/api/stream/<token>` | 音频代理：纯播放时 **302 直达 CDN**（不占本站带宽）；`?download=1`、`?embed_lyric=1`、`?format=xxx` 会触发服务端中转，下载关闭时一律 403 |
| `GET` | `/api/cover/<token>` | 专辑封面（缺失时返回内置 SVG） |
| `GET` | `/api/lyric/<token>` | LRC 歌词文本 |
| `GET` | `/api/track/info/<token>` | 曲目详情与当前直链状态 |
| `POST` | `/api/track/resolve` | 直链自愈解析 `{song_name, singers, source, identifier, album}` |
| `POST` | `/api/playlist/parse` | 歌单链接解析 `{url, source}` |
| `POST` | `/api/playlist/activate` | 用纯元数据秒级加载歌单 `{tracks: [...]}` |
| `POST` | `/api/sync/create` | 生成跨端同步码，返回扫码地址 |
| `GET` | `/api/sync/get/<token>` | 取回同步数据 |
| `POST` | `/api/download/local` | 服务端落盘下载 `{token}`（下载关闭时返回 403） |

搜索接口示例：

```bash
curl -N "http://127.0.0.1:5050/api/search/stream?q=%E5%91%A8%E6%9D%B0%E4%BC%A6&sources=NeteaseMusicClient,QQMusicClient"
```

## 🐳 生产部署

推荐 **Docker + 1Panel + OpenResty**：应用只监听 `127.0.0.1:5050`，由反代负责域名与 HTTPS。

### 1. 容器编排

1Panel →【容器】→【编排】→【创建编排】，命名 `musicdl`，粘贴仓库内 [`docker-compose.yml`](docker-compose.yml) 内容；
或直接在服务器上 `docker compose up -d --build`。

### 2. 反向代理

【网站】→【创建网站】→【反向代理】→ 代理地址填 `http://127.0.0.1:5050`，随后为该站点申请 HTTPS 证书。

### 3. OpenResty / Nginx 关键参数

**这一节直接决定「边搜边出」和「拖动进度条」是否正常**，请务必在站点【配置文件】中补齐：

```nginx
proxy_http_version 1.1;
proxy_set_header Connection "";
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;

# 音频拖拽 / 续播：必须透传 Range
proxy_set_header Range $http_range;
proxy_set_header If-Range $http_if_range;

# SSE 流式搜索：必须关闭缓冲
proxy_buffering off;
proxy_cache off;
chunked_transfer_encoding on;

# 大型歌单批量解析需要更长超时
proxy_read_timeout 600s;
proxy_send_timeout 600s;
```

### 4. 更新版本

`Dockerfile` 用 `COPY . .` 把代码打进镜像层，**镜像建好之后容器里的文件就是只读快照**。所以宿主机上 `git pull` 只更新了宿主机目录，跑着的容器读的仍是旧代码 —— 光 `docker compose up -d` 也不会变，它只会复用旧镜像。

分两种情况：

```bash
cd /opt/musicdl && git pull origin main

# A. 只改了前端（index.html / style.css / app.js）—— compose 已挂载静态目录，直接生效
#    刷新浏览器即可，必要时 Ctrl+F5

# B. 改了后端 Python（server.py 等）或依赖 —— 必须重建镜像
docker compose up -d --build musicdl
```

验证容器里到底是哪一版（静态文件里带 `?v=` 版本号，最直观）：

```bash
docker compose exec musicdl grep -o 'v=[0-9_]*' /app/musicdl/web/static/index.html
```

> 静态目录的只读挂载写在仓库的 `docker-compose.yml` 里。**老部署**（在 1Panel 里粘贴过编排内容的）需要重新粘贴一次编排，只 `git pull` 不会改到已生效的 compose 配置。挂载的宿主机目录若不存在，Docker 会自动建成空目录，页面会 404，确认 `./musicdl/web/static` 在仓库里存在后再启动。

## 🧪 测试

`tests/` 下的脚本大多是**对着已启动服务**的端到端校验（基址写死 `http://127.0.0.1:5050`），
所以先起服务再跑：

```bash
musicdl-web --port 5050 --no-browser &

python -m pytest tests/                    # 函数式用例（需安装 pytest）
python -m unittest discover -s tests       # unittest 用例
python tests/verify_sources.py             # 逐个音源连通性体检
```

覆盖范围：流式搜索、音频代理 Range、下载格式与歌词内嵌、歌单解析与原始标题、播放器布局、歌单备份与恢复。

## ❓ 常见问题

| 现象 | 排查方向 |
| :-- | :-- |
| 端口被占用 | 换 `--port`，或 `lsof -i :5050` 找到占用进程 |
| 手机打不开 / 扫码地址是 127.0.0.1 | 启动加 `--host 0.0.0.0`；Docker 需放开端口映射 |
| 搜索要等很久才一起出现 | 反代缺少 `proxy_buffering off`，SSE 被缓冲了 |
| 进度条拖不动、播放到一半停 | 反代未透传 `Range` / `If-Range`，或直链已过期（见 `MUSICDL_DIRECT_URL_TTL`） |
| 某个音源一直没结果 | 单个平台接口波动，切换到其他音源；可用 `python tests/verify_sources.py` 体检 |
| 下载的中文文件名乱码 | 已用 RFC 5987/6266 编码；若仍乱码请检查浏览器与反代是否改写 `Content-Disposition` |
| 找不到下载的文件 | WebUI 的下载由浏览器保存到其默认下载目录；`--work-dir` 只作用于服务端缓存与 `/api/download/local` 落盘 |
| 封面偶尔空白 | 平台封面缺失，接口会返回内置 SVG 兜底，不影响播放 |
| `git pull` 后刷新页面没变化 | 容器里是构建时的代码快照，前端需 compose 挂载静态目录（已内置），后端改动要 `docker compose up -d --build musicdl`；详见[更新版本](#4-更新版本) |

## ⚠️ 免责声明

本仓库仅用于**学习、研究与个人测试**，禁止任何商业用途。

- 本项目只与公开可访问的 Web 端点交互，**不托管、不存储、不分发**任何受版权保护的内容；
- 不随仓库分发任何可执行程序；未经许可不得二次分发、转售或捆绑打包；
- 付费 / 订阅 / 受限内容请通过官方渠道获取；**严禁**用本项目绕过付费墙、DRM 或访问控制；
- 若你是版权方并认为本仓库侵犯了你的权益，请提供具体链接与权属证明，我会及时核实并处理（含删除相关内容）。

使用本项目即表示你已理解并同意上述条款，并自行承担由此产生的一切后果。

## 📄 许可证与致谢

- 许可证：[PolyForm Noncommercial License 1.0.0](LICENSE)（仅限非商业使用）。
- 音源内核与 50+ 平台客户端来自 [CharlesPikachu/musicdl](https://github.com/CharlesPikachu/musicdl)，作者 **Zhenchao Jin**，感谢上游长期的维护。
- 前端依赖：[Tailwind CSS](https://tailwindcss.com/)（CDN）、[qrcode](https://github.com/soldair/node-qrcode)、[jsQR](https://github.com/cozmo/jsQR)。
- 后端依赖：[Flask](https://flask.palletsprojects.com/)、[PyAV](https://pyav.org/)（转码）、[mutagen](https://mutagen.readthedocs.io/)（元数据）。

<div align="center">
<sub>如果这个工作台对你有帮助，欢迎点一个 ⭐ Star；有问题请提 Issue。</sub>
</div>
