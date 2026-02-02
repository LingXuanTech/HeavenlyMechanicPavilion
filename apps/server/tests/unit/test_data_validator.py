"""
DataValidator 单元测试

覆盖:
1. 数据质量等级枚举
2. 字段验证结果
3. 验证结果类
4. 跨源数据验证
5. 价格数据验证
6. 质量等级计算
7. 上下文生成
"""
import pytest
from dataclasses import asdict

from services.data_validator import (
    DataValidator,
    DataQualityLevel,
    FieldValidation,
    ValidationResult,
    data_validator,
)


# =============================================================================
# 枚举测试
# =============================================================================

class TestDataQualityLevel:
    """数据质量等级枚举测试"""

    def test_quality_level_values(self):
        """质量等级枚举值"""
        assert DataQualityLevel.HIGH.value == "high"
        assert DataQualityLevel.MEDIUM.value == "medium"
        assert DataQualityLevel.LOW.value == "low"
        assert DataQualityLevel.SINGLE_SOURCE.value == "single_source"
        assert DataQualityLevel.UNAVAILABLE.value == "unavailable"


# =============================================================================
# FieldValidation 测试
# =============================================================================

class TestFieldValidation:
    """字段验证结果测试"""

    def test_field_validation_creation(self):
        """创建 FieldValidation"""
        field = FieldValidation(
            field_name="pe_ratio",
            primary_value=15.5,
            fallback_value=16.0,
            deviation_pct=3.13,
            quality=DataQualityLevel.HIGH,
            note="Values within tolerance",
        )

        assert field.field_name == "pe_ratio"
        assert field.primary_value == 15.5
        assert field.deviation_pct == 3.13
        assert field.quality == DataQualityLevel.HIGH

    def test_field_validation_defaults(self):
        """FieldValidation 默认值"""
        field = FieldValidation(
            field_name="eps",
            primary_value=2.5,
        )

        assert field.fallback_value is None
        assert field.deviation_pct is None
        assert field.quality == DataQualityLevel.SINGLE_SOURCE
        assert field.note == ""


# =============================================================================
# ValidationResult 测试
# =============================================================================

class TestValidationResult:
    """验证结果测试"""

    def test_validation_result_creation(self):
        """创建 ValidationResult"""
        result = ValidationResult(
            symbol="AAPL",
            overall_quality=DataQualityLevel.HIGH,
            field_results=[],
            warnings=[],
            data_quality_context="",
        )

        assert result.symbol == "AAPL"
        assert result.overall_quality == DataQualityLevel.HIGH

    def test_has_warnings_false(self):
        """无警告"""
        result = ValidationResult(symbol="AAPL", warnings=[])
        assert result.has_warnings() is False

    def test_has_warnings_true(self):
        """有警告"""
        result = ValidationResult(symbol="AAPL", warnings=["Warning 1"])
        assert result.has_warnings() is True

    def test_get_low_quality_fields(self):
        """获取低质量字段"""
        result = ValidationResult(
            symbol="AAPL",
            field_results=[
                FieldValidation(field_name="pe_ratio", primary_value=15, quality=DataQualityLevel.HIGH),
                FieldValidation(field_name="eps", primary_value=2, quality=DataQualityLevel.LOW),
                FieldValidation(field_name="market_cap", primary_value=1000, quality=DataQualityLevel.LOW),
            ],
        )

        low_fields = result.get_low_quality_fields()

        assert len(low_fields) == 2
        assert "eps" in low_fields
        assert "market_cap" in low_fields

    def test_get_low_quality_fields_empty(self):
        """无低质量字段"""
        result = ValidationResult(
            symbol="AAPL",
            field_results=[
                FieldValidation(field_name="pe_ratio", primary_value=15, quality=DataQualityLevel.HIGH),
            ],
        )

        low_fields = result.get_low_quality_fields()
        assert low_fields == []


# =============================================================================
# DataValidator 辅助方法测试
# =============================================================================

