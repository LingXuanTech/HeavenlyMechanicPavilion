import { StockPrice } from '../types';

// Helper to generate a random walk for charts
const generateHistory = (startPrice: number, points: number = 50) => {
  const history = [];
  let currentPrice = startPrice;
  const now = new Date();
  
  for (let i = points; i > 0; i--) {
    const time = new Date(now.getTime() - i * 60000 * 30); // 30 min intervals
    // Random walk
    const change = (Math.random() - 0.5) * (startPrice * 0.02);
    currentPrice += change;
    history.push({
      time: time.getHours() + ':' + time.getMinutes().toString().padStart(2, '0'),
      value: parseFloat(currentPrice.toFixed(2))
    });
  }
  return history;
};

// Mock initial prices map
const MOCK_PRICES: Record<string, number> = {
  '600276.SH': 45.20,
  '00700.HK': 385.40,
  'AAPL': 175.50,
  '603993.SH': 6.85,
  '000002.SZ': 9.30,
  'NVDA': 880.20
};

export const getMockStockPrice = (symbol: string): StockPrice => {
  const basePrice = MOCK_PRICES[symbol] || (Math.random() * 100 + 10);
  // Add some daily fluctuation
  const currentPrice = basePrice + (Math.random() - 0.5) * (basePrice * 0.05);
  const prevClose = basePrice; // Treat base as prev close for simplicity
  const change = currentPrice - prevClose;
  const changePercent = (change / prevClose) * 100;

  return {
    price: parseFloat(currentPrice.toFixed(2)),
    change: parseFloat(change.toFixed(2)),
    changePercent: parseFloat(changePercent.toFixed(2)),
    history: generateHistory(prevClose)
  };
};