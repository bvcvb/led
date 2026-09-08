# CoreS3 + UIFlow2 纯无线推送方案

> 目标：**脱离 USB**，让 `dsh` 里的 `key.py` 通过 WiFi 无线下发到 M5Stack CoreS3 并运行。
> 设备：M5Stack **CoreS3**，固件 **UIFlow2**，已配置好 WiFi。

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
- 完全可脚本化：`dsh` 改代码 → 更新下发源 → 设备下个周期自动拉到新版本。

### 总体架构

```text
  dsh (你的工作环境 /home/abc/work/led)
      │  push.py（GitHub API + PAT token）
      ▼
  GitHub Gist（raw 公网地址，设备 WiFi 可访问）
      ▲
      │  requests2.get(gist_raw_url).text
      ▼
  M5Stack CoreS3 (UIFlow2 固件, 已连 WiFi)
      │  device/loader.py 开机自启
      ▼
  exec(拉到的代码)  →  运行 key.py 逻辑
```

---

## 三、交付物说明

| 文件 | 位置 | 作用 |
|---|---|---|
| `key.py` | `./key.py` | 你的设备端业务代码（本方案下拉取并运行的对象） |
| `device/loader.py` | `./device/loader.py` | **设备端引导程序**：开机连 WiFi → 拉取 → exec。需作为 `main.py` 部署到设备 |
| `push.py` | `./push.py` | **dsh 端一键推送**：把本地 `key.py` 上报到 GitHub Gist |
| 本文档 | `./docs/uiflow2-wifi-push.md` | 完整说明 |
| `docs/device-flash-notes.md` | `./docs/device-flash-notes.md` | 首次部署（把 loader 弄上设备）的两种方式 |

---

## 四、前提条件（必读）

1. **设备已烧录 UIFlow2 固件**，并在 M5Burner 烧录时填好了 WiFi SSID/密码（已确认满足）。
2. **一个 GitHub 账号**，并且你能创建一个 Gist（Public 或 Private）。
3. 一个 **GitHub Personal Access Token（PAT）**，权限勾选 `gist`。用于 `push.py` 把文件写入 Gist。
4. **首次部署**需要一次把 `device/loader.py` 弄到设备上（见 `docs/device-flash-notes.md`）。此后所有更新都走 WiFi，不再需要 USB。

---

## 五、dsh 端：push.py 一键推送

把本地 `key.py` 内容更新到 Gist 的某个文件，让设备的 `loader.py` 下个周期拉到。

```bash
# 前置：GitHub token
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"   # 需 gist 权限

# 推送（更新 Gist 里的 key.py）
python3 push.py <GIST_ID> key.py
```

- `<GIST_ID>`：Gist 链接 `https://gist.github.com/<user>/<gist_id>` 中的那串 `gist_id`。
- `push.py` 会读取本地 `key.py`，用 `PATCH /gists/{gist_id}/files/key.py` 上传内容，成功后把 **raw 地址**打印出来（设备端 `loader.py` 用的就是 `https://gist.githubusercontent.com/<user>/<gist_id>/raw/key.py`）。

> 若还没有 Gist：用 GitHub 网页新建一个包含 `key.py` 的 Gist，拿到 `gist_id` 和 raw 地址即可；之后都靠 `push.py` 更新。

---

## 六、设备端：loader.py 主动拉取

作为设备 `main.py` 部署。逻辑：

1. 开机（UIFlow2 固件已自动连 WiFi）。
2. 周期 `requests2.get(<gist raw url>)` 拉取文本。
3. 与上次内容比对：有变化才 `exec()`，避免重复重载。
4. 运行中出错则打印/继续轮询，不崩溃。

**关键：raw 地址是设备能访问的公网 HTTPS 地址；拉取失败时 loader 会持续重试（降低频率），保证网络波动后能自动恢复。**

---

## 七、使用流程（日常迭代）

```text
1. 在 dsh 里改 ./key.py
2. python3 push.py <GIST_ID> key.py      # 推到下发展
3. 设备下个周期自动拉到 && 运行新版      # 无需 USB
```

想立即生效可以：重启设备 / 用 UIFlow2 网页 IDE「Run Once」。否则 loader 默认带的一个轮询周期即可自动更新。

---

## 八、局限与注意

- **代码大小**：Gist 单文件 ≤ 10MB，`key.py` 远小于此，无碍。
- **安全性**：若用 Public Gist，代码公开可见；脚本里避免硬编码隐私信息。Private Gist 也可，但设备用 raw 地址访问 Private Gist 需要带 token 的 URL（`push.py` 可生成，需注意 token 安全性）。
- **依赖 UIFlow2 设备端 `requests2` 模块**：已核实存在（`m5stack/libs/requests2`，基于 `urequests`），`Response.text` 返回字符串。
- **loader 与业务代码共存**：`loader.py` 是独立引导程序；业务逻辑 `key.py` 通常通过 `import` 或整体 `exec` 进 loader。为保持简单，本方案 loader 直接 `exec()` 拉到的整段代码。

---

## 九、参考资料

- UIFlow2 CoreS3 烧录与运行：<https://docs.m5stack.com/en/uiflow2/m5cores3/program>
- UIFlow2 网页版介绍：<https://docs.m5stack.com/en/uiflow2/uiflow_web>
- 设备端 `requests2` 模块源码：<https://github.com/m5stack/uiflow-micropython/blob/master/m5stack/libs/requests2/__init__.py>
- 设备端 WebSocket 通道源码（证明无开放 API）：<https://github.com/m5stack/uiflow-micropython/blob/master/m5stack/components/webrepl/webrepl.c>
