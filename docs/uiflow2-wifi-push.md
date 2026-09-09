# CoreS3 + UIFlow2 纯无线推送方案

> 目标：**脱离 USB**，让 `dsh` 里的 `key.py` 通过 WiFi 无线下发到 M5Stack CoreS3 并运行。
> 设备：M5Stack **CoreS3**，固件 **UIFlow2**，已配置好 WiFi。
> 下发展：**GitHub 仓库 `bvcvb/led`**（公开，raw 地址可免认证拉取）。

---

## 一、为什么不能用「UIFlow2 官方接口」直接推

已核实官方源码（`m5stack/uiflow-micropython` 的 `m5stack/components/webrepl/webrepl.c`）：

```c
#define WEBREPL_URI_TEMPLATE "ws://uiflow2.m5stack.com/ws/realtime?role=device&mac=%s"
```

这个 `webrepl` 组件是**设备端主动连 UIFlow2 云服务器**的 WebSocket 客户端（`esp_websocket_client`），收到云端 `type=="clientMessage"` 的 `payload` 后，经 `dupterm` 写进 MicroPython 的 stdin 交给 REPL 执行。

**结论：**
- UIFlow2 的无线推送走的是**私有云协议 + 账号会话**，不是开放 API。
- 设备当前是 WebSocket **客户端**（主动向外连），不是局域网监听服务。
- 标准 WebREPL（`8266` 端口局域网直连）在这套固件中**不可用**，`mpremote connect` 也不支持 WebREPL。

所以「从命令行调一个官方接口推代码」这条路**不存在**。

---

## 二、可行方案：设备端「主动拉取」+ dsh 一键下发

**核心思想**：把「推送」变成「拉取」。设备（CoreS3）开机连上 WiFi 后，**主动**去请求一个它能访问到的公网地址上的代码文件，拿到后 `exec()` 运行。这样：

- 无需 USB（设备联网自行拉取）。
- 无需 UIFlow2 云 / 账号会话。
- 完全可脚本化：`dsh` 改代码 → 更新下发展 → 设备下个周期自动拉到新版本。

### 总体架构

```text
  dsh (你的工作环境 /home/abc/work/led)
      │  push.py（GitHub Contents API + PAT token）
      ▼
  GitHub 仓库 bvcvb/led（公开，raw 地址设备免认证可访问）
      ▲
      │  requests2.get(raw_url).text
      ▼
  M5Stack CoreS3 (UIFlow2 固件, 已连 WiFi)
      │  device/loader.py 开机自启
      ▼
  exec(拉到的代码)  →  运行 key.py 逻辑
```

下发展 raw 地址：`https://raw.githubusercontent.com/bvcvb/led/master/key.py`

---

## 三、交付物说明

| 文件 | 位置 | 作用 |
|---|---|---|
| `key.py` | `./key.py` | 你的设备端业务代码（本方案下拉取并运行的对象） |
| `device/loader.py` | `./device/loader.py` | **设备端引导程序**：开机连 WiFi → 拉取 → exec。需作为 `main.py` 部署到设备 |
| `push.py` | `./push.py` | **dsh 端一键推送**：把本地 `key.py` 上报到仓库 `bvcvb/led/master/key.py` |
| 本文档 | `./docs/uiflow2-wifi-push.md` | 完整说明 |
| `docs/device-flash-notes.md` | `./docs/device-flash-notes.md` | 首次部署（把 loader 弄上设备）的两种方式 |

---

## 四、前提条件（必读）

1. **设备已烧录 UIFlow2 固件**，并在 M5Burner 烧录时填好了 WiFi SSID/密码（已确认满足）。
2. 一个 **GitHub** 账号，仓库 **`bvcvb/led`**（已建好，**公开**）。下发展的 `key.py` 文件就在这个仓库的 `master` 分支。
3. 一个 **GitHub Personal Access Token（PAT）**，需有该仓库的 **Contents 读写** 权限。用于 `push.py` 把文件写入仓库。
4. **首次部署**需要一次把 `device/loader.py` 弄到设备上（见 `docs/device-flash-notes.md`）。此后所有更新都走 WiFi，不再需要 USB。

