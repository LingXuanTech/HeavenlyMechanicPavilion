/**
 * RiskGauge - 半圆风险仪表盘组件
 *
 * 从 StockDetailModal 拆分，可复用于需要展示风险评分的场景。
 */
import React, { memo } from 'react';

interface RiskGaugeProps {
  /** 风险评分 0-10 */
  score: number;
  /** 风险裁定 */
  verdict: string;
}

/** 根据风险分数返回对应颜色 */
const getColor = (s: number): string => {
  if (s <= 3) return '#10B981'; // 绿色
  if (s <= 6) return '#F59E0B'; // 黄色
  return '#EF4444'; // 红色
};

const RiskGauge: React.FC<RiskGaugeProps> = memo(({ score }) => {
  // 0-10 映射到 0-180 度
  const angle = (score / 10) * 180;
  const radians = ((180 - angle) * Math.PI) / 180;
  const needleX = 50 + 35 * Math.cos(radians);
  const needleY = 50 - 35 * Math.sin(radians);

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-24 h-14">
        <svg viewBox="0 0 100 55" className="w-full h-full">
          {/* 渐变定义 */}
          <defs>
            <linearGradient id="riskGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#10B981" />
              <stop offset="50%" stopColor="#F59E0B" />
              <stop offset="100%" stopColor="#EF4444" />
            </linearGradient>
          </defs>

          {/* 背景弧 */}
          <path
            d="M 10 50 A 40 40 0 0 1 90 50"
            fill="none"
            stroke="#292524"
            strokeWidth="8"
            strokeLinecap="round"
          />

          {/* 彩色渐变弧 */}
          <path
            d="M 10 50 A 40 40 0 0 1 90 50"
            fill="none"
            stroke="url(#riskGradient)"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${(angle / 180) * 125.6} 125.6`}
            className="transition-all duration-1000"
          />

          {/* 指针 */}
          <line
            x1="50" y1="50"
            x2={needleX} y2={needleY}
            stroke="white"
            strokeWidth="2"
            strokeLinecap="round"
            className="transition-all duration-1000"
          />

          {/* 中心点 */}
          <circle cx="50" cy="50" r="4" fill="white" />

          {/* 刻度标记 */}
          <text x="8" y="54" fill="#78716C" fontSize="6">0</text>
          <text x="48" y="10" fill="#78716C" fontSize="6">5</text>
          <text x="88" y="54" fill="#78716C" fontSize="6">10</text>
        </svg>
      </div>

      {/* 分数显示 */}
      <div className="text-center -mt-1">
        <span className="text-2xl font-bold" style={{ color: getColor(score) }}>{score}</span>
        <span className="text-xs text-stone-500">/10</span>
      </div>
    </div>
  );
});
RiskGauge.displayName = 'RiskGauge';

export default RiskGauge;
