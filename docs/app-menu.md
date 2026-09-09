# 应用菜单（menu.py）—— 应用选择器

> 设备开机后由 loader 拉取 **`src/menu.py`** 作为主应用运行，它在屏幕上列出仓库 `src/apps.json` 里的应用，
> **点击某行先高亮选中，再次点击该行才下载并运行**。当前仓库里只有 `key.py`（键盘测试）。

---

## 文件与角色

| 文件 | 角色 |
|---|---|
| `device/loader.py` | 设备 `main.py`，**开机拉取一次** `src/menu.py` 作为主应用运行 |
| `src/menu.py` | 主应用：请求 `src/apps.json` → 列出应用 → **点选高亮，再点运行** |
| `src/apps.json` | 应用清单（含 `version`），menu 据此渲染列表并做版本对比 |
| `src/key.py` | 一个可运行的应用（键盘测试），是菜单里的一个条目 |

---

## 流程

```text
开机 → loader 拉取一次 src/menu.py → 运行 menu
                                  │ 菜单展示期: 周期性拉 src/apps.json(版本源)
                                  ▼
                         屏幕列出应用: [Keyboard Test  v1.1.0]
                                  │ 用户点击该行 → 选中高亮(绿色/箭头)
                                  ▼
                         再次点击该行 → 再拉一次 apps.json → 版本对比
                                  ├─ 版本变 → 拉取 src/key.py, exec, 运行
                                  └─ 版本同 → 复用已加载的, 运行
```

---

## 版本对比（增量加载）机制

- **`apps.json`（小）每次都拉取**：菜单展示期每 3 秒 + 点选前，作为版本对比源。
- **应用 `.py`（大）只在版本变化时下载**：menu 保存每个应用已加载的 `version`（`_loaded_ver`），
  点选时对比 `apps.json` 声明的 `version`，相同则复用已加载并运行，不同才重新下载。

好处：改某应用后**升版本号**即可让设备重新下载；版本不变则设备复用本地，省流量。

---

## src/apps.json 格式

```json
{
  "apps": [
    {
      "file": "key.py",
      "name": "Keyboard Test",
      "desc": "Faces Keyboard3 键盘测试",
      "version": "v1.1.0"
    }
  ]
}
```

- `file`：仓库 `src/` 里该应用的文件名（menu 用它拼 raw URL）。
- `name`：屏幕上显示的名称。
- `version`：应用版本号，用于增量加载判断（应与应用内 `APP_VERSION` 一致）。
- 想加新应用：往 `apps` 数组再加一项，并把该 `.py` 推到仓库 `src/` 下即可。

---

## 更新策略（重要）

- **loader 开机拉取一次 `menu.py`**：`menu.py` 更新后需**重启设备**才生效（menu 不常改，代价可接受）。
- **运行应用期间 loader 不再拉取**：不会因为 menu 更新而打断正在运行的应用。
- **应用的更新**：改 `src/key.py` + `apps.json` 的 `version` 后 `push.py`，设备在菜单展示期/点选时对比版本，自动重新下载。

---

## 如何在 menu 里新增一个应用

假设你要加 `blink.py`：

1. 写好 `src/blink.py`（只提供 `setup()`/`loop()`，不要独立死循环——由 menu 调度）。
2. 在 `src/apps.json` 的 `apps` 里加一项：
   ```json
   { "file": "blink.py", "name": "Blink", "desc": "闪灯示例", "version": "v1.0.0" }
   ```
3. 推送这两个文件到仓库 `src/` 下（GitHub token 需仓库 Contents 权限）：
   ```bash
   export GITHUB_TOKEN="github_pat_xxx"
   GH_PATH=src/apps.json python3 push.py src/apps.json
   GH_PATH=src/blink.py python3 push.py src/blink.py
   ```
4. 重启设备（loader 重新拉 `menu.py`；menu 重新拉 `apps.json` 显示新条目）。

---

## 当前已有应用

| 应用 | 文件 | 说明 |
|---|---|---|
| Keyboard Test | `src/key.py` | Faces Keyboard3 键盘与指示灯测试（版本号显示在屏幕左上） |

---

## 相关文件

- `src/apps.json` —— 应用清单（版本对比源）
- `src/menu.py` —— 应用选择器
- `docs/uiflow2-wifi-push.md` —— 无线推送整体方案
