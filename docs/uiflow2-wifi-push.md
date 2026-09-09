# CoreS3 + UIFlow2 纯无线推送方案

> 目标：**脱离 USB**，让 `dsh` 里的代码通过 WiFi 无线下发到 M5Stack CoreS3 并运行。
> 设备：M5Stack **CoreS3**，固件 **UIFlow2**，已配置好 WiFi。
> 下发展：**GitHub 仓库 `bvcvb/led`**（公开），代码在 `src/` 目录下。

---

## 一、为什么不能用「UIFlow2 官方接口」直接推

已核实官方源码（`m5stack/components/webrepl/webrepl.c`）：

```c
#define WEBREPL_URI_TEMPLATE "ws://uiflow2.m5stack.com/ws/realtime?role=device&mac=%s"
```

这个 `webrepl` 组件是**设备端主动连 UIFlow2 云服务器**的 WebSocket 客户端，走的是私有云协议 + 账号会话，**不是开放 API**。标准 WebREPL（局域网直连）在这套固件中不可用，`mpremote connect` 也不支持 WebREPL。

所以「从命令行调一个官方接口推代码」这条路**不存在**。

---

## 二、可行方案：设备端「主动拉取」+ dsh 一键下发

设备（CoreS3）开机连 WiFi 后，**主动**请求一个它能访问的公网地址上的代码文件，拿到后 `exec()` 运行。这样：无需 USB、无需 UIFlow2 云、完全可脚本化。

### 总体架构（两级）

```text
  dsh (你的工作环境 /home/abc/work/led)
      │  push.py（GitHub Contents API + PAT token）
      ▼
  GitHub 仓库 bvcvb/led/src/（公开）
        ├─ menu.py        ← 应用选择器(主程序)
        ├─ apps.json      ← 应用清单
        └─ key.py         ← 一个可运行应用(键盘测试)
      ▲
      │  requests2.get(...)
      ▼
  M5Stack CoreS3 (UIFlow2 固件)
      │  loader.py(设备 /main.py) 开机自启
      ▼
  拉取 src/menu.py → 运行菜单 → 列出 src/apps.json 的应用
                        ↑ 点选某应用 → 拉取 src/<file> → 运行
```

- **loader（设备 `main.py`）**：开机拉取 **`src/menu.py`** 并作为主应用运行。
- **menu.py**：列出 **`src/apps.json`** 里的应用，点选后拉取并运行。
- 下发展 raw 地址（loader 拉取）：`https://raw.githubusercontent.com/bvcvb/led/master/src/menu.py`

---

## 三、交付物说明

| 文件 | 位置 | 作用 |
|---|---|---|
| `src/menu.py` | 设备端主应用 | 应用选择器：列清单、点选下载运行 |
| `src/apps.json` | 应用清单 | 列出可运行应用（当前只有 `key.py`） |
| `src/key.py` | 一个应用 | 键盘测试（业务代码） |
| `device/loader.py` | 设备 `main.py` | 开机拉取 `src/menu.py` 并运行 |
| `push.py` | `./push.py` | **dsh 端一键推送**：把本地文件写到仓库 `src/` 下 |
| `docs/` | `./docs` | 说明文档 |

---

## 四、前提条件

1. 设备已烧录 UIFlow2 固件，烧录时填好了 WiFi SSID/密码。
2. GitHub 仓库 `bvcvb/led`（公开），代码在 `src/` 下。
3. 一个 PAT（token），需仓库 **Contents 读写** 权限，通过环境变量 `GITHUB_TOKEN` 传入。
4. 首次部署需把 `device/loader.py` 设为设备 `main.py`（见 `docs/device-flash-notes.md` / `docs/usb-mpremote-deploy.md`）。

> 仓库必须公开：设备端 `requests2.get()` 无法免认证访问私有仓库 raw。

---

## 五、dsh 端：push.py 一键推送

把本地 `src/key.py` 内容更新到仓库 `src/key.py`（或任意应用），设备的 menu 下个周期拉到。

```bash
export GITHUB_TOKEN="github_pat_xxx"
python3 push.py src/key.py       # 默认推 src/key.py
```

推其它文件用 `GH_PATH` 指定仓库内路径：
```bash
GH_PATH=src/menu.py python3 push.py src/menu.py
GH_PATH=src/apps.json python3 push.py src/apps.json
```

成功会打印 `fetch_url` 供核对。`push.py` 直接用 Contents API 写远端文件，不经过本地 git。

---

## 六、使用流程（日常迭代）

```text
1. 在 dsh 里改 src/key.py (或新增应用 src/<file>.py)
2. python3 push.py src/key.py        # 推到仓库 src/key.py
3. 设备上 menu 列表项点选 → 自动拉到新版运行   # 无需 USB
```

想立即生效可重启设备（menu 重新拉取），否则 loader 周期性检查（默认 3s）自动拉取。

---

## 七、局限与注意

- **仓库公开**：`src/` 下代码对所有人可见，**不要硬编码 token/密钥**。
- **token 安全**：只通过环境变量 `GITHUB_TOKEN` 传入，并尽快轮换（本会话 PAT 已暴露，建议重新生成）。
- **依赖 `requests2` 模块**：已核实存在于设备固件（基于 `urequests`），`Response.text` 返回字符串。
- **两级结构**：loader 拉 menu，menu 拉具体应用；应用只需提供 `setup()`/`loop()`，不要写独立死循环。

---

## 八、参考资料

- UIFlow2 CoreS3 烧录与运行：<https://docs.m5stack.com/en/uiflow2/m5cores3/program>
- 设备端 `requests2` 模块源码：<https://github.com/m5stack/uiflow-micropython/blob/master/m5stack/libs/requests2/__init__.py>
- 设备端 WebSocket 通道源码：<https://github.com/m5stack/uiflow-micropython/blob/master/m5stack/components/webrepl/webrepl.c>
- 下发仓库：<https://github.com/bvcvb/led>
