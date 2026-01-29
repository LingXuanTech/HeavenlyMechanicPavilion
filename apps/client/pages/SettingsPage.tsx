/**
 * 设置页面
 *
 * 应用程序通用设置
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Settings, User, Bell, Shield, Palette, Database } from 'lucide-react';

const SettingsPage: React.FC = () => {
  const navigate = useNavigate();

  const settingsSections = [
    {
      icon: User,
      title: 'Account',
      description: '管理账户信息和登录设置',
      items: ['个人资料', '邮箱验证', '密码修改'],
    },
    {
      icon: Bell,
      title: 'Notifications',
      description: '配置通知和提醒方式',
      items: ['分析完成通知', '价格预警', '市场动态推送'],
    },
    {
      icon: Shield,
      title: 'Security',
      description: '安全和隐私设置',
      items: ['两步验证', 'Passkey 管理', '登录历史'],
    },
    {
      icon: Palette,
      title: 'Appearance',
      description: '界面显示和主题设置',
      items: ['深色模式', '数据显示精度', '图表样式'],
    },
    {
      icon: Database,
      title: 'Data',
      description: '数据存储和缓存管理',
      items: ['清除缓存', '导出数据', '同步设置'],
    },
  ];

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
            <div className="p-2 bg-gray-500/10 rounded-lg">
              <Settings className="w-5 h-5 text-gray-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Settings</h1>
              <p className="text-xs text-gray-500">应用程序设置</p>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {settingsSections.map((section) => (
            <div
              key={section.title}
              className="bg-gray-800/50 rounded-xl border border-gray-700 overflow-hidden"
            >
              <div className="p-4 border-b border-gray-700">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-gray-700 rounded-lg">
                    <section.icon className="w-5 h-5 text-gray-400" />
                  </div>
                  <div>
                    <h3 className="font-medium text-white">{section.title}</h3>
                    <p className="text-xs text-gray-500">{section.description}</p>
                  </div>
                </div>
              </div>

              <div className="divide-y divide-gray-700">
                {section.items.map((item) => (
                  <button
                    key={item}
                    className="w-full px-4 py-3 text-left text-sm text-gray-300 hover:bg-gray-700/50 transition-colors flex items-center justify-between"
                  >
                    <span>{item}</span>
                    <span className="text-gray-600">→</span>
                  </button>
                ))}
              </div>
            </div>
          ))}

          {/* Placeholder Notice */}
          <div className="bg-yellow-900/20 border border-yellow-700/50 rounded-xl p-4">
            <p className="text-sm text-yellow-400">
              ⚠️ 设置功能正在开发中，部分选项可能暂不可用。
            </p>
          </div>
        </div>
      </main>
    </div>
  );
};

export default SettingsPage;