> 仓库必须是**公开**的：设备端 `requests2.get()` 无法免认证访问私有仓库的 raw 地址。若改为私有，需要带 token 的拉取方式（会泄露 token，不推荐）。

---

## 五、dsh 端：push.py 一键推送

把本地 `key.py` 内容更新到仓库 `bvcvb/led/master/key.py`，让设备的 `loader.py` 下个周期拉到。

```bash
# 前置：GitHub token（需该仓库 Contents 读写权限）
export GITHUB_TOKEN="github_pat_xxxx"

# 推送（默认推 bvcvb/led/master/key.py）
python3 push.py
# 或显式指定本地文件
python3 push.py key.py
```

成功会打印设备端可用的 `fetch_url`：

```text
[push] 已更新 bvcvb/led/master/key.py (3602 bytes)
[push] fetch_url (设备端 loader 用这个):
       https://raw.githubusercontent.com/bvcvb/led/master/key.py
```

可选环境变量：`GH_OWNER`（默认 `bvcvb`）、`GH_REPO`（默认 `led`）、`GH_BRANCH`（默认 `master`）、`GH_PATH`（默认 `key.py`）。

> `push.py` 用 GitHub **Contents API** 直接把内容写到远端仓库文件，**不经过本地 git**（无需 commit/push）。

---

## 六、设备端：loader.py 主动拉取

作为设备 `main.py` 部署。逻辑：

1. 开机（UIFlow2 固件已自动连 WiFi）。
2. 周期 `requests2.get(<raw url>)` 拉取文本。
3. 与上次内容比对：有变化才 `exec()`，避免重复重载。
4. 运行中出错则打印/继续轮询，不崩溃。

**关键：raw 地址是设备能访问的公网 HTTPS 地址，且仓库公开可免认证；拉取失败时 loader 会持续重试（保持轮询），保证网络波动后自动恢复。**

---

## 七、使用流程（日常迭代）

```text
1. 在 dsh 里改 ./key.py
2. python3 push.py                    # 推到 bvcvb/led/master/key.py
3. 设备下个周期自动拉到 && 运行新版    # 无需 USB
```

想立即生效可以：重启设备 / 用 UIFlow2 网页 IDE「Run Once」。否则 loader 默认的轮询周期（5s）到点即自动更新。

---

## 八、局限与注意

- **代码大小**：仓库文件无 Gist 的 10MB 限制，`key.py` 远小于此，无碍。
- **安全性**：仓库是**公开**的，`key.py`、`push.py` 等对所有人可见，**代码里不要硬编码任何 token/密钥**。token 只通过环境变量 `GITHUB_TOKEN` 传入，并尽快轮换（本会话的 PAT 已暴露，建议重新生成）。
- **依赖 UIFlow2 设备端 `requests2` 模块**：已核实存在（`m5stack/libs/requests2`，基于 `urequests`），`Response.text` 返回字符串。
- **loader 与业务代码共存**：`loader.py` 是独立引导程序；业务逻辑 `key.py` 通过整体 `exec()` 拉进的代码运行。为保持简单，loader 直接 `exec()` 拉到的整段代码。

---

## 九、参考资料

- UIFlow2 CoreS3 烧录与运行：<https://docs.m5stack.com/en/uiflow2/m5cores3/program>
- UIFlow2 网页版介绍：<https://docs.m5stack.com/en/uiflow2/uiflow_web>
- 设备端 `requests2` 模块源码：<https://github.com/m5stack/uiflow-micropython/blob/master/m5stack/libs/requests2/__init__.py>
- 设备端 WebSocket 通道源码（证明无开放 API）：<https://github.com/m5stack/uiflow-micropython/blob/master/m5stack/components/webrepl/webrepl.c>
- 下发仓库：<https://github.com/bvcvb/led>
