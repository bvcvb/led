# 首次部署 loader 到 CoreS3

> 本步骤**只需要做一次**：把 `device/loader.py` 弄到 CoreS3 上并让它开机自启。
> 之后所有代码更新都走 WiFi（`push.py` → 仓库 → 设备自动拉取），不再需要本步骤。
> 设备：CoreS3，固件 UIFlow2，已配好 WiFi。

---

## 方式一：UIFlow2 网页 IDE「Run Always（下载到设备）」（最省事）

> 前提：设备能连上 `uiflow2.m5stack.com` 网页 IDE（通过 Access Code 无线，或 USB）。

1. 打开 <https://uiflow2.m5stack.com/>，登录 M5Stack 账号。
2. 按官方 CoreS3 流程连接设备：
   - **无线**：查看设备 UIFlow2 启动屏上的 **Access Code** → 网页端「Connect Device」→ 输入 Access Code + 设备名 → 确认。
   - 或 **USB**：网页端 WebTerminal 选串口连接。
3. 把本地 `device/loader.py` 的内容粘贴进 UIFlow2 编辑器的 Python 模式（或用底部导入将其作为程序）。
   - loader 顶部的 `FETCH_URL` 已经是仓库地址 `https://raw.githubusercontent.com/bvcvb/led/master/key.py`，无需再改；若要改，以 `push.py` 输出的 `fetch_url` 为准。
4. 点击右下角 **Run Always**（= 把程序下载到设备，且把设备 `boot_option` 设为 2，开机直接跑 `main.py`）。

> 官方说明(见参考)：`Run Once` = 跑一次；`Run Always` = download 到设备并在 boot_option=2 下自启。后者正是我们要的。

5. 设备重启后即进入 loader 的轮询循环。

---

## 方式二：USB + `mpremote` 直接推文件

> 如果你更愿意用命令行一次性把 loader 部署成设备 `main.py`。

```bash
# 本机安装 mpremote(已在本机临时目录可用, 或正常 pip 安装)
# pip install mpremote

# 连接设备(串口名以实际检测到为准)
mpremote connect port:/dev/ttyACM0

# 把 loader.py 推成设备 main.py
mpremote connect port:/dev/ttyACM0 cp device/loader.py :main.py

# 软复位让设备重启并运行 main.py
mpremote connect port:/dev/ttyACM0 reset
```

> 注意：`mpremote` 走 USB 串口。此方式只用于**首次**把 loader 装上；之后的业务代码更新都走 WiFi。

---

## 部署后验证

- 看设备屏幕/串口日志是否打印：
  `[loader] started, polling: https://raw.githubusercontent.com/bvcvb/led/master/key.py`
- 手动跑一次 `push.py`，等一个轮询周期，看是否打印：
  `[loader] got new code, (N bytes)`

---

## 关键点

- **`FETCH_URL` 必须填对**：就是 `push.py` 成功输出后的 `fetch_url`（当前为 `https://raw.githubusercontent.com/bvcvb/led/master/key.py`）。填错设备会一直拉不到。
- **`push.py` 推送的目标与 loader 拉取的地址必须一致**：loader 拉 `bvcvb/led/master/key.py`；push.py 默认也推 `bvcvb/led/master/key.py`。两者匹配才能拉到新版。
- **loader 是引导层**：真正的业务逻辑是 `key.py`(被拉取后 `exec`)。要改设备行为就改 `key.py` 并 `push.py`，别再动设备上的 loader。
- 想立刻更新：重启设备或轮询周期(默认 5s)到点即可。也可以把 `POLL_INTERVAL_MS` 调小让更及时。
- `push.py` 推完后，需要 `git commit`/`git push` 到仓库吗？**不需要**——`push.py` 直接用 GitHub Contents API 把内容写到远端仓库文件，不经过本地 git。

---

## 参考

- UIFlow2 CoreS3 烧录与运行：<https://docs.m5stack.com/en/uiflow2/m5cores3/program>
- mpremote 文档：<https://docs.micropython.org/en/latest/reference/mpremote.html>
