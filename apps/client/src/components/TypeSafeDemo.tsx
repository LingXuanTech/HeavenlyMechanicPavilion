import React, { useEffect, useState } from 'react';
import { components } from '../types/api'; // 导入生成的类型

// 定义从 OpenAPI 架构中提取的类型别名，方便使用
type Watchlist = components['schemas']['Watchlist'];

/**
 * 演示组件：展示如何使用 openapi-typescript 生成的类型
 */
export const TypeSafeComponent: React.FC = () => {
  const [stocks, setStocks] = useState<Watchlist[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 模拟 API 调用
    const fetchStocks = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/watchlist/');
        const data: Watchlist[] = await response.json();
        setStocks(data);
      } finally {
        setLoading(false);
      }
    };

    fetchStocks();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold mb-4">类型安全自选股列表</h1>
      <ul className="space-y-2">
        {stocks.map((stock) => (
          <li key={stock.symbol} className="border p-2 rounded shadow-sm">
            <span className="font-mono font-bold">{stock.symbol}</span>
            {/* 这里的 stock.name 会有完美的 IDE 补全和类型检查 */}
            <span className="ml-2 text-gray-600">{stock.name}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};
