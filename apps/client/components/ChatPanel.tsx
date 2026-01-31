/**
 * ChatPanel - Agent 对话面板
 *
 * 从 StockDetailModal 拆分，提供与 Fund Manager Agent 的对话功能。
 */
import React, { useState, useRef, useEffect, memo } from 'react';
import type { Stock, AgentAnalysis, ChatMessage } from '../types';
import * as api from '../services/api';
import { Bot, Send } from 'lucide-react';

interface ChatPanelProps {
  stock: Stock;
  analysis?: AgentAnalysis;
}

const ChatPanel: React.FC<ChatPanelProps> = memo(({ stock, analysis }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize chat with greeting
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        role: 'model',
        text: `Hello! I've analyzed ${stock.name}. I have insights from the Bull Researcher, Bear Researcher, and Risk Manager. What would you like to know?`
      }]);
    }
  }, [stock.name, messages.length]);

  // Scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !analysis) return;

    const userMsg: ChatMessage = { role: 'user', text: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    const response = await api.getChatResponse(stock.symbol, userMsg.text);

    setMessages(prev => [...prev, { role: 'model', text: response.text }]);
    setIsTyping(false);
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 overflow-y-auto pr-2 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-lg p-3 ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white rounded-br-none'
                : 'bg-gray-800 text-gray-200 rounded-bl-none border border-gray-700'
            }`}>
              <div className="flex items-center gap-2 mb-1 opacity-50 text-xs">
                {msg.role === 'model' ? <Bot className="w-3 h-3" /> : 'You'}
              </div>
              <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.text}</p>
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-gray-800 text-gray-400 rounded-lg p-3 rounded-bl-none border border-gray-700 text-sm flex items-center gap-2">
              <Bot className="w-3 h-3" /> Thinking...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSendMessage} className="mt-4 relative">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={analysis ? "Ask about risks, targets, or details..." : "Run analysis first to chat..."}
          disabled={!analysis || isTyping}
          className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg pl-4 pr-12 py-3 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || !analysis || isTyping}
          className="absolute right-2 top-2 p-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
});
ChatPanel.displayName = 'ChatPanel';

export default ChatPanel;