class TestDataValidatorHelpers:
    """DataValidator 辅助方法测试"""

    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        return DataValidator()

    def test_is_numeric_int(self, validator):
        """整数是数值"""
        assert validator._is_numeric(42) is True

    def test_is_numeric_float(self, validator):
        """浮点数是数值"""
        assert validator._is_numeric(3.14) is True

    def test_is_numeric_string_number(self, validator):
        """数字字符串是数值"""
        assert validator._is_numeric("123.45") is True

    def test_is_numeric_none(self, validator):
        """None 不是数值"""
        assert validator._is_numeric(None) is False

    def test_is_numeric_string(self, validator):
        """非数字字符串不是数值"""
        assert validator._is_numeric("hello") is False

    def test_is_numeric_empty_string(self, validator):
        """空字符串不是数值"""
        assert validator._is_numeric("") is False

    def test_is_numeric_list(self, validator):
        """列表不是数值"""
        assert validator._is_numeric([1, 2, 3]) is False


# =============================================================================
# 整体质量计算测试
# =============================================================================

class TestComputeOverallQuality:
    """整体质量计算测试"""

    @pytest.fixture
    def validator(self):
        return DataValidator()

    def test_empty_fields_unavailable(self, validator):
        """空字段列表 = UNAVAILABLE"""
        result = validator._compute_overall_quality([])
        assert result == DataQualityLevel.UNAVAILABLE

    def test_all_single_source(self, validator):
        """全部单一来源 = SINGLE_SOURCE"""
        fields = [
            FieldValidation(field_name="a", primary_value=1, quality=DataQualityLevel.SINGLE_SOURCE),
            FieldValidation(field_name="b", primary_value=2, quality=DataQualityLevel.SINGLE_SOURCE),
        ]
        result = validator._compute_overall_quality(fields)
        assert result == DataQualityLevel.SINGLE_SOURCE

    def test_all_high_quality(self, validator):
        """全部高质量 = HIGH"""
        fields = [
            FieldValidation(field_name="a", primary_value=1, quality=DataQualityLevel.HIGH),
            FieldValidation(field_name="b", primary_value=2, quality=DataQualityLevel.HIGH),
            FieldValidation(field_name="c", primary_value=3, quality=DataQualityLevel.HIGH),
        ]
        result = validator._compute_overall_quality(fields)
        assert result == DataQualityLevel.HIGH

    def test_some_low_quality(self, validator):
        """部分低质量 = MEDIUM"""
        fields = [
            FieldValidation(field_name="a", primary_value=1, quality=DataQualityLevel.HIGH),
            FieldValidation(field_name="b", primary_value=2, quality=DataQualityLevel.LOW),
            FieldValidation(field_name="c", primary_value=3, quality=DataQualityLevel.HIGH),
            FieldValidation(field_name="d", primary_value=4, quality=DataQualityLevel.HIGH),
        ]
        result = validator._compute_overall_quality(fields)
        assert result == DataQualityLevel.MEDIUM

    def test_many_low_quality(self, validator):
        """多数低质量 = LOW"""
        fields = [
            FieldValidation(field_name="a", primary_value=1, quality=DataQualityLevel.LOW),
            FieldValidation(field_name="b", primary_value=2, quality=DataQualityLevel.LOW),
            FieldValidation(field_name="c", primary_value=3, quality=DataQualityLevel.HIGH),
        ]
        result = validator._compute_overall_quality(fields)
        assert result == DataQualityLevel.LOW

    def test_many_medium_quality(self, validator):
        """多数中等质量 = MEDIUM"""
        fields = [
            FieldValidation(field_name="a", primary_value=1, quality=DataQualityLevel.MEDIUM),
            FieldValidation(field_name="b", primary_value=2, quality=DataQualityLevel.MEDIUM),
            FieldValidation(field_name="c", primary_value=3, quality=DataQualityLevel.MEDIUM),
            FieldValidation(field_name="d", primary_value=4, quality=DataQualityLevel.HIGH),
        ]
        result = validator._compute_overall_quality(fields)
        assert result == DataQualityLevel.MEDIUM


# =============================================================================
# 跨源验证测试
# =============================================================================

