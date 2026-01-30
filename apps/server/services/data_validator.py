"""Data Validator Service

跨数据源校验机制，确保多数据源返回数据的一致性。

功能：
- 比较主备数据源的同一指标
- 标记偏差超过阈值的字段
- 生成数据质量标记，注入到 Agent 上下文

使用场景：
- 基本面数据（PE、EPS、市值）：多源交叉验证
- 价格数据：不同时间源间的价差校验
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


class DataQualityLevel(str, Enum):
    """数据质量等级"""
    HIGH = "high"          # 多源一致
    MEDIUM = "medium"      # 存在小偏差但在容忍范围内
    LOW = "low"            # 偏差超过阈值
    SINGLE_SOURCE = "single_source"  # 仅单一数据源
    UNAVAILABLE = "unavailable"      # 数据不可用


@dataclass
class FieldValidation:
    """单个字段的验证结果"""
    field_name: str
    primary_value: Any
    fallback_value: Optional[Any] = None
    deviation_pct: Optional[float] = None
    quality: DataQualityLevel = DataQualityLevel.SINGLE_SOURCE
    note: str = ""


@dataclass
class ValidationResult:
    """完整的验证结果"""
    symbol: str
    overall_quality: DataQualityLevel = DataQualityLevel.HIGH
    field_results: List[FieldValidation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    data_quality_context: str = ""  # 可注入 Agent prompt 的上下文

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def get_low_quality_fields(self) -> List[str]:
        """获取低质量字段列表"""
        return [f.field_name for f in self.field_results if f.quality == DataQualityLevel.LOW]


class DataValidator:
    """数据校验器"""

    # 各字段的容忍偏差阈值（百分比）
    TOLERANCE = {
        # 估值指标
        "pe_ratio": 0.15,            # 15%
        "pe_ttm": 0.15,
        "forward_pe": 0.20,          # 前瞻 PE 允许更大偏差
        "pb_ratio": 0.10,            # 10%
        "ps_ratio": 0.15,

        # 每股数据
        "eps": 0.10,                 # 10%
        "eps_ttm": 0.10,
        "dps": 0.05,                 # 5% (股息更精确)
        "bvps": 0.10,

        # 市值和规模
        "market_cap": 0.05,          # 5% (市值差异应该很小)
        "total_revenue": 0.10,
        "net_income": 0.10,

        # 价格数据
        "close": 0.02,              # 2% (价格差异应很小)
        "open": 0.02,
        "high": 0.02,
        "low": 0.02,
        "volume": 0.20,             # 20% (成交量可能有差异)

        # 财务比率
        "roe": 0.15,
        "roa": 0.15,
        "debt_to_equity": 0.10,
        "current_ratio": 0.10,
        "gross_margin": 0.10,
        "net_margin": 0.10,
    }

    # 默认容忍阈值
    DEFAULT_TOLERANCE = 0.15

    def validate_cross_source(
        self,
        symbol: str,
        primary: Dict[str, Any],
        fallback: Dict[str, Any],
        source_names: Tuple[str, str] = ("primary", "fallback"),
    ) -> ValidationResult:
        """对比两个数据源的数据

        Args:
            symbol: 股票代码
            primary: 主数据源数据
            fallback: 备数据源数据
            source_names: 数据源名称（用于日志）

        Returns:
            ValidationResult
        """
        result = ValidationResult(symbol=symbol)
        warnings = []

        # 收集两个源共有的数值字段
        common_fields = set(primary.keys()) & set(fallback.keys())

        for field_name in common_fields:
            p_val = primary.get(field_name)
            f_val = fallback.get(field_name)

            # 跳过非数值或空值
            if not self._is_numeric(p_val) or not self._is_numeric(f_val):
                continue

            p_num = float(p_val)
            f_num = float(f_val)

            # 跳过零值（避免除零错误）
            if p_num == 0 and f_num == 0:
                result.field_results.append(FieldValidation(
                    field_name=field_name,
                    primary_value=p_num,
                    fallback_value=f_num,
                    deviation_pct=0.0,
                    quality=DataQualityLevel.HIGH,
                ))
                continue

            # 计算偏差百分比
            base = max(abs(p_num), abs(f_num))
            if base == 0:
                deviation = 0.0
            else:
                deviation = abs(p_num - f_num) / base

            tolerance = self.TOLERANCE.get(field_name, self.DEFAULT_TOLERANCE)

            if deviation <= tolerance * 0.5:
                quality = DataQualityLevel.HIGH
            elif deviation <= tolerance:
                quality = DataQualityLevel.MEDIUM
            else:
                quality = DataQualityLevel.LOW
                warnings.append(
                    f"{field_name}: {source_names[0]}={p_num:.4f}, {source_names[1]}={f_num:.4f} "
                    f"(偏差 {deviation*100:.1f}%, 阈值 {tolerance*100:.0f}%)"
                )

            result.field_results.append(FieldValidation(
                field_name=field_name,
                primary_value=p_num,
                fallback_value=f_num,
                deviation_pct=round(deviation * 100, 2),
                quality=quality,
            ))

        # 标记仅在一个源中存在的字段
        primary_only = set(primary.keys()) - set(fallback.keys())
        fallback_only = set(fallback.keys()) - set(primary.keys())

        for f in primary_only:
            if self._is_numeric(primary.get(f)):
                result.field_results.append(FieldValidation(
                    field_name=f,
                    primary_value=primary[f],
                    quality=DataQualityLevel.SINGLE_SOURCE,
                    note=f"Only available from {source_names[0]}",
                ))

        # 计算整体质量
        result.warnings = warnings
        result.overall_quality = self._compute_overall_quality(result.field_results)

        # 生成可注入 Agent 的上下文
        result.data_quality_context = self._generate_context(result, source_names)

        if warnings:
            logger.warning(
                "Data quality issues detected",
                symbol=symbol,
                warning_count=len(warnings),
                overall_quality=result.overall_quality.value,
            )

        return result

    def validate_price_data(
        self,
        symbol: str,
        prices: List[Dict[str, Any]],
    ) -> List[str]:
        """验证价格数据的内部一致性

        检查：
        - high >= low
        - high >= close >= low (不严格，收盘价可能等于最高/最低)
        - volume >= 0
        - 日期连续性

        Args:
            symbol: 股票代码
            prices: 价格数据列表

        Returns:
            警告信息列表
        """
        warnings = []

        for i, price in enumerate(prices):
            date_str = price.get("date", f"index_{i}")
            high = price.get("high", 0)
            low = price.get("low", 0)
            close = price.get("close", 0)
            volume = price.get("volume", 0)

            if high < low:
                warnings.append(f"{date_str}: high({high}) < low({low})")

            if volume < 0:
                warnings.append(f"{date_str}: negative volume({volume})")

            if close > high * 1.01 or close < low * 0.99:
                warnings.append(f"{date_str}: close({close}) outside high-low range [{low}, {high}]")

        return warnings

    def _is_numeric(self, value: Any) -> bool:
        """检查值是否为数值类型"""
        if value is None:
            return False
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            return False

    def _compute_overall_quality(self, fields: List[FieldValidation]) -> DataQualityLevel:
        """计算整体数据质量等级"""
        if not fields:
            return DataQualityLevel.UNAVAILABLE

        quality_values = [f.quality for f in fields if f.quality != DataQualityLevel.SINGLE_SOURCE]

        if not quality_values:
            return DataQualityLevel.SINGLE_SOURCE

        low_count = sum(1 for q in quality_values if q == DataQualityLevel.LOW)
        medium_count = sum(1 for q in quality_values if q == DataQualityLevel.MEDIUM)

        if low_count > len(quality_values) * 0.3:
            return DataQualityLevel.LOW
        elif low_count > 0 or medium_count > len(quality_values) * 0.5:
            return DataQualityLevel.MEDIUM
        else:
            return DataQualityLevel.HIGH

    def _generate_context(
        self,
        result: ValidationResult,
        source_names: Tuple[str, str],
    ) -> str:
        """生成可注入 Agent prompt 的数据质量上下文"""
        if result.overall_quality == DataQualityLevel.HIGH:
            return ""  # 高质量无需额外说明

        lines = [f"⚠️ 数据质量提示 ({result.symbol}):"]
        lines.append(f"整体质量: {result.overall_quality.value}")

        low_fields = result.get_low_quality_fields()
        if low_fields:
            lines.append(f"存在显著偏差的字段: {', '.join(low_fields)}")

        for w in result.warnings[:5]:  # 最多 5 条警告
            lines.append(f"  - {w}")

        if len(result.warnings) > 5:
            lines.append(f"  ... 还有 {len(result.warnings) - 5} 条警告")

        lines.append(f"数据源: {source_names[0]} (主) / {source_names[1]} (备)")
        lines.append("请在分析中考虑数据可靠性。")

        return "\n".join(lines)


# 全局单例
data_validator = DataValidator()
