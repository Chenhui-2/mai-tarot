"""
塔罗牌占卜插件

功能：
- 单张抽牌：随机抽取一张塔罗牌，输出正/逆位解读
- 三张牌阵：抽取三张牌，按「积极」「消极」「中性」三方面由AI解读
- 指令与AI配置通过 config.toml 管理
- 图片输出：根据 JPG 牌面素材发送图片，自动匹配文件名
"""

import random
import re
import base64
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:  # pragma: no cover
        tomllib = None  # type: ignore

from maibot_sdk import Command, MaiBotPlugin

from .tarot_data import ALL_CARDS, MAJOR_ARCANA, SUITS


def _get_plugin_dir() -> Path:
    """返回当前插件源码目录"""
    return Path(__file__).resolve().parent


def _default_config() -> dict:
    """返回默认配置（config.toml 缺失或解析失败时使用）"""
    return {
        "commands": {
            "tarot": {
                "custom_commands": ["/tarot"],
                "description": "塔罗牌占卜",
                "usage": "/tarot [数量] [问题]",
            }
        },
        "ai": {
            "enabled": True,
            "model": "replyer",
            "temperature": 0.7,
            "max_tokens": 800,
            "system_prompt": "你是一位专业的塔罗牌占卜师，请根据用户抽到的塔罗牌进行解读。",
        },
        "image_output": {
            "enabled": False,
            "assets_dir": "assets/cards",
        },
    }


def _load_config() -> dict:
    """从插件目录加载 config.toml"""
    if tomllib is None:
        return _default_config()
    config_path = _get_plugin_dir() / "config.toml"
    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except (FileNotFoundError, ValueError):
        return _default_config()


def _get_command_prefixes(config_cmd: dict) -> list:
    """从配置中获取命令前缀列表，兼容旧版单字符串格式"""
    if not config_cmd:
        return ["/tarot"]
    raw = config_cmd.get("custom_commands") or config_cmd.get("command") or ["/tarot"]
    if isinstance(raw, str):
        return [raw]
    return list(raw or ["/tarot"])


def _build_command_pattern(primary: str, aliases: list) -> str:
    """根据主指令和别名列表构建统一正则匹配模式"""
    primary = primary.strip()
    alias_bodies = [p.strip().lstrip("/") for p in aliases if p and p.strip()]
    all_bodies = [primary.lstrip("/")] + alias_bodies
    escaped = [re.escape(b) for b in all_bodies if b]
    if not escaped:
        escaped = ["tarot"]
    names_part = "|".join(escaped)
    return r"^/(?:" + names_part + r")(?:\s+(?P<count>\d+))?(?:\s+(?P<question>.+))?\s*$"


_COMMAND_CONFIG = _get_command_prefixes(
    _load_config().get("commands", {}).get("tarot", {})
)
_COMMAND_NAME = _COMMAND_CONFIG[0].lstrip("/") if _COMMAND_CONFIG else "tarot"
_COMMAND_ALIASES = [cmd.strip() for cmd in _COMMAND_CONFIG[1:] if cmd and cmd.strip()]
_COMMAND_PATTERN = _build_command_pattern(_COMMAND_CONFIG[0], _COMMAND_ALIASES)



def _pick_card(major_only: bool = False) -> dict:
    """
    随机抽取一张牌，并随机决定正位/逆位。
    当 major_only=True 时，仅从大阿卡纳（22 张）中抽取。
    返回：{
        "card": 牌数据,
        "is_upright": bool,
        "position": "正位" | "逆位",
        "interpretation": str,
    }
    """
    pool = MAJOR_ARCANA if major_only else ALL_CARDS
    card = random.choice(pool)
    is_upright = random.choice([True, False])
    position = "正位" if is_upright else "逆位"
    interpretation = card["upright"] if is_upright else card["reversed"]
    return {
        "card": card,
        "is_upright": is_upright,
        "position": position,
        "interpretation": interpretation,
    }


def _format_card_line(result: dict, index: int = 0) -> str:
    """将单张牌格式化为一行文字"""
    card = result["card"]
    prefix = f"第 {index} 张：" if index > 0 else ""
    suit_info = f"【{card['suit_name']}】" if card.get("suit_name") else "【大阿卡纳】"
    element_info = f"（{card['element']}元素）" if card.get("element") else ""
    return (
        f"{prefix}{suit_info}{card['name']}（{card['name_en']}）{element_info}\n"
        f"  位置：{result['position']}\n"
        f"  牌意：{result['interpretation']}\n"
    )


