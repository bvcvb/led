# 用 USB + mpremote 部署 loader 到 CoreS3（在你的电脑上）

> 这是绕开 UIFlow2 网页 IDE 的可靠方式：直接把 `device/loader.py` 拷成设备的 `main.py`。
> 前提：**在你自己的电脑**上做（不要在这台 dsh 沙箱里，沙箱连不到设备 USB）。
> 设备：CoreS3，固件 UIFlow2（MicroPython 1.27.0），已配好 WiFi。

---

## 一、准备（一次）

```bash
# 装 mpremote（任选其一）
pip install mpremote
# 或免安装直接跑:
# pypi 方式: pipx run mpremote ...
```

```bash
# 把本项目拉到本地(如果还没有)
git clone https://github.com/bvcvb/led.git
cd led
# 之后要更新代码: git pull
```

---

## 二、把 loader 部署成设备 main.py（一次就能用）

1. **用 USB-C 数据线把 CoreS3 接到电脑**。
2. 确认串口出现：
   ```bash
   mpremote connect list
   ```
   Linux 常见 `dev:/dev/ttyACM0`。
3. 把 `device/loader.py` 拷成设备 `main.py`：
   ```bash
   mpremote connect /dev/ttyACM0 cp device/loader.py :main.py
   ```
4. 软复位让设备重启并运行：
   ```bash
   mpremote connect /dev/ttyACM0 reset
   ```
5. 观察串口日志（可选，进入 REPL 看输出）：
   ```bash
   mpremote connect /dev/ttyACM0 repl
   ```
   应看到：
   ```
   [loader] started, polling: https://raw.githubusercontent.com/bvcvb/led/master/src/menu.py
   ```

---

## 三、之后日常更新（不再需要 USB，纯无线）

此后 `main.py` = loader 在设备上常驻，它会周期去拉仓库里的 `src/menu.py`（应用菜单）。改某个应用代码只需：

```bash
# 在你电脑上
cd led
改 src/key.py
python3 push.py src/key.py         # 推 src/key.py 到 bvcvb/led/master/src/key.py
```

设备下个轮询周期（默认 3s）自动拉取菜单/应用，全程无 USB。

> `push.py` 需要 `GITHUB_TOKEN`(仓库 Contents 权限)，且依赖 git 仓库里的 `push.py` 脚本。
> 快捷示例：
> ```bash
> export GITHUB_TOKEN="github_pat_xxx"
> python3 push.py src/key.py       # 推本地 src/key.py 到 bvcvb/led/master/src/key.py
> ```

---

## 四、常见问题

- **主板进不了下载模式**：CoreS3 长按 G0 到指示灯由红变绿再松开（已在 M5Burner 烧录时验证过）。
- **`connect list` 看不到设备**：换一根**数据线**（有些线只能充电）；确认 `/dev/ttyACM0` 权限，必要时 `sudo` 或加入 `dialout` 组。
- **拷进去后没打印 `[loader] started`**：可能 `main.py` 没被设为自启。可在 REPL 里软复位，或确认设备没有旧 `main.py` 版本先行启动。若不确定，先 `mpremote connect /dev/ttyACM0 repl`，然后 `import main` 手动运行一次看输出。
- **想还原/清除设备**：`mpremote connect /dev/ttyACM0 fs rm :main.py`，再 `reset`。

---

## 五、验证清单

- [ ] `mpremote connect list` 能看到 CoreS3 串口
- [ ] `cp device/loader.py :main.py` 成功
- [ ] `reset` 后日志打印 `[loader] started, polling: https://raw.githubusercontent.com/bvcvb/led/master/src/menu.py`
- [ ] 改 `key.py` 后跑 `python3 push.py`，等一个周期设备打印 `[loader] got new code, (N bytes)`
