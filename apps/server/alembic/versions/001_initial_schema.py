"""初始数据库架构

Revision ID: 001
Revises: 
Create Date: 2026-02-06

此迁移脚本创建所有初始数据库表，包括：
- 基础业务表：watchlist, analysisresult, chathistory
- AI 配置表：ai_providers, ai_model_configs
- Prompt 配置表：agent_prompts, prompt_versions
- 用户认证表：users, oauth_accounts, webauthn_credentials, refresh_tokens
- 预测追踪表：prediction_outcomes, agent_performance, model_performance
- 赛马分析表：racing_analysis_results
- 回测结果表：backtest_results
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移 - 创建所有表"""
    
    # ============ 基础业务表 ============
    
    # watchlist 表
    op.create_table(
        'watchlist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('market', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_watchlist_symbol'), 'watchlist', ['symbol'], unique=True)
    
    # analysisresult 表
    op.create_table(
        'analysisresult',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('date', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('signal', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('confidence', sa.Integer(), nullable=False),
        sa.Column('full_report_json', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('anchor_script', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('task_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('error_message', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('elapsed_seconds', sa.Float(), nullable=True),
        sa.Column('token_usage', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analysisresult_symbol'), 'analysisresult', ['symbol'], unique=False)
    op.create_index(op.f('ix_analysisresult_date'), 'analysisresult', ['date'], unique=False)
    op.create_index(op.f('ix_analysisresult_task_id'), 'analysisresult', ['task_id'], unique=False)
    op.create_index('ix_analysis_symbol_created', 'analysisresult', ['symbol', 'created_at'], unique=False)
    op.create_index('ix_analysis_symbol_status', 'analysisresult', ['symbol', 'status'], unique=False)
    
    # chathistory 表
    op.create_table(
        'chathistory',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('role', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('content', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chathistory_thread_id'), 'chathistory', ['thread_id'], unique=False)
    
    # ============ AI 配置表 ============
    
    # ai_providers 表
    op.create_table(
        'ai_providers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('provider_type', sa.Enum('openai', 'openai_compatible', 'google', 'anthropic', 'deepseek', name='aiprovidertype'), nullable=False),
        sa.Column('base_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('api_key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('models', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_providers_name'), 'ai_providers', ['name'], unique=True)
    
    # ai_model_configs 表
    op.create_table(
        'ai_model_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=True),
        sa.Column('model_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['provider_id'], ['ai_providers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_model_configs_config_key'), 'ai_model_configs', ['config_key'], unique=True)
    
    # ============ Prompt 配置表 ============
    
    # agent_prompts 表
    op.create_table(
        'agent_prompts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('category', sa.Enum('analyst', 'researcher', 'manager', 'risk', 'trader', 'synthesizer', name='agentcategory'), nullable=False),
        sa.Column('display_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('system_prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('user_prompt_template', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('available_variables', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_prompts_agent_key'), 'agent_prompts', ['agent_key'], unique=False)
    op.create_index('ix_prompt_agent_active', 'agent_prompts', ['agent_key', 'is_active'], unique=False)
    
    # prompt_versions 表
    op.create_table(
        'prompt_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('prompt_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('system_prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('user_prompt_template', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('change_note', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(['prompt_id'], ['agent_prompts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prompt_versions_prompt_id'), 'prompt_versions', ['prompt_id'], unique=False)
    
    # ============ 用户认证表 ============
    
    # users 表
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('hashed_password', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('display_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('avatar_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('email_verified', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # oauth_accounts 表
    op.create_table(
        'oauth_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('provider_user_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('access_token', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('refresh_token', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_oauth_accounts_user_id'), 'oauth_accounts', ['user_id'], unique=False)
    op.create_index('ix_oauth_provider_user', 'oauth_accounts', ['provider', 'provider_user_id'], unique=False)
    
    # webauthn_credentials 表
    op.create_table(
        'webauthn_credentials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('credential_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('public_key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('sign_count', sa.Integer(), nullable=False),
        sa.Column('device_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webauthn_credentials_user_id'), 'webauthn_credentials', ['user_id'], unique=False)
    op.create_index(op.f('ix_webauthn_credentials_credential_id'), 'webauthn_credentials', ['credential_id'], unique=True)
    
    # refresh_tokens 表
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_token'), 'refresh_tokens', ['token'], unique=True)
    
    # ============ 预测追踪表 ============
    
    # prediction_outcomes 表
    op.create_table(
        'prediction_outcomes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('analysis_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('prediction_date', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('signal', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('confidence', sa.Integer(), nullable=False),
        sa.Column('target_price', sa.Float(), nullable=True),
        sa.Column('stop_loss', sa.Float(), nullable=True),
        sa.Column('entry_price', sa.Float(), nullable=True),
        sa.Column('agent_key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('outcome_date', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('actual_price', sa.Float(), nullable=True),
        sa.Column('actual_return', sa.Float(), nullable=True),
        sa.Column('outcome', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('return_vs_benchmark', sa.Float(), nullable=True),
        sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['analysis_id'], ['analysisresult.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prediction_outcomes_analysis_id'), 'prediction_outcomes', ['analysis_id'], unique=False)
    op.create_index(op.f('ix_prediction_outcomes_symbol'), 'prediction_outcomes', ['symbol'], unique=False)
    op.create_index(op.f('ix_prediction_outcomes_prediction_date'), 'prediction_outcomes', ['prediction_date'], unique=False)
    op.create_index('ix_prediction_symbol_date', 'prediction_outcomes', ['symbol', 'prediction_date'], unique=False)
    op.create_index('ix_prediction_agent', 'prediction_outcomes', ['agent_key'], unique=False)
    
    # agent_performance 表
    op.create_table(
        'agent_performance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('period_start', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('period_end', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('total_predictions', sa.Integer(), nullable=False),
        sa.Column('correct_predictions', sa.Integer(), nullable=False),
        sa.Column('win_rate', sa.Float(), nullable=False),
        sa.Column('avg_return', sa.Float(), nullable=False),
        sa.Column('avg_confidence', sa.Float(), nullable=False),
        sa.Column('strong_buy_accuracy', sa.Float(), nullable=True),
        sa.Column('buy_accuracy', sa.Float(), nullable=True),
        sa.Column('hold_accuracy', sa.Float(), nullable=True),
        sa.Column('sell_accuracy', sa.Float(), nullable=True),
        sa.Column('strong_sell_accuracy', sa.Float(), nullable=True),
        sa.Column('overconfidence_bias', sa.Float(), nullable=True),
        sa.Column('direction_bias', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('calculated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_performance_agent_key'), 'agent_performance', ['agent_key'], unique=False)
    op.create_index(op.f('ix_agent_performance_period_start'), 'agent_performance', ['period_start'], unique=False)
    op.create_index('ix_agent_perf_key_period', 'agent_performance', ['agent_key', 'period_start'], unique=False)
    
    # model_performance 表
    op.create_table(
        'model_performance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('model_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('period_start', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('period_end', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('total_predictions', sa.Integer(), nullable=False),
        sa.Column('correct_predictions', sa.Integer(), nullable=False),
        sa.Column('win_rate', sa.Float(), nullable=False),
        sa.Column('avg_return', sa.Float(), nullable=False),
        sa.Column('avg_confidence', sa.Float(), nullable=False),
        sa.Column('avg_response_time', sa.Float(), nullable=False),
        sa.Column('consensus_agreement_rate', sa.Float(), nullable=False),
        sa.Column('strong_buy_accuracy', sa.Float(), nullable=True),
        sa.Column('buy_accuracy', sa.Float(), nullable=True),
        sa.Column('sell_accuracy', sa.Float(), nullable=True),
        sa.Column('overconfidence_bias', sa.Float(), nullable=True),
        sa.Column('direction_bias', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('calculated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_performance_model_key'), 'model_performance', ['model_key'], unique=False)
    op.create_index(op.f('ix_model_performance_period_start'), 'model_performance', ['period_start'], unique=False)
    op.create_index('ix_model_perf_key_period', 'model_performance', ['model_key', 'period_start'], unique=False)
    
    # ============ 赛马分析表 ============
    
    # racing_analysis_results 表
    op.create_table(
        'racing_analysis_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('market', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('analysis_date', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('consensus_signal', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('consensus_confidence', sa.Integer(), nullable=False),
        sa.Column('consensus_method', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('agreement_rate', sa.Float(), nullable=False),
        sa.Column('model_results_json', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('dissenting_models', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('total_models', sa.Integer(), nullable=False),
        sa.Column('successful_models', sa.Integer(), nullable=False),
        sa.Column('total_elapsed_seconds', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_racing_analysis_results_symbol'), 'racing_analysis_results', ['symbol'], unique=False)
    op.create_index(op.f('ix_racing_analysis_results_analysis_date'), 'racing_analysis_results', ['analysis_date'], unique=False)
    op.create_index('ix_racing_symbol_created', 'racing_analysis_results', ['symbol', 'created_at'], unique=False)
    
    # ============ 回测结果表 ============
    
    # backtest_results 表
    op.create_table(
        'backtest_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('market', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('start_date', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('end_date', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('initial_capital', sa.Float(), nullable=False),
        sa.Column('final_capital', sa.Float(), nullable=False),
        sa.Column('total_return_pct', sa.Float(), nullable=False),
        sa.Column('annualized_return_pct', sa.Float(), nullable=False),
        sa.Column('max_drawdown_pct', sa.Float(), nullable=False),
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=False),
        sa.Column('winning_trades', sa.Integer(), nullable=False),
        sa.Column('losing_trades', sa.Integer(), nullable=False),
        sa.Column('win_rate', sa.Float(), nullable=False),
        sa.Column('avg_win_pct', sa.Float(), nullable=False),
        sa.Column('avg_loss_pct', sa.Float(), nullable=False),
        sa.Column('profit_factor', sa.Float(), nullable=True),
        sa.Column('benchmark_return_pct', sa.Float(), nullable=True),
        sa.Column('alpha', sa.Float(), nullable=True),
        sa.Column('trades_json', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('holding_days', sa.Integer(), nullable=False),
        sa.Column('stop_loss_pct', sa.Float(), nullable=False),
        sa.Column('take_profit_pct', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backtest_results_symbol'), 'backtest_results', ['symbol'], unique=False)
    op.create_index('ix_backtest_symbol_created', 'backtest_results', ['symbol', 'created_at'], unique=False)


def downgrade() -> None:
    """降级迁移 - 删除所有表"""
    
    # 按照依赖关系的逆序删除表
    
    # 回测结果表
    op.drop_index('ix_backtest_symbol_created', table_name='backtest_results')
    op.drop_index(op.f('ix_backtest_results_symbol'), table_name='backtest_results')
    op.drop_table('backtest_results')
    
    # 赛马分析表
    op.drop_index('ix_racing_symbol_created', table_name='racing_analysis_results')
    op.drop_index(op.f('ix_racing_analysis_results_analysis_date'), table_name='racing_analysis_results')
    op.drop_index(op.f('ix_racing_analysis_results_symbol'), table_name='racing_analysis_results')
    op.drop_table('racing_analysis_results')
    
    # 预测追踪表
    op.drop_index('ix_model_perf_key_period', table_name='model_performance')
    op.drop_index(op.f('ix_model_performance_period_start'), table_name='model_performance')
    op.drop_index(op.f('ix_model_performance_model_key'), table_name='model_performance')
    op.drop_table('model_performance')
    
    op.drop_index('ix_agent_perf_key_period', table_name='agent_performance')
    op.drop_index(op.f('ix_agent_performance_period_start'), table_name='agent_performance')
    op.drop_index(op.f('ix_agent_performance_agent_key'), table_name='agent_performance')
    op.drop_table('agent_performance')
    
    op.drop_index('ix_prediction_agent', table_name='prediction_outcomes')
    op.drop_index('ix_prediction_symbol_date', table_name='prediction_outcomes')
    op.drop_index(op.f('ix_prediction_outcomes_prediction_date'), table_name='prediction_outcomes')
    op.drop_index(op.f('ix_prediction_outcomes_symbol'), table_name='prediction_outcomes')
    op.drop_index(op.f('ix_prediction_outcomes_analysis_id'), table_name='prediction_outcomes')
    op.drop_table('prediction_outcomes')
    
    # 用户认证表
    op.drop_index(op.f('ix_refresh_tokens_token'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    
    op.drop_index(op.f('ix_webauthn_credentials_credential_id'), table_name='webauthn_credentials')
    op.drop_index(op.f('ix_webauthn_credentials_user_id'), table_name='webauthn_credentials')
    op.drop_table('webauthn_credentials')
    
    op.drop_index('ix_oauth_provider_user', table_name='oauth_accounts')
    op.drop_index(op.f('ix_oauth_accounts_user_id'), table_name='oauth_accounts')
    op.drop_table('oauth_accounts')
    
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    
    # Prompt 配置表
    op.drop_index(op.f('ix_prompt_versions_prompt_id'), table_name='prompt_versions')
    op.drop_table('prompt_versions')
    
    op.drop_index('ix_prompt_agent_active', table_name='agent_prompts')
    op.drop_index(op.f('ix_agent_prompts_agent_key'), table_name='agent_prompts')
    op.drop_table('agent_prompts')
    
    # AI 配置表
    op.drop_index(op.f('ix_ai_model_configs_config_key'), table_name='ai_model_configs')
    op.drop_table('ai_model_configs')
    
    op.drop_index(op.f('ix_ai_providers_name'), table_name='ai_providers')
    op.drop_table('ai_providers')
    
    # 基础业务表
    op.drop_index(op.f('ix_chathistory_thread_id'), table_name='chathistory')
    op.drop_table('chathistory')
    
    op.drop_index('ix_analysis_symbol_status', table_name='analysisresult')
    op.drop_index('ix_analysis_symbol_created', table_name='analysisresult')
    op.drop_index(op.f('ix_analysisresult_task_id'), table_name='analysisresult')
    op.drop_index(op.f('ix_analysisresult_date'), table_name='analysisresult')
    op.drop_index(op.f('ix_analysisresult_symbol'), table_name='analysisresult')
    op.drop_table('analysisresult')
    
    op.drop_index(op.f('ix_watchlist_symbol'), table_name='watchlist')
    op.drop_table('watchlist')
    
    # 删除枚举类型（PostgreSQL 需要）
    # 注意：SQLite 不支持枚举类型，会自动忽略
    op.execute("DROP TYPE IF EXISTS aiprovidertype")
    op.execute("DROP TYPE IF EXISTS agentcategory")
