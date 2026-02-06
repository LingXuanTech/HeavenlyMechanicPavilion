/**
 * Vision 图片上传和分析组件
 *
 * 支持拖拽上传、粘贴板上传，展示 Vision 分析结果。
 */

import React, { useState, useCallback, useRef } from 'react';
import { useVisionAnalysis } from '../hooks/useVision';
import type { VisionAnalysisResult } from '../hooks/useVision';
import {
  Upload,
  Image as ImageIcon,
  X,
  Loader2,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  CheckCircle,
  FileText,
} from 'lucide-react';

interface VisionUploadProps {
  symbol?: string;
  className?: string;
  onAnalysisComplete?: (result: VisionAnalysisResult) => void;
}

const VisionUpload: React.FC<VisionUploadProps> = ({
  symbol = '',
  className = '',
  onAnalysisComplete,
}) => {
  const [preview, setPreview] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [description, setDescription] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { mutate: analyze, data: result, isPending, error, reset } = useVisionAnalysis();

  // 处理文件选择
  const handleFile = useCallback((file: File) => {
    if (!file.type.startsWith('image/')) {
      return;
    }

    setSelectedFile(file);
    reset();

    // 生成预览
    const reader = new FileReader();
    reader.onload = (e) => {
      setPreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  }, [reset]);

  // 拖拽处理
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  // 粘贴板处理
  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      const items = e.clipboardData.items;
      for (const item of items) {
        if (item.type.startsWith('image/')) {
          const file = item.getAsFile();
          if (file) handleFile(file);
          break;
        }
      }
    },
    [handleFile]
  );

  // 提交分析
  const handleAnalyze = () => {
    if (!selectedFile) return;

    analyze(
      { file: selectedFile, description, symbol },
      {
        onSuccess: (data) => {
          if (data.success && onAnalysisComplete) {
            onAnalysisComplete(data.analysis);
          }
        },
      }
    );
  };

  // 清除
  const handleClear = () => {
    setPreview(null);
    setSelectedFile(null);
    setDescription('');
    reset();
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className={`bg-surface-raised rounded-lg ${className}`} onPaste={handlePaste}>
      {/* 头部 */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <ImageIcon className="w-5 h-5 text-indigo-400" />
          <h3 className="text-white font-medium">Vision 图表分析</h3>
        </div>
        {(preview || result) && (
          <button
            onClick={handleClear}
            className="text-stone-400 hover:text-stone-50 text-xs flex items-center gap-1"
          >
            <X className="w-3 h-3" />
            清除
          </button>
        )}
      </div>

      <div className="p-4 space-y-4">
        {/* 上传区域 */}
        {!preview && (
          <div
            className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer ${
              isDragging
                ? 'border-indigo-400 bg-indigo-900/20'
                : 'border-border-strong hover:border-border-strong'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="w-8 h-8 text-stone-500 mx-auto mb-2" />
            <p className="text-stone-400 text-sm">拖拽图片到此处，或点击上传</p>
            <p className="text-stone-600 text-xs mt-1">支持 PNG、JPG、WebP，最大 10MB</p>
            <p className="text-stone-600 text-xs">也可以直接 Ctrl+V 粘贴截图</p>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFile(file);
              }}
            />
          </div>
        )}

        {/* 预览 */}
        {preview && (
          <div className="relative">
            <img
              src={preview}
              alt="Preview"
              className="w-full rounded-lg max-h-64 object-contain bg-surface-overlay"
            />
            {selectedFile && (
              <div className="absolute bottom-2 left-2 bg-black/70 text-stone-300 text-xs px-2 py-1 rounded">
                {selectedFile.name} ({(selectedFile.size / 1024).toFixed(0)} KB)
              </div>
            )}
          </div>
        )}

        {/* 描述输入 */}
        {preview && !result && (
          <>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="补充说明（可选）：如 '分析这张K线图的趋势'"
              className="w-full bg-surface-overlay text-stone-300 text-sm rounded px-3 py-2 border border-border-strong focus:border-indigo-500 focus:outline-none"
            />
            <button
              onClick={handleAnalyze}
              disabled={isPending}
              className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-surface-muted text-white text-sm font-medium py-2 rounded transition-colors flex items-center justify-center gap-2"
            >
              {isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  分析中...
                </>
              ) : (
                <>
                  <ImageIcon className="w-4 h-4" />
                  开始分析
                </>
              )}
            </button>
          </>
        )}

        {/* 错误 */}
        {error && (
          <div className="bg-red-900/20 border border-red-800 rounded p-3 text-red-400 text-sm flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{(error as Error).message}</span>
          </div>
        )}

        {/* 分析结果 */}
        {result?.success && result.analysis && (
          <AnalysisResultView analysis={result.analysis} />
        )}
      </div>
    </div>
  );
};

