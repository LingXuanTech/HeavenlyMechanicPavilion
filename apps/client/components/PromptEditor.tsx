import React, { useState, useEffect } from 'react';
import { logger } from '../utils/logger';
import {
  X,
  Save,
  RefreshCw,
  Bot,
  ChevronRight,
  AlertCircle,
  Check,
  Lock,
  FileText,
  User,
} from 'lucide-react';
import { usePrompts, useUpdatePrompt, useReloadPrompts, PromptConfig } from '../hooks/usePrompts';

interface PromptEditorProps {
  onClose: () => void;
}

// Agent 角色的图标和颜色配置
const ROLE_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
  fundamentals_analyst: { icon: '📊', color: 'blue', label: 'Fundamentals Analyst' },
  news_analyst: { icon: '📰', color: 'purple', label: 'News Analyst' },
  market_analyst: { icon: '📈', color: 'green', label: 'Market Analyst' },
  social_media_analyst: { icon: '💬', color: 'pink', label: 'Social Media Analyst' },
  bull_researcher: { icon: '🐂', color: 'emerald', label: 'Bull Researcher' },
  bear_researcher: { icon: '🐻', color: 'red', label: 'Bear Researcher' },
  risk_manager: { icon: '🛡️', color: 'amber', label: 'Risk Manager' },
  portfolio_manager: { icon: '💼', color: 'indigo', label: 'Portfolio Manager' },
  trader: { icon: '💹', color: 'cyan', label: 'Trader' },
};

