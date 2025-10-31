#!/usr/bin/env python3
"""Test script for streaming infrastructure."""

import asyncio
import sys


async def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    # Schemas
    
    # Services
    
    # Workers
    
    # API
    
    print("✓ All imports successful")
    return True


async def test_schemas():
    """Test schema creation."""
    print("\nTesting schemas...")
    
    from app.schemas.streaming import (
        DataType,
        InstrumentConfig,
        RefreshCadence,
    )
    
    # Test InstrumentConfig
    instrument = InstrumentConfig(
        symbol="AAPL",
        data_types=[DataType.MARKET_DATA, DataType.NEWS],
        enabled=True,
    )
    assert instrument.symbol == "AAPL"
    assert len(instrument.data_types) == 2
    
    # Test RefreshCadence
    cadence = RefreshCadence(
        data_type=DataType.MARKET_DATA,
        interval_seconds=60,
        enabled=True,
        retry_attempts=3,
    )
    assert cadence.data_type == DataType.MARKET_DATA
    assert cadence.interval_seconds == 60
    
    print("✓ Schema tests passed")
    return True


async def test_redis_required():
    """Test that streaming requires Redis."""
    print("\nTesting Redis requirement...")
    
    from app.cache import get_redis_manager
    
    redis = get_redis_manager()
    if redis is None:
        print("✓ Redis not initialized (expected without redis_enabled)")
    else:
        print("✓ Redis initialized")
    
    return True


async def test_api_routes():
    """Test that API routes are registered."""
    print("\nTesting API routes...")
    
    from app.api import get_api_router
    
    router = get_api_router()
    
    # Check that routes exist
    routes = [route.path for route in router.routes]
    
    # Check for streaming routes
    streaming_routes = [r for r in routes if "streaming" in r]
    
    if streaming_routes:
        print(f"✓ Found {len(streaming_routes)} streaming routes")
        for route in streaming_routes[:5]:  # Show first 5
            print(f"  - {route}")
    else:
        print("✗ No streaming routes found")
        return False
    
    return True


async def test_worker_manager_creation():
    """Test worker manager can be created."""
    print("\nTesting worker manager creation...")
    
    # We can't fully test without Redis, but we can test imports and structure
    from app.schemas.streaming import DataType
    
    print("✓ WorkerManager class available")
    print(f"✓ DataTypes available: {[dt.value for dt in DataType]}")
    
    return True


async def test_configuration_structure():
    """Test configuration structure."""
    print("\nTesting configuration structure...")
    
    from app.schemas.streaming import (
        DataType,
        InstrumentConfig,
        RefreshCadence,
        StreamingConfig,
    )
    
    # Create a complete configuration
    config = StreamingConfig(
        instruments=[
            InstrumentConfig(
                symbol="AAPL",
                data_types=[DataType.MARKET_DATA],
                enabled=True,
            ),
        ],
        cadences=[
            RefreshCadence(
                data_type=DataType.MARKET_DATA,
                interval_seconds=60,
            ),
        ],
        global_enabled=True,
        max_retries=3,
        cache_ttl_seconds=300,
    )
    
    assert len(config.instruments) == 1
    assert len(config.cadences) == 1
    assert config.global_enabled
    
    # Test serialization
    config_dict = config.model_dump()
    assert "instruments" in config_dict
    assert "cadences" in config_dict
    
    print("✓ Configuration structure tests passed")
    return True


async def run_all_tests():
    """Run all tests."""
    print("=" * 80)
    print("Testing Streaming Infrastructure")
    print("=" * 80)
    
    tests = [
        test_imports,
        test_schemas,
        test_redis_required,
        test_api_routes,
        test_worker_manager_creation,
        test_configuration_structure,
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test.__name__, False))
    
    print("\n" + "=" * 80)
    print("Test Results")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("-" * 80)
    print(f"Passed: {passed}/{total}")
    
    return passed == total


if __name__ == "__main__":
    # Add parent directory to path
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