// ============ 分析结果展示 ============

const AnalysisResultView: React.FC<{ analysis: VisionAnalysisResult }> = ({ analysis }) => {
  const TrendIcon =
    analysis.trend === 'Bullish'
      ? TrendingUp
      : analysis.trend === 'Bearish'
        ? TrendingDown
        : Minus;

  const trendColor =
    analysis.trend === 'Bullish'
      ? 'text-green-400'
      : analysis.trend === 'Bearish'
        ? 'text-red-400'
        : 'text-stone-400';

  return (
    <div className="space-y-3">
      {/* 概要 */}
      <div className="bg-surface-overlay/50 rounded p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-indigo-400" />
            <span className="text-white text-sm font-medium">分析结果</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`flex items-center gap-1 text-xs ${trendColor}`}>
              <TrendIcon className="w-3 h-3" />
              {analysis.trend}
            </span>
            <span className="text-xs text-stone-500">
              信心度: {analysis.confidence}%
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 mb-2">
          <span className="bg-surface-muted text-stone-300 text-xs px-2 py-0.5 rounded">
            {analysis.chart_type}
          </span>
          {analysis.time_range && (
            <span className="text-stone-500 text-xs">{analysis.time_range}</span>
          )}
        </div>

        <p className="text-stone-300 text-xs leading-relaxed">{analysis.summary}</p>
      </div>

      {/* 关键数据点 */}
      {analysis.key_data_points && analysis.key_data_points.length > 0 && (
        <div className="bg-surface-overlay/50 rounded p-3">
          <h5 className="text-stone-400 text-xs font-medium mb-2">关键数据</h5>
          <div className="grid grid-cols-2 gap-2">
            {analysis.key_data_points.map((point, idx) => (
              <div key={idx} className="flex justify-between text-xs">
                <span className="text-stone-500">{point.label}</span>
                <span className="text-white">{point.value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 形态和信号 */}
      {((analysis.patterns && analysis.patterns.length > 0) ||
        (analysis.signals && analysis.signals.length > 0)) && (
        <div className="bg-surface-overlay/50 rounded p-3">
          {analysis.patterns && analysis.patterns.length > 0 && (
            <div className="mb-2">
              <h5 className="text-stone-400 text-xs font-medium mb-1">识别形态</h5>
              <div className="flex flex-wrap gap-1">
                {analysis.patterns.map((p, idx) => (
                  <span key={idx} className="bg-indigo-900/30 text-indigo-300 text-xs px-2 py-0.5 rounded">
                    {p}
                  </span>
                ))}
              </div>
            </div>
          )}
          {analysis.signals && analysis.signals.length > 0 && (
            <div>
              <h5 className="text-stone-400 text-xs font-medium mb-1">技术信号</h5>
              <div className="flex flex-wrap gap-1">
                {analysis.signals.map((s, idx) => (
                  <span key={idx} className="bg-yellow-900/30 text-yellow-300 text-xs px-2 py-0.5 rounded">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 建议 */}
      {analysis.recommendation && (
        <div className="bg-surface-overlay/50 rounded p-3 flex items-start gap-2">
          <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
          <div>
            <h5 className="text-stone-400 text-xs font-medium mb-1">投资建议</h5>
            <p className="text-stone-300 text-xs">{analysis.recommendation}</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default VisionUpload;
