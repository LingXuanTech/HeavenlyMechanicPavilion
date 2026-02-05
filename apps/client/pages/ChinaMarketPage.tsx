/**
 * A股市场页面
 *
 * 整合北向资金、龙虎榜、限售解禁三大 A 股特色功能
 * 使用 wide 布局以充分展示数据表格
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Landmark } from 'lucide-react';
import PageLayout from '../components/layout/PageLayout';
import ChinaMarketPanel from '../components/ChinaMarketPanel';
import NorthMoneyPanel from '../components/NorthMoneyPanel';
import { useAddStock } from '../hooks';
import { useToast } from '../components/Toast';

const ChinaMarketPage: React.FC = () => {
  const navigate = useNavigate();
  const addStockMutation = useAddStock();
  const toast = useToast();

  const handleStockClick = async (symbol: string) => {
    try {
      await addStockMutation.mutateAsync(symbol);
      toast.success(`已添加 ${symbol} 到关注列表`);
      navigate('/');
    } catch (error) {
      toast.error('添加失败: ' + String(error));
    }
  };

  return (
    <PageLayout
      title="A股市场"
      subtitle="北向资金 · 龙虎榜 · 限售解禁"
      icon={Landmark}
      iconColor="text-red-400"
      iconBgColor="bg-red-500/10"
      variant="wide"
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <ChinaMarketPanel onStockClick={handleStockClick} />
        </div>
        <div className="space-y-6">
          <NorthMoneyPanel onStockClick={handleStockClick} />
        </div>
      </div>
    </PageLayout>
  );
};

export default ChinaMarketPage;
