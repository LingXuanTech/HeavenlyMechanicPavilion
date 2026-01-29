/**
 * A股市场页面
 *
 * 整合北向资金、龙虎榜、限售解禁三大 A 股特色功能
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Landmark, ArrowLeft } from 'lucide-react';
import ChinaMarketPanel from '../components/ChinaMarketPanel';
import { useAddStock } from '../hooks';

const ChinaMarketPage: React.FC = () => {
  const navigate = useNavigate();
  const addStockMutation = useAddStock();

  const handleStockClick = async (symbol: string) => {
    try {
      await addStockMutation.mutateAsync(symbol);
      navigate('/');
    } catch (error) {
      console.error('Failed to add stock', error);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="shrink-0 px-6 py-4 border-b border-gray-800 bg-gray-900/50">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-500/10 rounded-lg">
              <Landmark className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">A股市场</h1>
              <p className="text-xs text-gray-500">北向资金 · 龙虎榜 · 限售解禁</p>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto">
          <ChinaMarketPanel onStockClick={handleStockClick} />
        </div>
      </main>
    </div>
  );
};

export default ChinaMarketPage;