def _card_to_jpg_filename(name_en: str) -> str:
    """将牌英文名转为 JPG 文件名，如 'The Fool' → 'the-fool.jpg'"""
    name = name_en.lower().replace(" ", "-")
    # 去掉特殊字符
    name = "".join(c for c in name if c.isalnum() or c == "-")
    while "--" in name:
        name = name.replace("--", "-")
    return name.strip("-") + ".jpg"


class TarotPlugin(MaiBotPlugin):
    """塔罗牌占卜插件"""

    def __init__(self):
        super().__init__()
        self._config = _load_config()
        self._ai_config = self._config.get("ai", {})
        self._cmd_config = self._config.get("commands", {}).get("tarot", {})
        self._image_config = self._config.get("image_output", {})

    async def on_load(self) -> None:
        self.ctx.logger.info("塔罗牌插件已加载，共 %d 张牌", len(ALL_CARDS))

    async def on_unload(self) -> None:
        self.ctx.logger.info("塔罗牌插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        self.ctx.logger.info("插件配置已更新: version=%s", version)
        self._config = _load_config()
        self._ai_config = self._config.get("ai", {})
        self._cmd_config = self._config.get("commands", {}).get("tarot", {})
        self._image_config = self._config.get("image_output", {})

    # ──────────── 核心抽牌逻辑 ────────────

    async def _draw_single(self, stream_id: str, question: str = "") -> str:
        """单张牌占卜 - 仅抽取大阿卡纳"""
        result = _pick_card(major_only=True)
        card = result["card"]

        suit_info = f"【{card['suit_name']}】" if card.get("suit_name") else "【大阿卡纳】"
        element_info = f"（{card['element']}元素）" if card.get("element") else ""
        question_part = f"占卜问题：{question}\n" if question else ""

        message = (
            f"🔮 塔罗牌占卜 — 单张抽牌\n"
            f"{question_part}"
            f"━━━━━━━━━━━━━━━━\n"
            f"{suit_info}{card['name']}（{card['name_en']}）{element_info}\n"
            f"位置：{result['position']}\n"
            f"牌意：{result['interpretation']}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"解读：\n"
            f"这张 {card['name']} 以{result['position']}位出现，"
            f"预示著 {result['interpretation']}。\n"
            f"请结合自身情况思考其含义。"
        )

        await self.ctx.send.text(message, stream_id)

        # 仅单卡时发送图片
        if self._image_config.get("enabled", False):
            await self._send_image([result], stream_id)

        return message

    async def _draw_three(self, stream_id: str, question: str = "") -> str:
        """三张牌占卜 - 使用 AI 解读"""
        results = [_pick_card() for _ in range(3)]
        aspects = ["积极的方面", "消极的方面", "中性的方面"]

        # 构建牌面概览
        question_part = f"占卜问题：{question}\n" if question else ""
        overview = f"🔮 塔罗牌占卜 — 三张牌阵\n{question_part}━━━━━━━━━━━━━━━━\n"
        for i, r in enumerate(results, 1):
            card = r["card"]
            suit_info = f"【{card['suit_name']}】" if card.get("suit_name") else "【大阿卡纳】"
            overview += f"第 {i} 张：{suit_info}{card['name']} · {r['position']}\n"
            overview += f"  牌意：{r['interpretation']}\n"
        overview += "━━━━━━━━━━━━━━━━\n"

        await self.ctx.send.text(overview, stream_id)

        # AI 解读
        if self._ai_config.get("enabled", True):
            interpretation = await self._ai_interpret(results, aspects, question)
            await self.ctx.send.text("🤖 AI 塔罗解读：\n" + interpretation, stream_id)
        else:
            # 无 AI 时直接输出牌面含义
            fallback = "牌面解读（AI未启用）：\n"
            for i, (r, aspect) in enumerate(zip(results, aspects), 1):
                fallback += f"\n【{aspect}】第 {i} 张：{r['card']['name']}（{r['position']}）\n"
                fallback += f"  {r['interpretation']}\n"
            await self.ctx.send.text(fallback, stream_id)

        return overview

    async def _ai_interpret(self, results: list, aspects: list, question: str = "") -> str:
        """调用 AI 对三张牌进行解读"""
        # 构建提示词
        cards_desc = ""
        for i, (r, aspect) in enumerate(zip(results, aspects), 1):
            card = r["card"]
            suit_info = card.get("suit_name", "大阿卡纳")
            cards_desc += (
                f"第{i}张（{aspect}）：{suit_info} {card['name']}（{card['name_en']}）\n"
                f"  位置：{r['position']}\n"
                f"  牌意：{r['interpretation']}\n"
            )

        question_part = f"用户询问的问题：{question}\n" if question else ""
        prompt = (
            f"用户抽到了以下三张塔罗牌，请按「积极的方面」「消极的方面」「中性的方面」进行解读。\n"
            f"{question_part}"
            f"\n{cards_desc}\n"
            f"请依次对每张牌进行专业解读，每张牌约 100-200 字。"
            f"{'请结合用户询问的问题进行针对性解读。' if question else ''}"
        )

        system_prompt = self._ai_config.get(
            "system_prompt",
            "你是一位专业的塔罗牌占卜师，请根据用户抽到的塔罗牌进行解读。"
        )

        temperature = self._ai_config.get("temperature", 0.7)
        max_tokens = self._ai_config.get("max_tokens", 800)

        # 读取模型名称，默认使用 replyer 模型
        model = self._ai_config.get("model", "replyer") or "replyer"

        try:
            # 使用 replyer 模型进行塔罗牌解读
            result = await self.ctx.llm.generate(
                prompt=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if result.get("success"):
                response = result["response"]
                # 尝试结构化输出
                return self._format_ai_response(response, results, aspects)
            else:
                return "⚠️ AI 解读暂时不可用，请稍后再试。"
        except Exception as e:
            self.ctx.logger.error("AI 解读失败: %s", str(e))
            return "⚠️ AI 解读服务异常，已展示牌面基础含义。请查看上方牌面信息。"

    def _format_ai_response(self, response: str, results: list, aspects: list) -> str:
        """格式化 AI 回复，确保结构清晰"""
        # 如果 AI 已按格式回复，直接返回
        if any(aspect in response for aspect in aspects):
            return response

        # 否则手动包装
        formatted = ""
        for i, (r, aspect) in enumerate(zip(results, aspects), 1):
            formatted += f"\n【{aspect}】\n"
            formatted += f"牌面：{r['card']['name']}（{r['position']}）\n"
            formatted += f"解读：{r['interpretation']}\n"
        return formatted

    # ──────────── 图片输出（JPG 素材） ────────────

    async def _send_image(self, results: list, stream_id: str) -> None:
        """读取 JPG 牌面素材并发送图片（base64 经 RPC 作为 image_base64 参数传递）"""
        try:
            assets_dir = _get_plugin_dir() / self._image_config.get("assets_dir", "assets/cards")

            for r in results:
                jpg_name = _card_to_jpg_filename(r["card"]["name_en"])
                jpg_path = assets_dir / jpg_name
                if not jpg_path.exists():
                    self.ctx.logger.warning("JPG 素材不存在: %s", jpg_path)
                    continue
                jpg_data = jpg_path.read_bytes()
                image_base64 = base64.b64encode(jpg_data).decode("ascii")
                ok = await self.ctx.send.image(image_base64, stream_id)
                if ok:
                    self.ctx.logger.info("已发送 JPG 牌面图片: %s", jpg_name)
                else:
                    self.ctx.logger.warning("图片发送失败（Host 拒绝）: %s", jpg_name)

        except Exception as e:
            self.ctx.logger.warning("图片输出失败: %s", str(e))

    # ──────────── Command 组件 ────────────

    @Command(_COMMAND_NAME, pattern=_COMMAND_PATTERN, aliases=_COMMAND_ALIASES)
    async def handle_tarot(self, **kwargs):
        """处理塔罗牌占卜命令"""
        stream_id = kwargs["stream_id"]
        matched = kwargs.get("matched_groups") or {}
        count_str = (matched.get("count") or "").strip()
        question = (matched.get("question") or "").strip()

        # 解析数量
        if count_str:
            try:
                count = int(count_str)
            except ValueError:
                await self.ctx.send.text(
                    "⚠️ 参数错误，请使用 "
                    + "、".join(_COMMAND_CONFIG)
                    + "（默认1张）、<指令> 1（单张）或 <指令> 3（三张牌阵）",
                    stream_id,
                )
        else:
            count = 1  # 默认单张

        if count == 1:
            msg = await self._draw_single(stream_id, question)
            return True, msg, 1
        elif count == 3:
            msg = await self._draw_three(stream_id, question)
            return True, msg, 1
        else:
            await self.ctx.send.text(
                "⚠️ 目前仅支持 1 张（单牌解读）或 3 张（三牌阵解读），请重新输入。",
                stream_id,
            )
            return True, "参数超出范围", 1


def create_plugin():
    return TarotPlugin()
