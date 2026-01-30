"""A 股市场数据工具

为 Agent 提供北向资金和龙虎榜数据的 LangChain 工具封装。
集成 north_money_service 和 lhb_service 的数据能力。
"""

import asyncio
from langchain_core.tools import tool
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


def _run_async(coro):
    """同步执行异步函数"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@tool
def get_north_money_summary() -> str:
    """获取北向资金概览

    Returns:
        北向资金今日流向、TOP 净买入/卖出股票、近期趋势
    """
    try:
        from services.north_money_service import north_money_service
        summary = _run_async(north_money_service.get_summary())

        output_lines = ["## 北向资金概览\n"]

        # 今日流向
        output_lines.append("### 今日资金流向")
        output_lines.append(f"- **沪股通**: {summary.today.sh_connect:.2f} 亿元")
        output_lines.append(f"- **深股通**: {summary.today.sz_connect:.2f} 亿元")
        output_lines.append(f"- **北向合计**: {summary.today.total:.2f} 亿元")
        output_lines.append(f"- **市场情绪**: {summary.today.market_sentiment}\n")

        # 本周趋势
        output_lines.append(f"### 本周趋势: {summary.trend}")
        output_lines.append(f"- 本周累计: {summary.week_total:.2f} 亿元\n")

        # TOP 净买入
        if summary.top_buys:
            output_lines.append("### 北向净买入 TOP 5")
            for i, stock in enumerate(summary.top_buys[:5], 1):
                output_lines.append(
                    f"{i}. **{stock.name}** ({stock.symbol}): "
                    f"净买入 {stock.net_buy:.2f} 亿元，持股占比 {stock.holding_ratio:.2f}%"
                )
            output_lines.append("")

        # TOP 净卖出
        if summary.top_sells:
            output_lines.append("### 北向净卖出 TOP 5")
            for i, stock in enumerate(summary.top_sells[:5], 1):
                output_lines.append(
                    f"{i}. **{stock.name}** ({stock.symbol}): "
                    f"净卖出 {abs(stock.net_buy):.2f} 亿元"
                )

        return "\n".join(output_lines)

    except Exception as e:
        logger.warning("Failed to get north money summary", error=str(e))
        return f"获取北向资金数据失败: {str(e)}"


@tool
def get_stock_north_holding(symbol: str) -> str:
    """获取个股北向资金持仓变化

    Args:
        symbol: 股票代码（如 600519.SH、000001.SZ）

    Returns:
        该股票的北向资金持仓情况和变化
    """
    try:
        from services.north_money_service import north_money_service
        holding = _run_async(north_money_service.get_stock_north_holding(symbol))

        if not holding:
            return f"未找到 {symbol} 的北向持仓数据（可能不在陆股通标的范围内）"

        output_lines = [f"## {holding.name} ({symbol}) 北向持仓\n"]
        output_lines.append(f"- **持股数量**: {holding.holding_shares:,} 股")
        output_lines.append(f"- **持股市值**: {holding.holding_value:.2f} 亿元")
        output_lines.append(f"- **持股占比**: {holding.holding_ratio:.2f}%")
        output_lines.append(f"- **今日增持**: {holding.change_shares:,} 股")
        output_lines.append(f"- **增持比例**: {holding.change_ratio:+.2f}%")
        output_lines.append(f"- **当前排名**: 第 {holding.rank} 名")

        # 信号解读
        if holding.change_ratio > 1:
            signal = "⬆️ 北向资金大幅加仓，看多信号"
        elif holding.change_ratio > 0:
            signal = "📈 北向资金小幅加仓"
        elif holding.change_ratio > -1:
            signal = "📉 北向资金小幅减仓"
        else:
            signal = "⬇️ 北向资金大幅减仓，看空信号"

        output_lines.append(f"\n**信号解读**: {signal}")

        return "\n".join(output_lines)

    except Exception as e:
        logger.warning("Failed to get stock north holding", symbol=symbol, error=str(e))
        return f"获取 {symbol} 北向持仓失败: {str(e)}"


@tool
def get_lhb_summary() -> str:
    """获取龙虎榜概览

    Returns:
        今日龙虎榜统计、TOP 净买入/卖出股票、活跃游资
    """
    try:
        from services.lhb_service import lhb_service
        summary = _run_async(lhb_service.get_summary())

        output_lines = [f"## 龙虎榜概览 ({summary.date})\n"]

        # 整体统计
        output_lines.append("### 市场统计")
        output_lines.append(f"- **上榜股票数**: {summary.total_stocks} 只")
        output_lines.append(f"- **龙虎榜净买入**: {summary.total_net_buy:.2f} 亿元")
        output_lines.append(f"- **机构净买入**: {summary.institution_net_buy:.2f} 亿元\n")

        # TOP 净买入
        if summary.top_buys:
            output_lines.append("### 净买入 TOP 5")
            for i, stock in enumerate(summary.top_buys[:5], 1):
                inst_tag = "🏛️机构" if stock.institution_net > 0 else ""
                hot_money_tag = "🔥游资" if stock.hot_money_involved else ""
                output_lines.append(
                    f"{i}. **{stock.name}** ({stock.symbol}) "
                    f"涨幅{stock.change_percent:+.2f}%，"
                    f"净买入 {stock.lhb_net_buy/10000:.2f} 亿元 "
                    f"{inst_tag}{hot_money_tag}"
                )
            output_lines.append("")

        # TOP 净卖出
        if summary.top_sells:
            output_lines.append("### 净卖出 TOP 5")
            for i, stock in enumerate(summary.top_sells[:5], 1):
                if stock.lhb_net_buy >= 0:
                    continue
                output_lines.append(
                    f"{i}. **{stock.name}** ({stock.symbol}) "
                    f"涨幅{stock.change_percent:+.2f}%，"
                    f"净卖出 {abs(stock.lhb_net_buy)/10000:.2f} 亿元"
                )
            output_lines.append("")

        # 活跃游资
        if summary.hot_money_active:
            output_lines.append("### 活跃知名游资")
            for seat in summary.hot_money_active[:5]:
                stocks_str = ", ".join(
                    f"{s['name']}({s['action']})"
                    for s in seat.recent_stocks[:3]
                )
                output_lines.append(
                    f"- **{seat.alias}** ({seat.style}): {stocks_str}"
                )

        return "\n".join(output_lines)

    except Exception as e:
        logger.warning("Failed to get LHB summary", error=str(e))
        return f"获取龙虎榜数据失败: {str(e)}"


@tool
def get_stock_lhb_history(symbol: str) -> str:
    """获取个股龙虎榜历史

    Args:
        symbol: 股票代码（如 600519.SH、000001.SZ）

    Returns:
        该股票近期龙虎榜上榜记录
    """
    try:
        from services.lhb_service import lhb_service
        history = _run_async(lhb_service.get_stock_lhb_history(symbol, days=30))

        if not history:
            return f"{symbol} 近 30 日无龙虎榜上榜记录"

        output_lines = [f"## {symbol} 龙虎榜历史（近 30 日）\n"]

        for record in history[:10]:  # 最多显示 10 条
            inst_signal = "🏛️机构买入" if record.institution_net > 0 else "🏛️机构卖出" if record.institution_net < 0 else ""
            output_lines.append(
                f"- **{record.date}**: {record.reason}，"
                f"净买入 {record.net_buy/10000:.2f} 亿元 {inst_signal}"
            )

        # 统计
        total_net = sum(r.net_buy for r in history)
        inst_total = sum(r.institution_net for r in history)
        output_lines.append(f"\n**近期累计**: 龙虎榜净买入 {total_net/10000:.2f} 亿元，机构净买入 {inst_total/10000:.2f} 亿元")

        # 频率分析
        if len(history) >= 3:
            output_lines.append(f"\n⚠️ 该股近期频繁上榜（{len(history)} 次），波动较大，注意风险")

        return "\n".join(output_lines)

    except Exception as e:
        logger.warning("Failed to get stock LHB history", symbol=symbol, error=str(e))
        return f"获取 {symbol} 龙虎榜历史失败: {str(e)}"


@tool
def get_china_flow_analysis(symbol: str) -> str:
    """综合分析个股的资金流向（北向资金 + 龙虎榜）

    Args:
        symbol: 股票代码（如 600519.SH、000001.SZ）

    Returns:
        该股票的综合资金流向分析
    """
    try:
        from services.north_money_service import north_money_service
        from services.lhb_service import lhb_service

        # 并行获取数据
        north_holding = _run_async(north_money_service.get_stock_north_holding(symbol))
        lhb_history = _run_async(lhb_service.get_stock_lhb_history(symbol, days=30))

        output_lines = [f"## {symbol} 综合资金流向分析\n"]

        # 北向资金部分
        output_lines.append("### 北向资金")
        if north_holding:
            direction = "加仓" if north_holding.change_ratio > 0 else "减仓"
            output_lines.append(f"- 持股市值: {north_holding.holding_value:.2f} 亿元")
            output_lines.append(f"- 持股占比: {north_holding.holding_ratio:.2f}%")
            output_lines.append(f"- 今日变化: {direction} {abs(north_holding.change_ratio):.2f}%")
            north_signal = 1 if north_holding.change_ratio > 0.5 else (-1 if north_holding.change_ratio < -0.5 else 0)
        else:
            output_lines.append("- 该股不在陆股通标的范围内")
            north_signal = 0

        output_lines.append("")

        # 龙虎榜部分
        output_lines.append("### 龙虎榜")
        if lhb_history:
            recent_net = sum(r.net_buy for r in lhb_history)
            inst_net = sum(r.institution_net for r in lhb_history)
            output_lines.append(f"- 近 30 日上榜: {len(lhb_history)} 次")
            output_lines.append(f"- 龙虎榜累计净买入: {recent_net/10000:.2f} 亿元")
            output_lines.append(f"- 机构累计净买入: {inst_net/10000:.2f} 亿元")
            lhb_signal = 1 if recent_net > 0 and inst_net > 0 else (-1 if recent_net < 0 and inst_net < 0 else 0)
        else:
            output_lines.append("- 近 30 日无龙虎榜记录")
            lhb_signal = 0

        output_lines.append("")

        # 综合研判
        output_lines.append("### 综合研判")
        total_signal = north_signal + lhb_signal

        if total_signal >= 2:
            verdict = "⬆️ **强烈看多**：北向资金和龙虎榜双重加持，资金面强势"
        elif total_signal == 1:
            verdict = "📈 **偏多**：资金面整体向好"
        elif total_signal == 0:
            verdict = "➡️ **中性**：资金面无明显方向"
        elif total_signal == -1:
            verdict = "📉 **偏空**：资金面整体偏弱"
        else:
            verdict = "⬇️ **强烈看空**：北向资金和龙虎榜双重减持，资金面疲软"

        output_lines.append(verdict)

        return "\n".join(output_lines)

    except Exception as e:
        logger.warning("Failed to analyze china flow", symbol=symbol, error=str(e))
        return f"分析 {symbol} 资金流向失败: {str(e)}"


@tool
def get_sector_rotation_analysis() -> str:
    """获取北向资金板块轮动分析

    分析北向资金在不同板块间的流动，识别轮动模式和投资机会。

    Returns:
        板块轮动分析报告，包括：
        - 各板块资金流向
        - 流入/流出 TOP 板块
        - 轮动模式判断（防御/进攻/混合）
        - 投资建议
    """
    try:
        from services.north_money_service import north_money_service

        # 获取板块流向和轮动信号
        sector_flows = _run_async(north_money_service.get_sector_flow())
        rotation_signal = _run_async(north_money_service.get_sector_rotation_signal())

        output_lines = ["## 北向资金板块轮动分析\n"]

        # 轮动信号
        output_lines.append("### 轮动信号")
        output_lines.append(f"- **轮动模式**: {rotation_signal.rotation_pattern}")
        output_lines.append(f"- **信号强度**: {rotation_signal.signal_strength}/100")
        output_lines.append(f"- **解读**: {rotation_signal.interpretation}\n")

        # 资金流入板块
        if rotation_signal.inflow_sectors:
            output_lines.append("### 资金流入板块 TOP 5")
            inflow_flows = [s for s in sector_flows if s.flow_direction == "inflow"][:5]
            for s in inflow_flows:
                output_lines.append(
                    f"- **{s.sector}**: 净流入 {s.net_buy:.2f} 亿元，{s.stock_count} 只股票"
                )
                if s.top_stocks:
                    output_lines.append(f"  主力标的: {', '.join(s.top_stocks[:3])}")
            output_lines.append("")

        # 资金流出板块
        if rotation_signal.outflow_sectors:
            output_lines.append("### 资金流出板块 TOP 5")
            outflow_flows = [s for s in sector_flows if s.flow_direction == "outflow"][:5]
            for s in outflow_flows:
                output_lines.append(
                    f"- **{s.sector}**: 净流出 {abs(s.net_buy):.2f} 亿元，{s.stock_count} 只股票"
                )
            output_lines.append("")

        # 投资建议
        output_lines.append("### 投资建议")
        if rotation_signal.rotation_pattern == "defensive":
            output_lines.append("- 🛡️ 市场偏好防御，可关注银行、食品饮料、公用事业等低估值板块")
            output_lines.append("- 🔻 减持高估值成长股，控制整体仓位")
        elif rotation_signal.rotation_pattern == "aggressive":
            output_lines.append("- 🚀 市场风险偏好上升，可适当加仓电子、计算机、新能源等成长板块")
            output_lines.append("- ⚡ 关注北向重仓的行业龙头")
        elif rotation_signal.rotation_pattern == "broad_inflow":
            output_lines.append("- ✅ 资金全面流入，市场做多情绪浓厚")
            output_lines.append("- 📈 可维持或增加多头敞口")
        elif rotation_signal.rotation_pattern == "broad_outflow":
            output_lines.append("- ⚠️ 资金全面流出，建议降低仓位")
            output_lines.append("- 💰 保留现金等待市场企稳")
        else:
            output_lines.append("- 🔄 板块分化明显，建议精选个股")
            output_lines.append("- 🎯 关注北向持续加仓的细分龙头")

        return "\n".join(output_lines)

    except Exception as e:
        logger.warning("Failed to get sector rotation analysis", error=str(e))
        return f"获取板块轮动分析失败: {str(e)}"


@tool
def get_hot_money_profiles() -> str:
    """获取知名游资席位画像列表

    Returns:
        所有知名游资的画像信息，包括层级、操作风格、偏好板块和近期操作
    """
    try:
        from services.lhb_service import lhb_service
        profiles = _run_async(lhb_service.get_all_hot_money_profiles())

        if not profiles:
            return "暂无知名游资画像数据"

        output_lines = ["## 知名游资席位画像\n"]

        for p in profiles:
            output_lines.append(f"### {p.alias}（{p.tier}）")
            output_lines.append(f"- **席位**: {p.seat_name}")
            output_lines.append(f"- **风格**: {p.style}")
            output_lines.append(f"- **风格标签**: {', '.join(p.style_tags)}")
            output_lines.append(f"- **偏好板块**: {', '.join(p.preferred_sectors)}")
            output_lines.append(f"- **偏好市值**: {p.preferred_market_cap}")

            if p.total_appearances > 0:
                output_lines.append(f"- **近期上榜**: {p.total_appearances} 次")
                output_lines.append(f"- **买入总额**: {p.total_buy_amount:.2f} 亿元")
                output_lines.append(f"- **卖出总额**: {p.total_sell_amount:.2f} 亿元")

            if p.recent_operations:
                output_lines.append("- **近期操作**:")
                for op in p.recent_operations[:3]:
                    output_lines.append(
                        f"  - {op['name']}({op['symbol']}): "
                        f"{op['action']} {op['amount']:.0f}万元"
                    )
            output_lines.append("")

        return "\n".join(output_lines)

    except Exception as e:
        logger.warning("Failed to get hot money profiles", error=str(e))
        return f"获取游资画像失败: {str(e)}"


@tool
def get_hot_money_movement() -> str:
    """获取游资动向信号

    分析多个知名游资的同向操作，识别共识买入/卖出信号。

    Returns:
        游资动向信号报告，包括信号类型、涉及席位和目标股票
    """
    try:
        from services.lhb_service import lhb_service
        signal = _run_async(lhb_service.get_hot_money_movement_signal())

        output_lines = [f"## 游资动向信号 ({signal.date})\n"]

        # 信号概览
        signal_emoji = {
            "consensus_buy": "🟢",
            "consensus_sell": "🔴",
            "divergence": "🟡",
            "new_entry": "🔵",
            "no_activity": "⚪",
        }
        emoji = signal_emoji.get(signal.signal_type, "⚪")

        output_lines.append(f"### {emoji} 信号类型: {signal.signal_type}")
        output_lines.append(f"- **信号强度**: {signal.signal_strength}/100")
        output_lines.append(f"- **解读**: {signal.interpretation}\n")

        # 涉及席位
        if signal.involved_seats:
            output_lines.append("### 涉及游资")
            output_lines.append(f"- {', '.join(signal.involved_seats)}\n")

        # 目标股票
        if signal.target_stocks:
            output_lines.append("### 目标股票")
            for stock in signal.target_stocks:
                seats_str = ", ".join(stock.get("involved_seats", []))
                output_lines.append(
                    f"- **{stock['name']}** ({stock['symbol']}): "
                    f"{stock['action']}，涨跌幅 {stock.get('change_percent', 0):+.2f}%"
                    f"（{seats_str}）"
                )

        return "\n".join(output_lines)

    except Exception as e:
        logger.warning("Failed to get hot money movement", error=str(e))
        return f"获取游资动向信号失败: {str(e)}"


@tool
def get_unlock_overview() -> str:
    """获取市场解禁概览

    Returns:
        市场解禁概览，包括本周/本月解禁市值、高压力股票、趋势判断
    """
    try:
        from services.unlock_service import unlock_service
        overview = _run_async(unlock_service.get_market_unlock_overview())

        output_lines = [f"## 市场解禁概览 ({overview.date})\n"]

        # 解禁市值统计
        output_lines.append("### 解禁市值统计")
        output_lines.append(f"- **本周解禁**: {overview.this_week_value:.1f} 亿元")
        output_lines.append(f"- **下周解禁**: {overview.next_week_value:.1f} 亿元")
        output_lines.append(f"- **本月解禁**: {overview.this_month_value:.1f} 亿元")
        output_lines.append(f"- **趋势**: {overview.trend}\n")

        # 市场影响
        output_lines.append("### 市场影响评估")
        output_lines.append(f"{overview.market_impact}\n")

        # 高压力股票
        if overview.high_pressure_stocks:
            output_lines.append("### 高压力解禁股 TOP 10")
            for stock in overview.high_pressure_stocks[:10]:
                output_lines.append(
                    f"- **{stock.name}** ({stock.symbol}): "
                    f"解禁 {stock.unlock_value:.1f} 亿元，"
                    f"占总股本 {stock.unlock_ratio:.1f}%，"
                    f"解禁日 {stock.unlock_date}"
                )

        return "\n".join(output_lines)

    except Exception as e:
        logger.warning("Failed to get unlock overview", error=str(e))
        return f"获取解禁概览失败: {str(e)}"


@tool
def get_stock_unlock_pressure(symbol: str) -> str:
    """获取个股解禁压力评估

    Args:
        symbol: 股票代码（如 600519.SH、000001.SZ）

    Returns:
        该股票的解禁压力评估报告
    """
    try:
        from services.unlock_service import unlock_service
        pressure = _run_async(unlock_service.get_unlock_pressure(symbol))

        # 压力等级图标
        level_emoji = {
            "低": "🟢",
            "中": "🟡",
            "高": "🟠",
            "极高": "🔴",
        }
        emoji = level_emoji.get(pressure.pressure_level, "⚪")

        output_lines = [f"## {pressure.name} ({symbol}) 解禁压力评估\n"]

        # 压力评分
        output_lines.append(f"### {emoji} 压力等级: {pressure.pressure_level}")
        output_lines.append(f"- **压力评分**: {pressure.pressure_score}/100")
        output_lines.append(f"- **未来30日解禁市值**: {pressure.total_unlock_value:.2f} 亿元")
        output_lines.append(f"- **解禁占流通比**: {pressure.total_unlock_ratio:.2f}%\n")

        # 风险因素
        if pressure.risk_factors:
            output_lines.append("### 风险因素")
            for factor in pressure.risk_factors:
                output_lines.append(f"- ⚠️ {factor}")
            output_lines.append("")

        # 解禁计划
        if pressure.upcoming_unlocks:
            output_lines.append("### 未来30日解禁计划")
            for u in pressure.upcoming_unlocks[:5]:
                output_lines.append(
                    f"- **{u.unlock_date}**: {u.unlock_shares:.0f}万股，"
                    f"市值约 {u.unlock_value:.2f} 亿元 ({u.unlock_type})"
                )
            output_lines.append("")

        # 操作建议
        output_lines.append("### 操作建议")
        output_lines.append(pressure.suggestion)

        return "\n".join(output_lines)

    except Exception as e:
        logger.warning("Failed to get stock unlock pressure", symbol=symbol, error=str(e))
        return f"获取 {symbol} 解禁压力评估失败: {str(e)}"


# 导出所有工具
CHINA_MARKET_TOOLS = [
    get_north_money_summary,
    get_stock_north_holding,
    get_lhb_summary,
    get_stock_lhb_history,
    get_china_flow_analysis,
    get_sector_rotation_analysis,
    get_hot_money_profiles,
    get_hot_money_movement,
    get_unlock_overview,
    get_stock_unlock_pressure,
]
