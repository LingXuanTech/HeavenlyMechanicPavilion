"""配置验证工具 - 运行时配置检查和验证."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config.settings import Settings


class ConfigValidator:
    """配置验证器."""
    
    def __init__(self, settings: Settings):
        """初始化验证器.
        
        Args:
            settings: Settings 实例
        """
        self.settings = settings
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    def validate_all(self) -> bool:
        """执行所有验证检查.
        
        Returns:
            验证是否通过 (无错误)
        """
        self.errors.clear()
        self.warnings.clear()
        self.info.clear()
        
        self._validate_required_fields()
        self._validate_paths()
        self._validate_llm_config()
        self._validate_vendors()
        self._validate_database()
        self._validate_redis()
        self._validate_api_keys()
        self._validate_numeric_ranges()
        
        return len(self.errors) == 0
    
    def _validate_required_fields(self) -> None:
        """验证必需字段."""
        required_fields = {
            "llm_provider": "LLM 提供商",
            "deep_think_llm": "深度思考 LLM 模型",
            "quick_think_llm": "快速思考 LLM 模型",
            "project_dir": "项目目录",
            "data_dir": "数据目录",
            "database_url": "数据库 URL"
        }
        
        for field, name in required_fields.items():
            value = getattr(self.settings, field, None)
            if not value:
                self.errors.append(f"必需字段 '{name}' ({field}) 未设置")
            else:
                self.info.append(f"✓ {name}: {value}")
    
    def _validate_paths(self) -> None:
        """验证路径配置."""
        path_fields = {
            "project_dir": "项目目录",
            "data_dir": "数据目录",
            "results_dir": "结果目录",
            "data_cache_dir": "数据缓存目录"
        }
        
        for field, name in path_fields.items():
            path_str = getattr(self.settings, field, None)
            if not path_str:
                continue
            
            path = Path(path_str)
            
            # 检查路径是否为绝对路径或相对路径
            if not path.is_absolute():
                self.info.append(f"{name} 使用相对路径: {path_str}")
            
            # 检查路径是否存在
            if not path.exists():
                self.warnings.append(
                    f"{name} '{path_str}' 不存在,将在首次使用时自动创建"
                )
            else:
                # 检查是否可写
                if not os.access(path, os.W_OK):
                    self.errors.append(f"{name} '{path_str}' 不可写")
                else:
                    self.info.append(f"✓ {name}: {path_str} (存在且可写)")
    
    def _validate_llm_config(self) -> None:
        """验证 LLM 配置."""
        # 验证 LLM 提供商
        valid_providers = ["openai", "deepseek", "anthropic", "grok"]
        if self.settings.llm_provider not in valid_providers:
            self.warnings.append(
                f"LLM 提供商 '{self.settings.llm_provider}' 可能无效. "
                f"已知提供商: {', '.join(valid_providers)}"
            )
        
        # 验证 backend_url
        if not self.settings.backend_url.startswith(("http://", "https://")):
            self.errors.append(
                f"Backend URL '{self.settings.backend_url}' 必须以 http:// 或 https:// 开头"
            )
        
        # 检查模型名称是否合理
        if not self.settings.deep_think_llm:
            self.errors.append("deep_think_llm 未设置")
        
        if not self.settings.quick_think_llm:
            self.errors.append("quick_think_llm 未设置")
        
        self.info.append(
            f"✓ LLM 配置: {self.settings.llm_provider} "
            f"(deep: {self.settings.deep_think_llm}, quick: {self.settings.quick_think_llm})"
        )
    
    def _validate_vendors(self) -> None:
        """验证数据供应商配置."""
        valid_vendors = ["yfinance", "alpha_vantage", "local", "google", "openai"]
        
        vendor_fields = {
            "vendor_core_stock_apis": "核心股票 API",
            "vendor_technical_indicators": "技术指标",
            "vendor_fundamental_data": "基本面数据",
            "vendor_news_data": "新闻数据"
        }
        
        for field, name in vendor_fields.items():
            value = getattr(self.settings, field, None)
            if not value:
                self.warnings.append(f"{name} 供应商未设置")
                continue
            
            if value not in valid_vendors:
                self.warnings.append(
                    f"{name} 供应商 '{value}' 可能无效. "
                    f"有效选项: {', '.join(valid_vendors)}"
                )
            else:
                self.info.append(f"✓ {name} 供应商: {value}")
    
    def _validate_database(self) -> None:
        """验证数据库配置."""
        db_url = self.settings.database_url
        
        if not db_url:
            self.errors.append("数据库 URL 未设置")
            return
        
        # 检查数据库类型
        if "sqlite" in db_url.lower():
            self.info.append("✓ 使用 SQLite 数据库")
            # 检查 SQLite 文件路径
            if ":///" in db_url:
                db_path = db_url.split(":///")[1]
                if db_path and not db_path.startswith(":memory:"):
                    db_file = Path(db_path)
                    db_dir = db_file.parent
                    if not db_dir.exists():
                        self.warnings.append(
                            f"SQLite 数据库目录 '{db_dir}' 不存在,将自动创建"
                        )
        elif "postgresql" in db_url.lower():
            self.info.append("✓ 使用 PostgreSQL 数据库")
            # 可以添加更多 PostgreSQL 特定的验证
        else:
            self.warnings.append(f"未知的数据库类型: {db_url}")
    
    def _validate_redis(self) -> None:
        """验证 Redis 配置."""
        if not self.settings.redis_enabled:
            self.info.append("Redis 未启用")
            return
        
        if not self.settings.redis_host:
            self.errors.append("Redis 已启用但 redis_host 未设置")
        
        if not self.settings.redis_port:
            self.errors.append("Redis 已启用但 redis_port 未设置")
        else:
            if not (1 <= self.settings.redis_port <= 65535):
                self.errors.append(
                    f"Redis 端口 {self.settings.redis_port} 无效 (必须在 1-65535 之间)"
                )
        
        if self.settings.redis_enabled and self.settings.streaming_enabled:
            self.info.append(
                f"✓ Redis 流式传输已启用: {self.settings.redis_host}:{self.settings.redis_port}"
            )
    
    def _validate_api_keys(self) -> None:
        """验证 API 密钥配置."""
        # 检查 LLM 提供商对应的 API 密钥
        provider_key_map = {
            "openai": "OPENAI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "grok": "GROK_API_KEY"
        }
        
        provider = self.settings.llm_provider
        if provider in provider_key_map:
            env_key = provider_key_map[provider]
            if not os.getenv(env_key):
                self.warnings.append(
                    f"LLM 提供商 '{provider}' 需要 {env_key} 环境变量"
                )
            else:
                self.info.append(f"✓ {env_key} 已设置")
        
        # 检查数据供应商的 API 密钥
        if self.settings.vendor_fundamental_data == "alpha_vantage" or \
           self.settings.vendor_news_data == "alpha_vantage":
            if not os.getenv("ALPHA_VANTAGE_API_KEY"):
                self.warnings.append(
                    "使用 Alpha Vantage 但 ALPHA_VANTAGE_API_KEY 未设置"
                )
            else:
                self.info.append("✓ ALPHA_VANTAGE_API_KEY 已设置")
        
        # 检查加密密钥
        if not os.getenv("ENCRYPTION_KEY"):
            self.warnings.append("ENCRYPTION_KEY 未设置,敏感数据加密功能将不可用")
        else:
            self.info.append("✓ ENCRYPTION_KEY 已设置")
    
    def _validate_numeric_ranges(self) -> None:
        """验证数值范围."""
        # 验证辩论轮数
        if self.settings.max_debate_rounds < 0:
            self.errors.append(
                f"max_debate_rounds ({self.settings.max_debate_rounds}) 不能为负数"
            )
        elif self.settings.max_debate_rounds > 10:
            self.warnings.append(
                f"max_debate_rounds ({self.settings.max_debate_rounds}) 较大,可能影响性能"
            )
        
        if self.settings.max_risk_discuss_rounds < 0:
            self.errors.append(
                f"max_risk_discuss_rounds ({self.settings.max_risk_discuss_rounds}) 不能为负数"
            )
        elif self.settings.max_risk_discuss_rounds > 10:
            self.warnings.append(
                f"max_risk_discuss_rounds ({self.settings.max_risk_discuss_rounds}) 较大,可能影响性能"
            )
        
        if self.settings.max_recur_limit < 1:
            self.errors.append(
                f"max_recur_limit ({self.settings.max_recur_limit}) 必须至少为 1"
            )
        elif self.settings.max_recur_limit > 1000:
            self.warnings.append(
                f"max_recur_limit ({self.settings.max_recur_limit}) 过大,可能导致无限递归"
            )
    
    def get_report(self) -> Dict[str, Any]:
        """获取验证报告.
        
        Returns:
            包含错误、警告和信息的报告字典
        """
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors.copy(),
            "warnings": self.warnings.copy(),
            "info": self.info.copy(),
            "summary": {
                "total_checks": len(self.errors) + len(self.warnings) + len(self.info),
                "errors_count": len(self.errors),
                "warnings_count": len(self.warnings),
                "info_count": len(self.info)
            }
        }
    
    def print_report(self) -> None:
        """打印验证报告到控制台."""
        print("\n" + "="*70)
        print("配置验证报告")
        print("="*70)
        
        report = self.get_report()
        summary = report["summary"]
        
        print(f"\n总检查项: {summary['total_checks']}")
        print(f"错误: {summary['errors_count']}")
        print(f"警告: {summary['warnings_count']}")
        print(f"信息: {summary['info_count']}")
        
        if self.errors:
            print("\n" + "="*70)
            print("错误 (必须修复):")
            print("="*70)
            for i, error in enumerate(self.errors, 1):
                print(f"{i}. ✗ {error}")
        
        if self.warnings:
            print("\n" + "="*70)
            print("警告 (建议检查):")
            print("="*70)
            for i, warning in enumerate(self.warnings, 1):
                print(f"{i}. ⚠ {warning}")
        
        if self.info:
            print("\n" + "="*70)
            print("配置信息:")
            print("="*70)
            for info in self.info:
                print(f"  {info}")
        
        print("\n" + "="*70)
        if report["valid"]:
            print("✓ 配置验证通过!")
        else:
            print("✗ 配置验证失败,请修复上述错误")
        print("="*70 + "\n")


def validate_settings(settings: Optional[Settings] = None, print_report: bool = True) -> bool:
    """验证配置设置的便捷函数.
    
    Args:
        settings: Settings 实例,如果为 None 则创建新实例
        print_report: 是否打印报告
        
    Returns:
        验证是否通过
    """
    if settings is None:
        settings = Settings()
    
    validator = ConfigValidator(settings)
    is_valid = validator.validate_all()
    
    if print_report:
        validator.print_report()
    
    return is_valid


if __name__ == "__main__":
    # 运行验证
    validate_settings()