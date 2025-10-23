"""VendorConfig model for storing data vendor configuration."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class VendorConfig(SQLModel, table=True):
    """VendorConfig model for storing data vendor configurations."""

    __tablename__ = "vendor_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=255)
    vendor_type: str = Field(index=True, max_length=50)  # market_data, news, fundamental, etc.
    
    # Vendor information
    provider: str = Field(max_length=100)  # yfinance, alpha_vantage, openai, etc.
    api_endpoint: Optional[str] = Field(default=None, max_length=500)
    
    # API Configuration (store encrypted or reference secrets)
    api_key_ref: Optional[str] = Field(default=None, max_length=255)  # Reference to secret store
    config_json: Optional[str] = Field(default=None)
    
    # Rate limiting
    rate_limit_per_minute: Optional[int] = Field(default=None)
    rate_limit_per_day: Optional[int] = Field(default=None)
    
    # Status
    is_active: bool = Field(default=True, index=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata fields
    description: Optional[str] = Field(default=None, max_length=1000)
    metadata_json: Optional[str] = Field(default=None)
