import React, { useState, useRef, useEffect, memo, useCallback } from 'react';
import {
  Volume2,
  VolumeX,
  Play,
  Pause,
  RotateCcw,
  Loader2,
  Settings,
  ChevronDown,
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

/**
 * TTS 状态
 */
interface TTSStatus {
  available: boolean;
  providers: string[];
  default_provider: string | null;
}

/**
 * 语音信息
 */
interface VoiceInfo {
  id: string;
  name: string;
  language: string;
  gender: string;
  provider?: string;
}

/**
 * AudioBriefing 组件属性
 */
export interface AudioBriefingProps {
  /** 股票代码 */
  symbol: string;
  /** 自定义播报文本（可选，不提供则使用服务端生成） */
  text?: string;
  /** 自动播放 */
  autoPlay?: boolean;
  /** 紧凑模式 */
  compact?: boolean;
  /** 自定义类名 */
  className?: string;
  /** 播放开始回调 */
  onPlay?: () => void;
  /** 播放结束回调 */
  onEnd?: () => void;
  /** 错误回调 */
  onError?: (error: string) => void;
}

/**
 * 音频播报组件
 *
 * 使用 TTS 服务生成股票分析播报
 *
 * @example
 * ```tsx
 * <AudioBriefing symbol="AAPL" />
 *
 * // 紧凑模式
 * <AudioBriefing symbol="AAPL" compact />
 *
 * // 自定义文本
 * <AudioBriefing symbol="AAPL" text="Apple analysis..." />
 * ```
 */
export const AudioBriefing: React.FC<AudioBriefingProps> = memo(({
  symbol,
  text,
  autoPlay = false,
  compact = false,
  className = '',
  onPlay,
  onEnd,
  onError,
}) => {
  // 状态
  const [isLoading, setIsLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // 设置
  const [speed, setSpeed] = useState(1.0);
  const [selectedVoice, setSelectedVoice] = useState<string | null>(null);
  const [voices, setVoices] = useState<VoiceInfo[]>([]);
  const [ttsStatus, setTtsStatus] = useState<TTSStatus | null>(null);

  // Refs
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  // 获取 TTS 状态和语音列表
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const [statusRes, voicesRes] = await Promise.all([
          fetch(`${API_URL}/tts/status`),
          fetch(`${API_URL}/tts/voices`),
        ]);

        if (statusRes.ok) {
          const status = await statusRes.json();
          setTtsStatus(status);
        }

        if (voicesRes.ok) {
          const voiceList = await voicesRes.json();
          setVoices(voiceList);
        }
      } catch (err) {
        console.error('Failed to fetch TTS status', err);
      }
    };

    fetchStatus();
  }, []);

  // 清理音频 URL
  useEffect(() => {
    return () => {
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
      }
    };
  }, []);

  // 生成播报
  const generateBriefing = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      let url: string;
      let options: RequestInit;

      if (text) {
        // 使用自定义文本
        url = `${API_URL}/tts/synthesize`;
        options = {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text,
            voice: selectedVoice,
            speed,
          }),
        };
      } else {
        // 使用服务端生成的播报
        const params = new URLSearchParams();
        if (selectedVoice) params.set('voice', selectedVoice);
        params.set('speed', speed.toString());
        url = `${API_URL}/tts/briefing/${symbol}?${params}`;
        options = { method: 'POST' };
      }

      const response = await fetch(url, options);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      // 获取音频数据
      const blob = await response.blob();

      // 清理旧的 URL
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
      }

      // 创建新的音频 URL
      const audioUrl = URL.createObjectURL(blob);
      audioUrlRef.current = audioUrl;

      // 创建音频元素
      if (audioRef.current) {
        audioRef.current.pause();
      }

      const audio = new Audio(audioUrl);
      audio.volume = isMuted ? 0 : volume;
      audioRef.current = audio;

      // 事件监听
      audio.addEventListener('loadedmetadata', () => {
        setDuration(audio.duration);
      });

      audio.addEventListener('timeupdate', () => {
        setCurrentTime(audio.currentTime);
      });

      audio.addEventListener('ended', () => {
        setIsPlaying(false);
        setCurrentTime(0);
        onEnd?.();
      });

      audio.addEventListener('error', () => {
        setError('播放失败');
        setIsPlaying(false);
        onError?.('播放失败');
      });

      // 自动播放
      if (autoPlay) {
        await audio.play();
        setIsPlaying(true);
        onPlay?.();
      }

    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '生成播报失败';
      setError(errorMsg);
      onError?.(errorMsg);
    } finally {
      setIsLoading(false);
    }
  }, [symbol, text, selectedVoice, speed, volume, isMuted, autoPlay, onPlay, onEnd, onError]);

  // 播放/暂停
  const togglePlay = useCallback(async () => {
    if (!audioRef.current) {
      await generateBriefing();
      return;
    }

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      await audioRef.current.play();
      setIsPlaying(true);
      onPlay?.();
    }
  }, [isPlaying, generateBriefing, onPlay]);

  // 重新生成
  const regenerate = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    setIsPlaying(false);
    setCurrentTime(0);
    generateBriefing();
  }, [generateBriefing]);

  // 静音切换
  const toggleMute = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? volume : 0;
    }
    setIsMuted(!isMuted);
  }, [isMuted, volume]);

  // 音量变化
  const handleVolumeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
    }
    if (newVolume > 0 && isMuted) {
      setIsMuted(false);
    }
  }, [isMuted]);

  // 进度跳转
  const handleSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
  }, []);

  // 格式化时间
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // TTS 不可用
  if (ttsStatus && !ttsStatus.available) {
    return (
      <div className={`flex items-center gap-2 text-gray-500 text-sm ${className}`}>
        <VolumeX className="w-4 h-4" />
        <span>语音播报不可用</span>
      </div>
    );
  }

  // 紧凑模式
  if (compact) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <button
          onClick={togglePlay}
          disabled={isLoading}
          className={`flex items-center justify-center w-8 h-8 rounded-full transition-colors ${
            isLoading ? 'bg-gray-700 cursor-wait' :
            isPlaying ? 'bg-blue-600 hover:bg-blue-500' :
            'bg-gray-700 hover:bg-gray-600'
          }`}
          title={isPlaying ? '暂停' : '播放播报'}
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
          ) : isPlaying ? (
            <Pause className="w-4 h-4 text-white" />
          ) : (
            <Volume2 className="w-4 h-4 text-gray-300" />
          )}
        </button>

        {error && (
          <span className="text-xs text-red-400" title={error}>
            ⚠
          </span>
        )}
      </div>
    );
  }

  // 完整模式
  return (
    <div className={`bg-gray-800/50 rounded-lg border border-gray-700 p-4 ${className}`}>
      {/* 头部 */}
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-200 flex items-center gap-2">
          <Volume2 className="w-4 h-4" />
          AI 语音播报
        </h4>
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="p-1 text-gray-400 hover:text-gray-200 transition-colors"
          title="设置"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>

      {/* 设置面板 */}
      {showSettings && (
        <div className="mb-4 p-3 bg-gray-900/50 rounded-lg space-y-3">
          {/* 语音选择 */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">语音</label>
            <select
              value={selectedVoice || ''}
              onChange={(e) => setSelectedVoice(e.target.value || null)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-gray-200"
            >
              <option value="">默认</option>
              {voices.map((voice) => (
                <option key={voice.id} value={voice.id}>
                  {voice.name} ({voice.language})
                </option>
              ))}
            </select>
          </div>

          {/* 语速 */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">
              语速: {speed.toFixed(1)}x
            </label>
            <input
              type="range"
              min="0.5"
              max="2"
              step="0.1"
              value={speed}
              onChange={(e) => setSpeed(parseFloat(e.target.value))}
              className="w-full"
            />
          </div>
        </div>
      )}

      {/* 播放控制 */}
      <div className="flex items-center gap-3">
        {/* 播放按钮 */}
        <button
          onClick={togglePlay}
          disabled={isLoading}
          className={`flex items-center justify-center w-10 h-10 rounded-full transition-colors ${
            isLoading ? 'bg-gray-700 cursor-wait' :
            isPlaying ? 'bg-blue-600 hover:bg-blue-500' :
            'bg-gray-700 hover:bg-gray-600'
          }`}
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
          ) : isPlaying ? (
            <Pause className="w-5 h-5 text-white" />
          ) : (
            <Play className="w-5 h-5 text-white ml-0.5" />
          )}
        </button>

        {/* 进度条 */}
        <div className="flex-1 space-y-1">
          <input
            type="range"
            min="0"
            max={duration || 100}
            value={currentTime}
            onChange={handleSeek}
            disabled={!audioRef.current}
            className="w-full h-1 bg-gray-700 rounded-full appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-xs text-gray-500">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>

        {/* 音量控制 */}
        <div className="flex items-center gap-2">
          <button
            onClick={toggleMute}
            className="p-1 text-gray-400 hover:text-gray-200 transition-colors"
          >
            {isMuted || volume === 0 ? (
              <VolumeX className="w-4 h-4" />
            ) : (
              <Volume2 className="w-4 h-4" />
            )}
          </button>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={isMuted ? 0 : volume}
            onChange={handleVolumeChange}
            className="w-16 h-1 bg-gray-700 rounded-full appearance-none cursor-pointer"
          />
        </div>

        {/* 重新生成 */}
        <button
          onClick={regenerate}
          disabled={isLoading}
          className="p-2 text-gray-400 hover:text-gray-200 transition-colors"
          title="重新生成"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="mt-2 text-xs text-red-400 flex items-center gap-1">
          <span>⚠</span>
          <span>{error}</span>
        </div>
      )}

      {/* 提供商信息 */}
      {ttsStatus?.default_provider && (
        <div className="mt-2 text-xs text-gray-500">
          使用 {ttsStatus.default_provider.toUpperCase()} TTS
        </div>
      )}
    </div>
  );
});

AudioBriefing.displayName = 'AudioBriefing';

export default AudioBriefing;