class TestValidateCrossSource:
    """跨源数据验证测试"""

    @pytest.fixture
    def validator(self):
        return DataValidator()

    def test_validate_identical_data(self, validator):
        """完全相同的数据"""
        primary = {"pe_ratio": 15.0, "eps": 2.5}
        fallback = {"pe_ratio": 15.0, "eps": 2.5}

        result = validator.validate_cross_source("AAPL", primary, fallback)

        assert result.symbol == "AAPL"
        assert result.overall_quality == DataQualityLevel.HIGH
        assert len(result.warnings) == 0

    def test_validate_small_deviation(self, validator):
        """小偏差（在容忍范围内）"""
        primary = {"pe_ratio": 15.0, "eps": 2.5}
        fallback = {"pe_ratio": 15.5, "eps": 2.55}  # ~3% 偏差

        result = validator.validate_cross_source("AAPL", primary, fallback)

        assert result.overall_quality in [DataQualityLevel.HIGH, DataQualityLevel.MEDIUM]
        assert len(result.warnings) == 0

    def test_validate_large_deviation(self, validator):
        """大偏差（超过阈值）"""
        primary = {"pe_ratio": 15.0, "eps": 2.5}
        fallback = {"pe_ratio": 25.0, "eps": 4.0}  # 大偏差

        result = validator.validate_cross_source("AAPL", primary, fallback)

        assert result.overall_quality == DataQualityLevel.LOW
        assert len(result.warnings) > 0

    def test_validate_both_zero(self, validator):
        """两个零值"""
        primary = {"pe_ratio": 0.0}
        fallback = {"pe_ratio": 0.0}

        result = validator.validate_cross_source("AAPL", primary, fallback)

        # 零值应该被视为高质量
        field = next((f for f in result.field_results if f.field_name == "pe_ratio"), None)
        assert field is not None
        assert field.quality == DataQualityLevel.HIGH
        assert field.deviation_pct == 0.0

    def test_validate_primary_only_fields(self, validator):
        """仅主数据源有的字段"""
        primary = {"pe_ratio": 15.0, "forward_pe": 12.0}
        fallback = {"pe_ratio": 15.0}

        result = validator.validate_cross_source(
            "AAPL", primary, fallback, source_names=("yfinance", "akshare")
        )

        # forward_pe 应标记为单一来源
        forward_pe_field = next(
            (f for f in result.field_results if f.field_name == "forward_pe"), None
        )
        assert forward_pe_field is not None
        assert forward_pe_field.quality == DataQualityLevel.SINGLE_SOURCE
        assert "yfinance" in forward_pe_field.note

    def test_validate_non_numeric_skipped(self, validator):
        """非数值字段被跳过"""
        primary = {"pe_ratio": 15.0, "name": "Apple Inc"}
        fallback = {"pe_ratio": 15.0, "name": "Apple"}

        result = validator.validate_cross_source("AAPL", primary, fallback)

        # name 字段不应该在结果中
        name_field = next(
            (f for f in result.field_results if f.field_name == "name"), None
        )
        assert name_field is None

    def test_validate_custom_source_names(self, validator):
        """自定义数据源名称"""
        primary = {"pe_ratio": 15.0}
        fallback = {"pe_ratio": 25.0}

        result = validator.validate_cross_source(
            "AAPL", primary, fallback, source_names=("Yahoo", "AkShare")
        )

        assert len(result.warnings) > 0
        assert "Yahoo" in result.warnings[0]
        assert "AkShare" in result.warnings[0]


# =============================================================================
# 价格数据验证测试
# =============================================================================