const PromptEditor: React.FC<PromptEditorProps> = ({ onClose }) => {
  const { data, isLoading, error } = usePrompts();
  const updatePromptMutation = useUpdatePrompt();
  const reloadPromptsMutation = useReloadPrompts();

  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [editedPrompts, setEditedPrompts] = useState<Record<string, PromptConfig>>({});
  const [apiKey, setApiKey] = useState('');
  const [showApiKeyInput, setShowApiKeyInput] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  // 初始化编辑状态
  useEffect(() => {
    if (data?.prompts) {
      setEditedPrompts(data.prompts);
      // 默认选择第一个角色
      const roles = Object.keys(data.prompts);
      if (roles.length > 0 && !selectedRole) {
        setSelectedRole(roles[0]);
      }
    }
  }, [data]);

  const handlePromptChange = (role: string, field: 'system' | 'user', value: string) => {
    setEditedPrompts(prev => ({
      ...prev,
      [role]: {
        ...prev[role],
        [field]: value,
      },
    }));
  };

  const handleSave = async () => {
    if (!selectedRole || !editedPrompts[selectedRole]) return;

    setSaveStatus('saving');
    setErrorMessage('');

    try {
      await updatePromptMutation.mutateAsync({
        role: selectedRole,
        config: editedPrompts[selectedRole],
        apiKey: apiKey || undefined,
      });
      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (err: unknown) {
      setSaveStatus('error');
      const errorMsg = err instanceof Error ? err.message : 'Failed to save';
      setErrorMessage(errorMsg);
      if (errorMsg.includes('API key')) {
        setShowApiKeyInput(true);
      }
    }
  };

  const handleReload = async () => {
    try {
      await reloadPromptsMutation.mutateAsync();
    } catch (err) {
      logger.error('Failed to reload prompts', err);
    }
  };

  const hasChanges = (role: string) => {
    if (!data?.prompts[role] || !editedPrompts[role]) return false;
    return (
      data.prompts[role].system !== editedPrompts[role].system ||
      data.prompts[role].user !== editedPrompts[role].user
    );
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  if (isLoading) {
    return (
      <div
        onClick={handleBackdropClick}
        className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center"
      >
        <div className="bg-gray-900 rounded-xl p-8 text-white">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4" />
          <p>Loading prompts...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        onClick={handleBackdropClick}
        className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center"
      >
        <div className="bg-gray-900 rounded-xl p-8 text-white text-center">
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-4" />
          <p className="text-red-400">Failed to load prompts</p>
          <button
            onClick={onClose}
            className="mt-4 px-4 py-2 bg-gray-700 rounded-lg hover:bg-gray-600"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  const roles = Object.keys(editedPrompts);

  return (
    <div
      onClick={handleBackdropClick}
      className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
    >
      <div className="bg-gray-900 border border-gray-800 w-full max-w-6xl h-[90vh] rounded-xl flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="shrink-0 p-4 border-b border-gray-800 bg-gray-950/50 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Bot className="w-6 h-6 text-purple-400" />
            <div>
              <h2 className="text-xl font-bold text-white">Prompt Editor</h2>
              <p className="text-xs text-gray-500">{data?.path}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* API Key Input Toggle */}
            <button
              onClick={() => setShowApiKeyInput(!showApiKeyInput)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                apiKey ? 'bg-green-600/20 text-green-400 border border-green-600' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              <Lock className="w-4 h-4" />
              {apiKey ? 'Key Set' : 'Set API Key'}
            </button>

            {/* Reload Button */}
            <button
              onClick={handleReload}
              disabled={reloadPromptsMutation.isPending}
              className="flex items-center gap-2 px-3 py-1.5 bg-gray-800 text-gray-300 rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${reloadPromptsMutation.isPending ? 'animate-spin' : ''}`} />
              Reload
            </button>

            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 p-2 rounded-full transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* API Key Input (Collapsible) */}
        {showApiKeyInput && (
          <div className="shrink-0 p-3 bg-gray-950 border-b border-gray-800">
            <div className="flex items-center gap-3 max-w-md">
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter API Key for write access..."
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
              />
              <button
                onClick={() => setShowApiKeyInput(false)}
                className="text-gray-500 hover:text-gray-300 text-sm"
              >
                Hide
              </button>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Sidebar - Role List */}
          <div className="w-64 shrink-0 border-r border-gray-800 overflow-y-auto bg-gray-950/50">
            <div className="p-2">
              {roles.map((role) => {
                const config = ROLE_CONFIG[role] || { icon: '🤖', color: 'gray', label: role };
                const isSelected = selectedRole === role;
                const changed = hasChanges(role);

                return (
                  <button
                    key={role}
                    onClick={() => setSelectedRole(role)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 transition-all ${
                      isSelected
                        ? 'bg-purple-600/20 border border-purple-500/50 text-white'
                        : 'hover:bg-gray-800 text-gray-400 hover:text-white'
                    }`}
                  >
                    <span className="text-lg">{config.icon}</span>
                    <span className="flex-1 text-left text-sm truncate">{config.label}</span>
                    {changed && (
                      <span className="w-2 h-2 bg-yellow-500 rounded-full" title="Unsaved changes" />
                    )}
                    {isSelected ? (
                      <ChevronRight className="w-4 h-4 text-purple-400" />
                    ) : null}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Main Editor Area */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {selectedRole && editedPrompts[selectedRole] ? (
              <>
                {/* Editor Header */}
                <div className="shrink-0 p-4 border-b border-gray-800 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">
                      {ROLE_CONFIG[selectedRole]?.icon || '🤖'}
                    </span>
                    <div>
                      <h3 className="text-lg font-bold text-white">
                        {ROLE_CONFIG[selectedRole]?.label || selectedRole}
                      </h3>
                      <p className="text-xs text-gray-500">Role: {selectedRole}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    {/* Save Status */}
                    {saveStatus === 'saving' && (
                      <span className="text-sm text-gray-400 flex items-center gap-2">
                        <RefreshCw className="w-4 h-4 animate-spin" /> Saving...
                      </span>
                    )}
                    {saveStatus === 'success' && (
                      <span className="text-sm text-green-400 flex items-center gap-2">
                        <Check className="w-4 h-4" /> Saved!
                      </span>
                    )}
                    {saveStatus === 'error' && (
                      <span className="text-sm text-red-400 flex items-center gap-2">
                        <AlertCircle className="w-4 h-4" /> {errorMessage}
                      </span>
                    )}

                    {/* Save Button */}
                    <button
                      onClick={handleSave}
                      disabled={!hasChanges(selectedRole) || saveStatus === 'saving'}
                      className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Save className="w-4 h-4" />
                      Save Changes
                    </button>
                  </div>
                </div>

                {/* Prompt Fields */}
                <div className="flex-1 overflow-y-auto p-4 space-y-6">
                  {/* System Prompt */}
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 text-sm font-medium text-gray-300">
                      <FileText className="w-4 h-4 text-blue-400" />
                      System Prompt
                    </label>
                    <textarea
                      value={editedPrompts[selectedRole].system}
                      onChange={(e) => handlePromptChange(selectedRole, 'system', e.target.value)}
                      className="w-full h-48 bg-gray-950 border border-gray-700 rounded-lg p-4 text-sm text-gray-200 font-mono resize-y focus:outline-none focus:ring-1 focus:ring-purple-500 placeholder-gray-600"
                      placeholder="Enter system prompt..."
                    />
                    <p className="text-xs text-gray-500">
                      Defines the agent's role, personality, and constraints.
                    </p>
                  </div>

                  {/* User Prompt Template */}
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 text-sm font-medium text-gray-300">
                      <User className="w-4 h-4 text-green-400" />
                      User Prompt Template
                    </label>
                    <textarea
                      value={editedPrompts[selectedRole].user}
                      onChange={(e) => handlePromptChange(selectedRole, 'user', e.target.value)}
                      className="w-full h-64 bg-gray-950 border border-gray-700 rounded-lg p-4 text-sm text-gray-200 font-mono resize-y focus:outline-none focus:ring-1 focus:ring-purple-500 placeholder-gray-600"
                      placeholder="Enter user prompt template... Use {variable} for placeholders."
                    />
                    <p className="text-xs text-gray-500">
                      Template for user messages. Use {'{symbol}'}, {'{data}'}, etc. as placeholders.
                    </p>
                  </div>

                  {/* Preview Section */}
                  <div className="bg-gray-950/50 border border-gray-800 rounded-lg p-4">
                    <h4 className="text-sm font-medium text-gray-400 mb-2">Character Count</h4>
                    <div className="flex gap-6 text-xs">
                      <span className="text-blue-400">
                        System: {editedPrompts[selectedRole].system.length} chars
                      </span>
                      <span className="text-green-400">
                        User: {editedPrompts[selectedRole].user.length} chars
                      </span>
                      <span className="text-gray-500">
                        Total: {editedPrompts[selectedRole].system.length + editedPrompts[selectedRole].user.length} chars
                      </span>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-500">
                <div className="text-center">
                  <Bot className="w-16 h-16 mx-auto mb-4 opacity-30" />
                  <p>Select a role to edit its prompts</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PromptEditor;
