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
        """定时更新关注列表中所有股票的价格（批量并发）"""
        logger.info("Starting scheduled watchlist price update")
        with Session(engine) as session:
            statement = select(Watchlist)
            items = session.exec(statement).all()

            if not items:
                logger.info("No stocks in watchlist")
                return

            # 批量并发获取价格，使用 asyncio.gather
            async def fetch_price(item):
                try:
                    price_info = await MarketRouter.get_stock_price(item.symbol)
                    logger.info("Updated price for watchlist item", symbol=item.symbol, price=price_info.price)
                    return {"symbol": item.symbol, "success": True, "price": price_info.price}
                except Exception as e:
                    logger.error("Failed to update price for watchlist item", symbol=item.symbol, error=str(e))
                    return {"symbol": item.symbol, "success": False, "error": str(e)}

            # 并发获取所有价格（无需 sleep，MarketRouter 内部有缓存和限流）
            results = await asyncio.gather(*[fetch_price(item) for item in items], return_exceptions=True)

            # 统计结果
            success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
            logger.info(
                "Watchlist price update completed",
                total=len(items),
                success=success_count,
                failed=len(items) - success_count
            )

    async def run_daily_analysis(self):
        """每日自动对 Watchlist 中所有股票进行分析"""
        if self._analysis_running:
            logger.warning("Daily analysis already running, skipping")
            return

        self._analysis_running = True
        logger.info("Starting daily watchlist analysis")

        try:
            # 延迟导入避免循环依赖
            from services.synthesizer import synthesizer, SynthesisContext
            from services.graph_executor import execute_trading_graph

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

                    # 使用统一的图执行器
                    result = await execute_trading_graph(
                        symbol=item.symbol,
                        trade_date=trade_date,
                        analysis_level="L2",
                        use_planner=True,
                        debug=False,
                    )

                    # 构建合成上下文
                    synthesis_context = SynthesisContext(
                        analysis_level="L2",
                        task_id=task_id,
                        elapsed_seconds=result.elapsed_seconds,
                        analysts_used=list(result.agent_reports.keys()),
                        market=MarketRouter.get_market(item.symbol),
                    )

                    # 合成结果
                    final_json = await synthesizer.synthesize(item.symbol, result.agent_reports, synthesis_context)
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

                    # 触发推送通知（不影响主流程）
                    try:
                        from services.notification_service import notification_service
                        summary_text = final_json.get("recommendation", {}).get("reasoning", "")[:300]
                        await notification_service.notify_analysis_complete(
                            symbol=item.symbol,
                            signal=final_json.get("signal", "Hold"),
                            confidence=final_json.get("confidence", 50),
                            summary=summary_text,
                        )
                    except Exception as notif_err:
                        logger.warning("Failed to send notification", error=str(notif_err))

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
        from services.synthesizer import synthesizer, SynthesisContext
        from services.graph_executor import execute_trading_graph

        task_id = f"manual_{symbol}_{uuid.uuid4().hex[:8]}"
        trade_date = date.today().isoformat()
        start_time = time.time()

        try:
            # 使用统一的图执行器
            result = await execute_trading_graph(
                symbol=symbol,
                trade_date=trade_date,
                analysis_level="L2",
                use_planner=True,
                debug=False,
            )

            # 构建合成上下文
            market = MarketRouter.get_market(symbol)
            synthesis_context = SynthesisContext(
                analysis_level="L2",
                task_id=task_id,
                elapsed_seconds=result.elapsed_seconds,
                analysts_used=list(result.agent_reports.keys()),
                market=market,
            )

            final_json = await synthesizer.synthesize(symbol, result.agent_reports, synthesis_context)
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

        # 北向资金板块数据采集：每日 15:30（收盘后）
        self.scheduler.add_job(
            self._collect_sector_data,
            CronTrigger(hour=15, minute=30, day_of_week="mon-fri"),
            id="collect_north_sector_data",
            replace_existing=True,
        )
        logger.info("North money sector data collection scheduled (15:30 weekdays)")

        self.scheduler.start()
        logger.info("Watchlist scheduler started")

    async def _collect_sector_data(self):
        """采集北向资金板块数据（定时任务回调）"""
        try:
            from services.north_money_service import north_money_service
            result = await north_money_service.save_sector_data()
            logger.info("Sector data collection completed", result=result)
        except Exception as e:
            logger.error("Sector data collection failed", error=str(e))

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
