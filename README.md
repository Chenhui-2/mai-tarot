# 🔮 MaiBot 塔罗牌占卜插件

一个功能完整的塔罗牌占卜插件，适用于 [MaiBot](https://docs.mai-mai.org/) 机器人框架。支持单张抽牌和三张牌阵，提供 AI 智能解读，配置灵活可扩展。

---

## 功能特性

| 功能 | 说明 |
|------|------|
| 🃏 **78 张完整牌库** | 22 张大阿卡纳 + 56 张小阿卡纳（权杖、圣杯、宝剑、星币四组） |
| 🔄 **正/逆位随机** | 每次抽牌随机决定正位或逆位，附带对应的牌面含义 |
| 1️⃣ **单张抽牌模式** | 输入 `/tarot` 或 `/tarot 1`，直接输出牌面名称、位置和解读 |
| 3️⃣ **三张牌阵模式** | 输入 `/tarot 3`，抽取三张牌，按「积极的方面」「消极的方面」「中性的方面」由 AI 进行专业解读 |
| 🤖 **AI 智能解读** | 三张牌阵模式下调用 `ctx.llm.generate()` 生成个性化占卜解读 |
| ⚙️ **TOML 配置** | 指令名称、AI 参数、图片开关等均可通过 `config.toml` 调整，无需修改代码 |
| 🖼️ **图片输出** | 可配置 JPG 牌面素材路径，抽牌时自动发送对应图片（需在 `config.toml` 中开启） |
| 🔌 **即插即用** | 遵循 MaiBot 插件规范，放入 `plugins/` 目录即可自动加载 |

---

## 安装

1. 将 `mai-tarot/` 整个目录复制到 MaiBot 的 `plugins/` 目录下：

   ```
   plugins/
   └── mai-tarot/
       ├── _manifest.json
       ├── plugin.py
       ├── tarot_data.py
       ├── config.toml
       └── assets/
           └── cards/              # 牌面 JPG 素材（用户自行放入）
   ```

2. 重启 MaiBot 或触发插件热重载，插件即自动加载。

3. 确保 MaiBot 主程序版本 >= 1.0.0，SDK 版本 >= 1.0.0。

---

## 使用方法

### 单张抽牌

```
/tarot
```

或显式指定数量：

```
/tarot 1
```

**效果示例：**

```
🔮 塔罗牌占卜 - 单张抽牌

🃏 节制 (Temperance) — 正位

📖 牌面解读：平衡、适度、耐心、和谐、融合
```

### 三张牌阵

```
/tarot 3
```

**三张牌阵支持附带占卜问题**，问题会交给 AI 结合牌面进行针对性解读：

```
/tarot 3 关于爱情的方向
```

**效果示例：**

```
🔮 塔罗牌占卜 - 三张牌阵
占卜问题：关于爱情的方向
━━━━━━━━━━━━━━━━

1️⃣ 命运之轮 (Wheel of Fortune) — 正位
2️⃣ 宝剑五 (Five of Swords) — 逆位
3️⃣ 星币皇后 (Queen of Pentacles) — 正位

🤖 AI 塔罗解读：

【积极的方面】命运之轮正位预示着你正处于一个积极变化的拐点...
【消极的方面】宝剑五逆位暗示你需要避免不必要的冲突...
【中性的方面】星币皇后正位提醒你保持务实和稳定的态度...
```

---

## 配置说明

所有配置项集中在 `config.toml` 中。AI 参数、图片开关等运行时配置修改后调用 `on_config_update()` 即可生效；**指令词（`custom_commands`）在插件加载时读取，修改后需重启插件或触发插件重载**。

### 指令配置

```toml
[commands.tarot]
custom_commands = ["/tarot", "/塔罗"]
description = "塔罗牌占卜"
usage = "/tarot [数量] [问题] 或 /塔罗 [数量] [问题]"
examples = ["/tarot", "/塔罗 1", "/tarot 3 关于爱情的方向"]
note = "可通过 custom_commands 自定义触发词，支持配置多个别名"
```

| 参数 | 说明 |
|------|------|
| `custom_commands` | 自定义触发词列表，数组格式。可配置任意多个，如 `["/tarot", "/塔罗", "/占卜"]` |
| `usage` | 使用说明（展示用） |
| `examples` | 示例列表（展示用） |

> 兼容说明：旧版使用 `command = "/tarot"` 单字符串格式仍可用，插件会自动识别。若同时存在 `custom_commands` 和 `command`，优先使用 `custom_commands`。

### AI 配置

```toml
[ai]
enabled = true
temperature = 0.7
max_tokens = 800
system_prompt = "你是一位专业的塔罗牌占卜师..."
```

| 参数 | 说明 |
|------|------|
| `enabled` | AI 解读开关，设为 `false` 则三张牌阵模式仅输出牌面基础含义 |
| `temperature` | 生成温度 (0.0~1.0)，越高越有创意 |
| `max_tokens` | 单次解读最大 token 数 |
| `system_prompt` | AI 角色设定提示词，可自定义占卜风格 |

> AI 解读不指定模型，自动调用 MaiBot 的 replyer 回复模型。

### 图片输出配置

```toml
[image_output]
enabled = false
assets_dir = "assets/cards"
```

| 参数 | 说明 |
|------|------|
| `enabled` | 设为 `true` 启用图片输出 |
| `assets_dir` | JPG 牌面素材目录（相对插件目录） |

请自行在目录的相应位置添加卡图，命名规则如下

**文件命名规则**

牌面图片需按牌的英文名命名，示例如下：

| 牌名 | 文件名 |
|------|--------|
| The Fool | `the-fool.jpg` |
| The Magician | `the-magician.jpg` |
| Ace of Wands | `ace-of-wands.jpg` |
| Knight of Cups | `knight-of-cups.jpg` |

> 转换步骤：**英文名全小写** → **空格转连字符** → **去除非字母数字字符** → **追加 `.jpg` 后缀**

---

## 插件架构

```
mai-tarot/
├── _manifest.json           # 插件清单：ID、版本、能力声明
├── plugin.py                # 主插件入口：MaiBotPlugin 子类
│   ├── TarotPlugin          # 插件主类
│   │   ├── on_load()        # 加载时读取配置
│   │   ├── on_unload()      # 卸载时清理资源
│   │   └── on_config_update()  # 配置热更新
│   └── @Command("tarot")    # 命令处理器
│       ├── _handle_command()   # 命令分发
│       ├── _single_card()      # 单张抽牌
│       ├── _three_cards()      # 三张牌阵
│       ├── _ai_interpret()     # AI 解读
│       └── _try_send_image()   # JPG 图片输出
├── tarot_data.py            # 78 张塔罗牌完整数据
│   ├── MAJOR_ARCANA         # 22 张大阿卡纳
│   ├── MINOR_ARCANA         # 56 张小阿卡纳（4组×14张）
│   └── ALL_CARDS            # 合并后的完整牌表
├── config.toml              # 运行时配置（指令、AI、图片）
├── assets/
│   └── cards/              # 牌面 JPG 素材（用户自行放入）
└── README.md                # 本文件
```

### 核心依赖

- `maibot-sdk` >= 1.0.0（提供 `MaiBotPlugin`、`Command` 等基类）
- 标准库：`tomllib`、`random`、`pathlib`

---

## 塔罗牌数据

插件内置了完整的 78 张塔罗牌数据：

| 分组 | 数量 | 说明 |
|------|------|------|
| 大阿卡纳 (Major Arcana) | 22 张 | 愚人、魔术师、女祭司……世界 |
| 权杖 (Wands) | 14 张 | 火元素，代表行动、热情、创造力 |
| 圣杯 (Cups) | 14 张 | 水元素，代表情感、直觉、人际关系 |
| 宝剑 (Swords) | 14 张 | 风元素，代表思想、沟通、冲突 |
| 星币 (Pentacles) | 14 张 | 土元素，代表物质、工作、财富 |

每张牌均包含中英文名称、正位含义、逆位含义。

---

## 开发

### 添加新牌面

在 `tarot_data.py` 中的对应分组下添加新条目即可：

```python
{
    "id": 22,
    "name": "自定义牌",
    "name_en": "Custom Card",
    "upright": "正位含义",
    "reversed": "逆位含义",
}
```

### 自定义 AI 解读风格

修改 `config.toml` 中的 `ai.system_prompt` 即可改变 AI 的解读风格。例如：

```toml
system_prompt = "你是一位神秘学塔罗大师，请用富有诗意的语言解读..."
```

### 图片素材

在 `assets/cards/` 目录下放入 JPG 牌面图片，文件名需与牌的英文名对应。例如：

| 牌名 | 文件名 |
|------|--------|
| The Fool | `the-fool.jpg` |
| The Magician | `the-magician.jpg` |
| Ace of Wands | `ace-of-wands.jpg` |
| Knight of Cups | `knight-of-cups.jpg` |

文件名规则：英文名全小写，空格转连字符，去除非字母数字字符。启用 `image_output.enabled = true` 后，抽牌时会自动搜索并发送对应的 JPG 图片。

---

## 许可证

MIT License

---

## 相关链接

- [MaiBot 文档中心](https://docs.mai-mai.org/)
- [MaiBot 插件开发指南](https://docs.mai-mai.org/plugin/)
- [MaiBot SDK](https://pypi.org/project/maibot-sdk/)
