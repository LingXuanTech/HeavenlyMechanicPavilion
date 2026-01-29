/**
 * Prompt 编辑器页面
 *
 * 用于管理和编辑 Agent Prompt 配置
 * 使用 split 布局变体（左侧列表 + 右侧编辑器）
 */
import React, { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bot, RefreshCw, Download, Upload } from 'lucide-react';
import PageLayout from '../components/layout/PageLayout';
import {
  getPromptList,
  getPromptDetail,
  updatePrompt,
  rollbackPrompt,
  refreshPromptCache,
  exportPromptsYaml,
  importPromptsYaml,
} from '../services/api';
import type { AgentPrompt, AgentPromptDetail, AgentCategory } from '../types';

// Agent 分类显示名称
const CATEGORY_LABELS: Record<AgentCategory, string> = {
  analyst: '分析师',
  researcher: '研究员',
  manager: '管理层',
  risk: '风险辩论',
  trader: '交易员',
  synthesizer: '合成器',
};

// 分类图标
const CATEGORY_ICONS: Record<AgentCategory, string> = {
  analyst: '📊',
  researcher: '🔬',
  manager: '👔',
  risk: '⚠️',
  trader: '💹',
  synthesizer: '🔗',
};

const PromptsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedCategory, setSelectedCategory] = useState<AgentCategory | 'all'>('all');
  const [selectedPromptId, setSelectedPromptId] = useState<number | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editedSystemPrompt, setEditedSystemPrompt] = useState('');
  const [editedUserPrompt, setEditedUserPrompt] = useState('');
  const [changeNote, setChangeNote] = useState('');
  const [showYamlImport, setShowYamlImport] = useState(false);
  const [yamlContent, setYamlContent] = useState('');

  // 获取 Prompt 列表
  const { data: promptsData, isLoading: isLoadingList } = useQuery({
    queryKey: ['prompts', selectedCategory],
    queryFn: () => getPromptList(selectedCategory === 'all' ? undefined : selectedCategory),
  });

  // 获取 Prompt 详情
  const { data: promptDetail, isLoading: isLoadingDetail } = useQuery({
    queryKey: ['prompt-detail', selectedPromptId],
    queryFn: () => (selectedPromptId ? getPromptDetail(selectedPromptId) : null),
    enabled: !!selectedPromptId,
  });

  // 更新 Prompt
  const updateMutation = useMutation({
    mutationFn: (data: { id: number; system_prompt: string; user_prompt_template: string; change_note: string }) =>
      updatePrompt(data.id, {
        system_prompt: data.system_prompt,
        user_prompt_template: data.user_prompt_template,
        change_note: data.change_note,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
      queryClient.invalidateQueries({ queryKey: ['prompt-detail', selectedPromptId] });
      setEditMode(false);
      setChangeNote('');
    },
  });

  // 回滚 Prompt
  const rollbackMutation = useMutation({
    mutationFn: ({ id, version }: { id: number; version: number }) => rollbackPrompt(id, version),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
      queryClient.invalidateQueries({ queryKey: ['prompt-detail', selectedPromptId] });
    },
  });

  // 刷新缓存
  const refreshMutation = useMutation({
    mutationFn: refreshPromptCache,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
    },
  });

  // 导入 YAML
  const importMutation = useMutation({
    mutationFn: importPromptsYaml,
    onSuccess: (result) => {
      alert(`导入完成：创建 ${result.created} 个，更新 ${result.updated} 个`);
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
      setShowYamlImport(false);
      setYamlContent('');
    },
    onError: (err: Error) => {
      alert(`导入失败: ${err.message}`);
    },
  });

  // 导出 YAML
  const handleExport = useCallback(async () => {
    try {
      const yaml = await exportPromptsYaml();
      const blob = new Blob([yaml], { type: 'text/yaml' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'agent_prompts.yaml';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert('导出失败');
    }
  }, []);

  // 开始编辑
  const handleStartEdit = useCallback(() => {
    if (promptDetail) {
      setEditedSystemPrompt(promptDetail.system_prompt);
      setEditedUserPrompt(promptDetail.user_prompt_template);
      setEditMode(true);
    }
  }, [promptDetail]);

  // 保存编辑
  const handleSave = useCallback(() => {
    if (selectedPromptId && editedSystemPrompt) {
      updateMutation.mutate({
        id: selectedPromptId,
        system_prompt: editedSystemPrompt,
        user_prompt_template: editedUserPrompt,
        change_note: changeNote || `Updated at ${new Date().toLocaleString()}`,
      });
    }
  }, [selectedPromptId, editedSystemPrompt, editedUserPrompt, changeNote, updateMutation]);

  // 取消编辑
  const handleCancelEdit = useCallback(() => {
    setEditMode(false);
    setChangeNote('');
  }, []);

  const prompts = promptsData?.prompts || [];

  // 左侧面板：Prompt 列表
  const leftPanel = (
    <>
      {/* Category Filter */}
      <div className="p-3 border-b border-gray-800">
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value as AgentCategory | 'all')}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
        >
          <option value="all">全部分类</option>
          {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {CATEGORY_ICONS[value as AgentCategory]} {label}
            </option>
          ))}
        </select>
      </div>

      {/* Prompt List */}
      <div className="flex-1 overflow-y-auto">
        {isLoadingList ? (
          <div className="p-4 text-center text-gray-500">加载中...</div>
        ) : prompts.length === 0 ? (
          <div className="p-4 text-center text-gray-500">暂无 Prompt</div>
        ) : (
          <div className="divide-y divide-gray-800">
            {prompts.map((prompt) => (
              <button
                key={prompt.id}
                onClick={() => {
                  setSelectedPromptId(prompt.id);
                  setEditMode(false);
                }}
                className={`w-full p-3 text-left hover:bg-gray-800/50 transition-colors ${
                  selectedPromptId === prompt.id ? 'bg-gray-800 border-l-2 border-blue-500' : ''
                }`}
              >
                <div className="flex items-center gap-2">
                  <span>{CATEGORY_ICONS[prompt.category]}</span>
                  <span className="font-medium text-white truncate">
                    {prompt.display_name}
                  </span>
                </div>
                <div className="text-xs text-gray-500 mt-1 truncate">
                  {prompt.agent_key} · v{prompt.version}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </>
  );

  return (
    <PageLayout
      title="Prompt 配置中心"
      subtitle="管理和编辑 Agent Prompt"
      icon={Bot}
      iconColor="text-purple-400"
      iconBgColor="bg-purple-500/10"
      variant="split"
      splitLeft={leftPanel}
      splitLeftWidth="w-80"
      actions={[
        {
          label: '刷新缓存',
          icon: RefreshCw,
          onClick: () => refreshMutation.mutate(),
          loading: refreshMutation.isPending,
          variant: 'ghost',
        },
        {
          label: '导出 YAML',
          icon: Download,
          onClick: handleExport,
          variant: 'secondary',
        },
        {
          label: '导入 YAML',
          icon: Upload,
          onClick: () => setShowYamlImport(true),
          variant: 'primary',
        },
      ]}
    >
      {/* Right Panel - Prompt Detail/Editor */}
      {!selectedPromptId ? (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <div className="text-4xl mb-3">👈</div>
            <p>选择左侧的 Prompt 进行查看或编辑</p>
          </div>
        </div>
      ) : isLoadingDetail ? (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          加载中...
        </div>
      ) : promptDetail ? (
        <>
          {/* Detail Header */}
          <div className="px-6 py-4 border-b border-gray-800 bg-gray-800/30">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white">
                  {CATEGORY_ICONS[promptDetail.category]} {promptDetail.display_name}
                </h3>
                <p className="text-sm text-gray-400 mt-1">{promptDetail.description}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-1 bg-gray-700 rounded text-xs">
                  v{promptDetail.version}
                </span>
                {!editMode ? (
                  <button
                    onClick={handleStartEdit}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium transition-colors"
                  >
                    ✏️ 编辑
                  </button>
                ) : (
                  <div className="flex gap-2">
                    <button
                      onClick={handleCancelEdit}
                      className="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded-lg text-sm font-medium transition-colors"
                    >
                      取消
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={updateMutation.isPending}
                      className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                    >
                      {updateMutation.isPending ? '保存中...' : '💾 保存'}
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Variables */}
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="text-xs text-gray-500">可用变量：</span>
              {promptDetail.available_variables.map((v) => (
                <code
                  key={v}
                  className="px-2 py-0.5 bg-gray-700 rounded text-xs text-yellow-400"
                >
                  {'{'}
                  {v}
                  {'}'}
                </code>
              ))}
            </div>
          </div>

          {/* Prompt Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* System Prompt */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                系统提示词 (System Prompt)
              </label>
              {editMode ? (
                <textarea
                  value={editedSystemPrompt}
                  onChange={(e) => setEditedSystemPrompt(e.target.value)}
                  className="w-full h-64 bg-gray-800 border border-gray-700 rounded-lg p-4 text-sm font-mono resize-none focus:border-blue-500 focus:outline-none"
                  placeholder="输入系统提示词..."
                />
              ) : (
                <pre className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-4 text-sm font-mono whitespace-pre-wrap text-gray-300 max-h-64 overflow-y-auto">
                  {promptDetail.system_prompt || '(空)'}
                </pre>
              )}
            </div>

            {/* User Prompt Template */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                用户消息模板 (User Prompt Template)
              </label>
              {editMode ? (
                <textarea
                  value={editedUserPrompt}
                  onChange={(e) => setEditedUserPrompt(e.target.value)}
                  className="w-full h-32 bg-gray-800 border border-gray-700 rounded-lg p-4 text-sm font-mono resize-none focus:border-blue-500 focus:outline-none"
                  placeholder="输入用户消息模板..."
                />
              ) : (
                <pre className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-4 text-sm font-mono whitespace-pre-wrap text-gray-300">
                  {promptDetail.user_prompt_template || '(空)'}
                </pre>
              )}
            </div>

            {/* Change Note (only in edit mode) */}
            {editMode && (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  变更说明 (可选)
                </label>
                <input
                  type="text"
                  value={changeNote}
                  onChange={(e) => setChangeNote(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  placeholder="描述本次修改的内容..."
                />
              </div>
            )}

            {/* Version History */}
            {!editMode && promptDetail.version_history.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  版本历史
                </label>
                <div className="bg-gray-800/50 border border-gray-700 rounded-lg divide-y divide-gray-700">
                  {promptDetail.version_history.map((v) => (
                    <div
                      key={v.version}
                      className="flex items-center justify-between px-4 py-3"
                    >
                      <div>
                        <span className="text-sm font-medium">v{v.version}</span>
                        <span className="text-xs text-gray-500 ml-3">
                          {new Date(v.created_at).toLocaleString()}
                        </span>
                        {v.change_note && (
                          <p className="text-xs text-gray-400 mt-1">{v.change_note}</p>
                        )}
                      </div>
                      <button
                        onClick={() =>
                          rollbackMutation.mutate({ id: promptDetail.id, version: v.version })
                        }
                        disabled={rollbackMutation.isPending}
                        className="px-3 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded transition-colors"
                      >
                        回滚
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      ) : null}

      {/* YAML Import Modal */}
      {showYamlImport && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 rounded-lg shadow-2xl w-full max-w-2xl p-6 border border-gray-700 m-4">
            <h3 className="text-lg font-semibold text-white mb-4">导入 YAML</h3>
            <textarea
              value={yamlContent}
              onChange={(e) => setYamlContent(e.target.value)}
              className="w-full h-80 bg-gray-800 border border-gray-700 rounded-lg p-4 text-sm font-mono resize-none focus:border-blue-500 focus:outline-none"
              placeholder="粘贴 YAML 内容..."
            />
            <div className="flex justify-end gap-3 mt-4">
              <button
                onClick={() => {
                  setShowYamlImport(false);
                  setYamlContent('');
                }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm"
              >
                取消
              </button>
              <button
                onClick={() => importMutation.mutate(yamlContent)}
                disabled={!yamlContent.trim() || importMutation.isPending}
                className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded-lg text-sm disabled:opacity-50"
              >
                {importMutation.isPending ? '导入中...' : '确认导入'}
              </button>
            </div>
          </div>
        </div>
      )}
    </PageLayout>
  );
};

export default PromptsPage;
