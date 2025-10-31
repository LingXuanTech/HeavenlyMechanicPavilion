#!/usr/bin/env python3
"""Example demonstrating the streaming infrastructure."""

import asyncio
import json

import httpx

BASE_URL = "http://localhost:8000"


async def configure_instruments():
    """Configure instruments to track."""
    async with httpx.AsyncClient() as client:
        # Add AAPL
        response = await client.post(
            f"{BASE_URL}/streaming/config/instruments",
            json={
                "symbol": "AAPL",
                "data_types": ["market_data", "news"],
                "enabled": True,
            },
        )
        print(f"Added AAPL: {response.status_code}")
        
        # Add TSLA
        response = await client.post(
            f"{BASE_URL}/streaming/config/instruments",
            json={
                "symbol": "TSLA",
                "data_types": ["market_data", "fundamentals"],
                "enabled": True,
            },
        )
        print(f"Added TSLA: {response.status_code}")


async def start_workers():
    """Start background workers."""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/streaming/config/workers/start-all")
        print(f"Started workers: {response.status_code}")


async def list_workers():
    """List worker status."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/streaming/config/workers")
        workers = response.json()
        
        print("\nWorker Status:")
        print("-" * 80)
        for worker in workers:
            print(f"  {worker['worker_id']}: {worker['status']}")
            print(f"    Success: {worker['success_count']}, Errors: {worker['error_count']}")
            if worker.get("current_vendor"):
                print(f"    Vendor: {worker['current_vendor']}")


async def get_latest_data(symbol: str = "AAPL"):
    """Get latest cached data for a symbol."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/streaming/latest/stream:market_data:{symbol}"
        )
        data = response.json()
        
        if data.get("message"):
            print(f"\nLatest data for {symbol}:")
            message = data["message"]
            print(f"  Timestamp: {message['timestamp']}")
            print(f"  Vendor: {message['vendor']}")
            print(f"  Data type: {message['data_type']}")
        else:
            print(f"\nNo cached data for {symbol}")


async def stream_websocket(symbol: str = "AAPL", duration: int = 30):
    """Stream data via WebSocket for a duration."""
    import websockets
    
    uri = f"ws://localhost:8000/streaming/ws?channels=stream:market_data:{symbol}&symbols={symbol}"
    
    print(f"\nConnecting to WebSocket stream for {symbol}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            
            # Set timeout
            end_time = asyncio.get_event_loop().time() + duration
            
            while asyncio.get_event_loop().time() < end_time:
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=5.0
                    )
                    
                    data = json.loads(message)
                    
                    if data["type"] == "connected":
                        print(f"  Subscribed to channels: {data['channels']}")
                    elif data["type"] == "data":
                        msg = data["message"]
                        print(f"  [{msg['timestamp']}] {msg['symbol']} - {msg['vendor']}")
                    elif data["type"] == "error":
                        print(f"  Error: {data['message']}")
                        
                except asyncio.TimeoutError:
                    continue
                    
    except Exception as e:
        print(f"WebSocket error: {e}")


async def stream_sse(symbol: str = "AAPL", duration: int = 30):
    """Stream data via SSE for a duration."""
    async with httpx.AsyncClient(timeout=duration + 5.0) as client:
        print(f"\nConnecting to SSE stream for {symbol}...")
        
        async with client.stream(
            "POST",
            f"{BASE_URL}/streaming/subscribe/sse",
            json={
                "channels": [f"stream:market_data:{symbol}"],
                "symbols": [symbol],
            },
        ) as response:
            print("Connected!")
            
            end_time = asyncio.get_event_loop().time() + duration
            
            async for line in response.aiter_lines():
                if asyncio.get_event_loop().time() > end_time:
                    break
                
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    try:
                        data = json.loads(data_str)
                        print(f"  [{data['timestamp']}] {data['symbol']} - {data['vendor']}")
                    except json.JSONDecodeError:
                        pass


async def main():
    """Main example."""
    print("=" * 80)
    print("Streaming Infrastructure Example")
    print("=" * 80)
    
    # Check if backend is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/")
            if response.status_code != 200:
                print("Error: Backend not responding")
                return
            
            info = response.json()
            if info.get("redis") != "enabled":
                print("Error: Redis is not enabled. Set REDIS_ENABLED=true")
                return
    except httpx.ConnectError:
        print("Error: Cannot connect to backend. Is it running?")
        print("Start with: uvicorn app.main:app --reload")
        return
    
    # Step 1: Configure instruments
    print("\n1. Configuring instruments...")
    await configure_instruments()
    
    # Step 2: Start workers
    print("\n2. Starting workers...")
    await start_workers()
    
    # Step 3: Wait for first data collection
    print("\n3. Waiting 5 seconds for data collection...")
    await asyncio.sleep(5)
    
    # Step 4: Check worker status
    await list_workers()
    
    # Step 5: Get latest data
    await get_latest_data("AAPL")
    await get_latest_data("TSLA")
    
    # Step 6: Choose streaming method
    print("\n" + "=" * 80)
    print("Choose streaming method:")
    print("  1. WebSocket (requires websockets package)")
    print("  2. SSE (Server-Sent Events)")
    print("  3. Skip streaming demo")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        try:
            await stream_websocket("AAPL", duration=30)
        except ImportError:
            print("Error: websockets package not installed")
            print("Install with: pip install websockets")
    elif choice == "2":
        await stream_sse("AAPL", duration=30)
    
    print("\n" + "=" * 80)
    print("Example complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