class TestValidatePriceData:
    """价格数据验证测试"""

    @pytest.fixture
    def validator(self):
        return DataValidator()

    def test_valid_price_data(self, validator):
        """有效价格数据"""
        prices = [
            {"date": "2026-02-01", "high": 150, "low": 145, "close": 148, "volume": 1000000},
            {"date": "2026-02-02", "high": 152, "low": 147, "close": 151, "volume": 1200000},
        ]

        warnings = validator.validate_price_data("AAPL", prices)

        assert len(warnings) == 0

    def test_high_less_than_low(self, validator):
        """高价低于低价"""
        prices = [
            {"date": "2026-02-01", "high": 145, "low": 150, "close": 148, "volume": 1000000},
        ]

        warnings = validator.validate_price_data("AAPL", prices)

        # 会产生多个警告（high < low 和 close outside range）
        assert len(warnings) >= 1
        assert any("high" in w and "low" in w for w in warnings)

    def test_negative_volume(self, validator):
        """负成交量"""
        prices = [
            {"date": "2026-02-01", "high": 150, "low": 145, "close": 148, "volume": -1000},
        ]

        warnings = validator.validate_price_data("AAPL", prices)

        assert len(warnings) == 1
        assert "negative volume" in warnings[0]

    def test_close_outside_range(self, validator):
        """收盘价超出范围"""
        prices = [
            {"date": "2026-02-01", "high": 150, "low": 145, "close": 160, "volume": 1000000},
        ]

        warnings = validator.validate_price_data("AAPL", prices)

        assert len(warnings) == 1
        assert "outside" in warnings[0]

    def test_multiple_issues(self, validator):
        """多个问题"""
        prices = [
            {"date": "2026-02-01", "high": 140, "low": 150, "close": 145, "volume": -100},
        ]

        warnings = validator.validate_price_data("AAPL", prices)

        assert len(warnings) >= 2

    def test_empty_prices(self, validator):
        """空价格列表"""
        warnings = validator.validate_price_data("AAPL", [])
        assert len(warnings) == 0


# =============================================================================
# 上下文生成测试
# =============================================================================

class TestGenerateContext:
    """上下文生成测试"""

    @pytest.fixture
    def validator(self):
        return DataValidator()

    def test_high_quality_no_context(self, validator):
        """高质量无上下文"""
        result = ValidationResult(
            symbol="AAPL",
            overall_quality=DataQualityLevel.HIGH,
            field_results=[],
            warnings=[],
        )

        context = validator._generate_context(result, ("primary", "fallback"))

        assert context == ""

    def test_low_quality_has_context(self, validator):
        """低质量有上下文"""
        result = ValidationResult(
            symbol="AAPL",
            overall_quality=DataQualityLevel.LOW,
            field_results=[
                FieldValidation(field_name="pe_ratio", primary_value=15, quality=DataQualityLevel.LOW),
            ],
            warnings=["pe_ratio: 偏差过大"],
        )

        context = validator._generate_context(result, ("Yahoo", "AkShare"))

        assert "AAPL" in context
        assert "low" in context.lower()
        assert "pe_ratio" in context
        assert "Yahoo" in context
        assert "AkShare" in context

    def test_context_limits_warnings(self, validator):
        """上下文限制警告数量"""
        warnings = [f"Warning {i}" for i in range(10)]
        result = ValidationResult(
            symbol="AAPL",
            overall_quality=DataQualityLevel.LOW,
            field_results=[],
            warnings=warnings,
        )

        context = validator._generate_context(result, ("primary", "fallback"))

        # 最多显示 5 条警告
        assert "还有 5 条警告" in context


# =============================================================================
# 容忍阈值测试
# =============================================================================

class TestToleranceThresholds:
    """容忍阈值测试"""

    def test_tolerance_values_exist(self):
        """容忍阈值存在"""
        assert "pe_ratio" in DataValidator.TOLERANCE
        assert "eps" in DataValidator.TOLERANCE
        assert "market_cap" in DataValidator.TOLERANCE
        assert "close" in DataValidator.TOLERANCE

    def test_default_tolerance(self):
        """默认容忍阈值"""
        assert DataValidator.DEFAULT_TOLERANCE == 0.15

    def test_price_tolerance_small(self):
        """价格容忍阈值较小"""
        assert DataValidator.TOLERANCE["close"] == 0.02
        assert DataValidator.TOLERANCE["open"] == 0.02

    def test_volume_tolerance_large(self):
        """成交量容忍阈值较大"""
        assert DataValidator.TOLERANCE["volume"] == 0.20


# =============================================================================
# 单例测试
# =============================================================================

class TestDataValidatorSingleton:
    """单例测试"""

    def test_singleton_exists(self):
        """全局单例存在"""
        assert data_validator is not None
        assert isinstance(data_validator, DataValidator)
