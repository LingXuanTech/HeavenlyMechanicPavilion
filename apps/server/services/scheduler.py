import asyncio
import json
import time
import uuid
import structlog
from datetime import date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import Session, select

from config.settings import settings
from db.models import Watchlist, AnalysisResult, engine
from services.data_router import MarketRouter

logger = structlog.get_logger()


class WatchlistScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._analysis_running = False

    async def update_market_indices(self):
        """定时更新全球市场指数"""
        try:
            from services.market_watcher import market_watcher
            indices = await market_watcher.get_all_indices(force_refresh=True)
            logger.info("Market indices updated", count=len(indices))
        except Exception as e:
            logger.error("Failed to update market indices", error=str(e))

    async def update_watchlist_prices(self):
        """定时更新关注列表中所有股票的价格"""
        logger.info("Starting scheduled watchlist price update")
        with Session(engine) as session:
            statement = select(Watchlist)
            items = session.exec(statement).all()

            for item in items:
                try:
                    price_info = await MarketRouter.get_stock_price(item.symbol)
                    logger.info("Updated price for watchlist item", symbol=item.symbol, price=price_info.price)
                except Exception as e:
                    logger.error("Failed to update price for watchlist item", symbol=item.symbol, error=str(e))

                # Avoid hitting rate limits
                await asyncio.sleep(1)

    async def run_daily_analysis(self):
        """每日自动对 Watchlist 中所有股票进行分析"""
        if self._analysis_running:
            logger.warning("Daily analysis already running, skipping")
            return

        self._analysis_running = True
        logger.info("Starting daily watchlist analysis")

        try:
            # 延迟导入避免循环依赖
            from services.synthesizer import synthesizer
            from tradingagents.graph.trading_graph import TradingAgentsGraph
            from tradingagents.default_config import DEFAULT_CONFIG

            with Session(engine) as session:
                statement = select(Watchlist)
                items = session.exec(statement).all()

            if not items:
                logger.info("No stocks in watchlist, skipping daily analysis")
                return

            trade_date = date.today().isoformat()
            total = len(items)
            completed = 0
            failed = 0

            for item in items:
                task_id = f"daily_{item.symbol}_{uuid.uuid4().hex[:8]}"
                start_time = time.time()

                try:
                    logger.info("Starting daily analysis", symbol=item.symbol, task_id=task_id, progress=f"{completed+1}/{total}")

                    # 初始化图
                    config = DEFAULT_CONFIG.copy()
                    ta = TradingAgentsGraph(debug=False, config=config)

                    # 执行分析
                    init_state = ta.propagator.create_initial_state(item.symbol, trade_date)
                    args = ta.propagator.get_graph_args()

                    agent_reports = {}

                    for chunk in ta.graph.stream(init_state, **args):
                        for node_name, node_data in chunk.items():
                            if "macro_report" in node_data:
                                agent_reports["macro"] = node_data["macro_report"]
                            if "market_report" in node_data:
                                agent_reports["market"] = node_data["market_report"]
                            if "news_report" in node_data:
                                agent_reports["news"] = node_data["news_report"]
                            if "fundamentals_report" in node_data:
                                agent_reports["fundamentals"] = node_data["fundamentals_report"]
                            if "portfolio_report" in node_data:
                                agent_reports["portfolio"] = node_data["portfolio_report"]

                    # 合成结果
                    final_json = await synthesizer.synthesize(item.symbol, agent_reports)
                    elapsed_seconds = round(time.time() - start_time, 2)

                    # 保存到数据库
                    with Session(engine) as session:
                        analysis_result = AnalysisResult(
                            symbol=item.symbol,
                            date=trade_date,
                            signal=final_json.get("signal", "Hold"),
                            confidence=final_json.get("confidence", 50),
                            full_report_json=json.dumps(final_json, ensure_ascii=False),
                            anchor_script=final_json.get("anchor_script", ""),
                            task_id=task_id,
                            status="completed",
                            elapsed_seconds=elapsed_seconds,
                        )
                        session.add(analysis_result)
                        session.commit()

                    completed += 1
                    logger.info("Daily analysis completed", symbol=item.symbol, elapsed_seconds=elapsed_seconds)

                except Exception as e:
                    failed += 1
                    elapsed_seconds = round(time.time() - start_time, 2)
                    logger.error("Daily analysis failed", symbol=item.symbol, error=str(e))

                    # 保存失败记录
                    with Session(engine) as session:
                        analysis_result = AnalysisResult(
                            symbol=item.symbol,
                            date=trade_date,
                            signal="Error",
                            confidence=0,
                            full_report_json="{}",
                            anchor_script="",
                            task_id=task_id,
                            status="failed",
                            error_message=str(e),
                            elapsed_seconds=elapsed_seconds,
                        )
                        session.add(analysis_result)
                        session.commit()

                # 错开请求，避免 API 限流（每个分析间隔 30 秒）
                await asyncio.sleep(30)

            logger.info("Daily analysis completed", total=total, completed=completed, failed=failed)

        finally:
            self._analysis_running = False

    async def trigger_single_analysis(self, symbol: str):
        """手动触发单个股票的分析（供管理 API 调用）"""
        from services.synthesizer import synthesizer
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG

        task_id = f"manual_{symbol}_{uuid.uuid4().hex[:8]}"
        trade_date = date.today().isoformat()
        start_time = time.time()

        try:
            config = DEFAULT_CONFIG.copy()
            ta = TradingAgentsGraph(debug=False, config=config)

            init_state = ta.propagator.create_initial_state(symbol, trade_date)
            args = ta.propagator.get_graph_args()

            agent_reports = {}

            for chunk in ta.graph.stream(init_state, **args):
                for node_name, node_data in chunk.items():
                    if "macro_report" in node_data:
                        agent_reports["macro"] = node_data["macro_report"]
                    if "market_report" in node_data:
                        agent_reports["market"] = node_data["market_report"]
                    if "news_report" in node_data:
                        agent_reports["news"] = node_data["news_report"]
                    if "fundamentals_report" in node_data:
                        agent_reports["fundamentals"] = node_data["fundamentals_report"]
                    if "portfolio_report" in node_data:
                        agent_reports["portfolio"] = node_data["portfolio_report"]

            final_json = await synthesizer.synthesize(symbol, agent_reports)
            elapsed_seconds = round(time.time() - start_time, 2)

            with Session(engine) as session:
                analysis_result = AnalysisResult(
                    symbol=symbol,
                    date=trade_date,
                    signal=final_json.get("signal", "Hold"),
                    confidence=final_json.get("confidence", 50),
                    full_report_json=json.dumps(final_json, ensure_ascii=False),
                    anchor_script=final_json.get("anchor_script", ""),
                    task_id=task_id,
                    status="completed",
                    elapsed_seconds=elapsed_seconds,
                )
                session.add(analysis_result)
                session.commit()

            return {"task_id": task_id, "status": "completed", "elapsed_seconds": elapsed_seconds}

        except Exception as e:
            logger.error("Manual analysis failed", symbol=symbol, error=str(e))
            raise

    def start(self):
        """启动调度器"""
        # 市场指数更新任务：每 2 分钟
        self.scheduler.add_job(
            self.update_market_indices,
            IntervalTrigger(minutes=2),
            id="update_market_indices",
            replace_existing=True
        )
        logger.info("Market indices update scheduled (every 2 minutes)")

        # 价格更新任务：每 5 分钟
        self.scheduler.add_job(
            self.update_watchlist_prices,
            CronTrigger(minute="*/5"),
            id="update_watchlist_prices",
            replace_existing=True
        )

        # 每日分析任务：可配置时间（默认关闭）
        if settings.DAILY_ANALYSIS_ENABLED:
            self.scheduler.add_job(
                self.run_daily_analysis,
                CronTrigger(
                    hour=settings.DAILY_ANALYSIS_HOUR,
                    minute=settings.DAILY_ANALYSIS_MINUTE
                ),
                id="daily_watchlist_analysis",
                replace_existing=True
            )
            logger.info(
                "Daily analysis scheduled",
                time=f"{settings.DAILY_ANALYSIS_HOUR:02d}:{settings.DAILY_ANALYSIS_MINUTE:02d}"
            )

        self.scheduler.start()
        logger.info("Watchlist scheduler started")

    def shutdown(self):
        """关闭调度器"""
        self.scheduler.shutdown()
        logger.info("Watchlist scheduler shut down")

    def get_jobs(self):
        """获取所有调度任务"""
        return [
            {
                "id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in self.scheduler.get_jobs()
        ]


watchlist_scheduler = WatchlistScheduler()
