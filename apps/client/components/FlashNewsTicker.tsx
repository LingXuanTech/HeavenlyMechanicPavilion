import React from 'react';
import { FlashNews } from '../types';
import { Radio, AlertTriangle, Zap, TrendingUp, TrendingDown } from 'lucide-react';

interface FlashNewsTickerProps {
  news: FlashNews[];
  isRefreshing: boolean;
}

const FlashNewsTicker: React.FC<FlashNewsTickerProps> = ({ news, isRefreshing }) => {
  if (!news || news.length === 0) return null;

  return (
    <div className="bg-indigo-950/30 border-t border-gray-800 border-b border-indigo-900/30 h-10 flex items-center overflow-hidden relative">
      <div className="absolute left-0 top-0 bottom-0 bg-indigo-900 px-3 z-10 flex items-center gap-2 text-xs font-bold text-white shadow-lg">
        <Zap className={`w-3 h-3 text-yellow-400 ${isRefreshing ? 'animate-pulse' : ''}`} />
        WATCHDOG
      </div>
      
      <div className="flex gap-12 animate-marquee px-4 w-full items-center">
         {news.map((item, i) => (
           <div key={`${item.id}-${i}`} className="flex items-center gap-3 shrink-0">
              <span className="text-[10px] text-gray-400 font-mono">{item.time}</span>
              <div className="flex items-center gap-2">
                 <span className={`text-xs font-medium ${item.sentiment === 'Positive' ? 'text-green-300' : 'text-red-300'}`}>
                   {item.sentiment === 'Positive' ? <TrendingUp className="w-3 h-3 inline mr-1" /> : <TrendingDown className="w-3 h-3 inline mr-1" />}
                   {item.headline}
                 </span>
                 {item.relatedSymbols?.map(sym => (
                   <span key={sym} className="text-[9px] bg-gray-800 px-1 rounded text-gray-300 border border-gray-700">{sym}</span>
                 ))}
                 {item.impact === 'High' && (
                    <span className="text-[9px] bg-red-600 text-white px-1 rounded font-bold animate-pulse">BREAKING</span>
                 )}
              </div>
           </div>
         ))}
      </div>
    </div>
  );
};

export default FlashNewsTicker;