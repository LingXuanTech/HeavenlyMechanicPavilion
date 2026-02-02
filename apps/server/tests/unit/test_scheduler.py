"""
WatchlistScheduler 单元测试

覆盖:
1. 调度器初始化
2. 市场指数更新
3. 关注列表价格更新
4. 每日分析
5. 手动触发分析
6. 启动/关闭
7. 获取任务列表
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from services.scheduler import WatchlistScheduler, watchlist_scheduler


# =============================================================================
# 初始化测试
# =============================================================================

class TestWatchlistSchedulerInit:
    """调度器初始化测试"""

    def test_init(self):
        """初始化调度器"""
        scheduler = WatchlistScheduler()

        assert scheduler.scheduler is not None
        assert scheduler._analysis_running is False

    def test_singleton_exists(self):
        """全局单例存在"""
        assert watchlist_scheduler is not None
        assert isinstance(watchlist_scheduler, WatchlistScheduler)


# =============================================================================
# 市场指数更新测试
# =============================================================================

class TestUpdateMarketIndices:
    """市场指数更新测试"""

    @pytest.fixture
    def scheduler(self):
        """创建调度器实例"""
        return WatchlistScheduler()

    @pytest.mark.asyncio
    async def test_update_market_indices_success(self, scheduler):
        """成功更新市场指数"""
        mock_watcher = MagicMock()
        mock_watcher.get_all_indices = AsyncMock(return_value=[
            {"symbol": "^DJI", "price": 40000},
            {"symbol": "^GSPC", "price": 5000},
        ])

        with patch("services.market_watcher.market_watcher", mock_watcher):
            await scheduler.update_market_indices()

        mock_watcher.get_all_indices.assert_called_once_with(force_refresh=True)

    @pytest.mark.asyncio
    async def test_update_market_indices_error(self, scheduler):
        """更新市场指数失败"""
        mock_watcher = MagicMock()
        mock_watcher.get_all_indices = AsyncMock(side_effect=Exception("API Error"))

        with patch("services.market_watcher.market_watcher", mock_watcher):
            # 不应抛出异常
            await scheduler.update_market_indices()


# =============================================================================
# 关注列表价格更新测试
# =============================================================================

class TestUpdateWatchlistPrices:
    """关注列表价格更新测试"""

    @pytest.fixture
    def scheduler(self):
        return WatchlistScheduler()

    @pytest.mark.asyncio
    async def test_update_watchlist_prices_empty(self, scheduler):
        """空关注列表"""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.exec.return_value.all.return_value = []

        with patch("services.scheduler.Session", return_value=mock_session):
            await scheduler.update_watchlist_prices()

    @pytest.mark.asyncio
    async def test_update_watchlist_prices_with_items(self, scheduler):
        """有关注项目"""
        mock_item = MagicMock()
        mock_item.symbol = "AAPL"

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.exec.return_value.all.return_value = [mock_item]

        mock_price_info = MagicMock()
        mock_price_info.price = 150.0

        with patch("services.scheduler.Session", return_value=mock_session):
            with patch("services.scheduler.MarketRouter.get_stock_price", new_callable=AsyncMock) as mock_get_price:
                mock_get_price.return_value = mock_price_info
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    await scheduler.update_watchlist_prices()

        mock_get_price.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_update_watchlist_prices_error_handling(self, scheduler):
        """价格更新错误处理"""
        mock_item = MagicMock()
        mock_item.symbol = "INVALID"

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.exec.return_value.all.return_value = [mock_item]

        with patch("services.scheduler.Session", return_value=mock_session):
            with patch("services.scheduler.MarketRouter.get_stock_price", new_callable=AsyncMock) as mock_get_price:
                mock_get_price.side_effect = Exception("Price fetch error")
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    # 不应抛出异常
                    await scheduler.update_watchlist_prices()


# =============================================================================
# 每日分析测试
# =============================================================================

class TestRunDailyAnalysis:
    """每日分析测试"""

    @pytest.fixture
    def scheduler(self):
        sched = WatchlistScheduler()
        sched._analysis_running = False
        return sched

    @pytest.mark.asyncio
    async def test_skip_if_already_running(self, scheduler):
        """已在运行时跳过"""
        scheduler._analysis_running = True

        await scheduler.run_daily_analysis()

        # 应该直接返回，不执行任何操作
        assert scheduler._analysis_running is True

    @pytest.mark.asyncio
    async def test_empty_watchlist(self, scheduler):
        """空关注列表"""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.exec.return_value.all.return_value = []

        with patch("services.scheduler.Session", return_value=mock_session):
            await scheduler.run_daily_analysis()

        assert scheduler._analysis_running is False

    @pytest.mark.asyncio
    async def test_analysis_running_flag(self, scheduler):
        """分析运行标志管理"""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.exec.return_value.all.return_value = []

        with patch("services.scheduler.Session", return_value=mock_session):
            assert scheduler._analysis_running is False
            await scheduler.run_daily_analysis()
            assert scheduler._analysis_running is False


# =============================================================================
# 启动/关闭测试
# =============================================================================

class TestSchedulerStartStop:
    """调度器启动/关闭测试"""

    @pytest.fixture
    def scheduler(self):
        return WatchlistScheduler()

    def test_start_adds_jobs(self, scheduler):
        """启动添加任务"""
        mock_apscheduler = MagicMock()
        scheduler.scheduler = mock_apscheduler

        with patch("services.scheduler.settings") as mock_settings:
            mock_settings.DAILY_ANALYSIS_ENABLED = False

            scheduler.start()

        # 应该添加至少 2 个任务（市场指数 + 价格更新）
        assert mock_apscheduler.add_job.call_count >= 2
        mock_apscheduler.start.assert_called_once()

    def test_start_with_daily_analysis(self, scheduler):
        """启动带每日分析"""
        mock_apscheduler = MagicMock()
        scheduler.scheduler = mock_apscheduler

        with patch("services.scheduler.settings") as mock_settings:
            mock_settings.DAILY_ANALYSIS_ENABLED = True
            mock_settings.DAILY_ANALYSIS_HOUR = 9
            mock_settings.DAILY_ANALYSIS_MINUTE = 0

            scheduler.start()

        # 应该添加 3 个任务
        assert mock_apscheduler.add_job.call_count >= 3

    def test_shutdown(self, scheduler):
        """关闭调度器"""
        mock_apscheduler = MagicMock()
        scheduler.scheduler = mock_apscheduler

        scheduler.shutdown()

        mock_apscheduler.shutdown.assert_called_once()


# =============================================================================
# 获取任务列表测试
# =============================================================================

class TestGetJobs:
    """获取任务列表测试"""

    @pytest.fixture
    def scheduler(self):
        return WatchlistScheduler()

    def test_get_jobs_empty(self, scheduler):
        """空任务列表"""
        mock_apscheduler = MagicMock()
        mock_apscheduler.get_jobs.return_value = []
        scheduler.scheduler = mock_apscheduler

        jobs = scheduler.get_jobs()

        assert jobs == []

    def test_get_jobs_with_items(self, scheduler):
        """有任务"""
        mock_job1 = MagicMock()
        mock_job1.id = "update_market_indices"
        mock_job1.next_run_time = datetime(2026, 2, 2, 10, 0, 0)
        mock_job1.trigger = "interval[0:02:00]"

        mock_job2 = MagicMock()
        mock_job2.id = "update_watchlist_prices"
        mock_job2.next_run_time = None
        mock_job2.trigger = "cron[minute='*/5']"

        mock_apscheduler = MagicMock()
        mock_apscheduler.get_jobs.return_value = [mock_job1, mock_job2]
        scheduler.scheduler = mock_apscheduler

        jobs = scheduler.get_jobs()

        assert len(jobs) == 2
        assert jobs[0]["id"] == "update_market_indices"
        assert jobs[0]["next_run_time"] == "2026-02-02T10:00:00"
        assert jobs[1]["id"] == "update_watchlist_prices"
        assert jobs[1]["next_run_time"] is None


# =============================================================================
# 手动触发分析测试
# =============================================================================

class TestTriggerSingleAnalysis:
    """手动触发分析测试"""

    @pytest.fixture
    def scheduler(self):
        return WatchlistScheduler()

    @pytest.mark.asyncio
    async def test_trigger_analysis_error(self, scheduler):
        """触发分析失败"""
        with patch("tradingagents.graph.trading_graph.TradingAgentsGraph", side_effect=Exception("Graph error")):
            with pytest.raises(Exception) as exc_info:
                await scheduler.trigger_single_analysis("AAPL")

            assert "Graph error" in str(exc_info.value)
