# 应用菜单（menu.py）—— 应用选择器

> 设备开机后由 loader 拉取 **`src/menu.py`** 作为主应用运行，它在屏幕上列出仓库 `src/apps.json` 里的应用，
> 点选某个应用后，下载该应用代码并运行。当前仓库里只有 `key.py`（键盘测试）。

---

## 文件与角色

| 文件 | 角色 |
|---|---|
| `device/loader.py` | 设备 `main.py`，开机拉取 **`src/menu.py`** 作为主应用运行 |
| `src/menu.py` | 主应用：请求 `src/apps.json` → 列出应用 → 点选 → 下载运行 |
| `src/apps.json` | 应用清单（当前只有 `key.py`），menu 根据它渲染列表 |
| `src/key.py` | 一个可运行的应用（键盘测试），是菜单里的一个条目 |

---

## 流程

```text
开机 → loader 拉取 src/menu.py → 运行 menu
                              │ 请求 src/apps.json
                              ▼
                     屏幕列出应用: [Keyboard Test]
                              │ 用户点选该行
                              ▼
                     menu 拉取 src/key.py → exec → 运行(setup/loop)
```

---

## src/apps.json 格式

```json
{
  "apps": [
    { "file": "key.py", "name": "Keyboard Test", "desc": "Faces Keyboard3 键盘测试" }
  ]
}
```

- `file`：仓库 `src/` 里该应用的文件名（menu 用它拼 raw URL）。
- `name`：屏幕上显示的名称。
- 想加新应用：往 `apps` 数组再加一项，并把该 `.py` 推到仓库 `src/` 下即可。

---

## 如何在 menu 里新增一个应用

假设你要加 `blink.py`：

1. 写好 `src/blink.py`（只提供 `setup()`/`loop()`，不要独立死循环——由 menu 调度）。
2. 在 `src/apps.json` 的 `apps` 里加一项：
   ```json
   { "file": "blink.py", "name": "Blink", "desc": "闪灯示例" }
   ```
3. 推送这两个文件到仓库 `src/` 下（GitHub token 需仓库 Contents 权限）：
   ```bash
   export GITHUB_TOKEN="github_pat_xxx"
   GH_PATH=src/apps.json python3 push.py src/apps.json
   GH_PATH=src/blink.py python3 push.py src/blink.py
   ```
4. 重启设备（menu 会重新拉 `src/apps.json` 显示新条目）。

> 想直接跑某个应用、跳过菜单：把 `device/loader.py` 顶部的 `FETCH_URL`
> 改成 `https://raw.githubusercontent.com/bvcvb/led/master/src/<file>` 即可（如 key.py），再重拷 loader 到设备。

---

## 当前已有应用

| 应用 | 文件 | 说明 |
|---|---|---|
| Keyboard Test | `src/key.py` | Faces Keyboard3 键盘与指示灯测试（版本号显示在屏幕左上） |

---

## 相关文件

- `src/apps.json` —— 应用清单
- `src/menu.py` —— 应用选择器
- `docs/uiflow2-wifi-push.md` —— 无线推送整体方案
