"""Analysis Worker

独立的 worker 进程，从任务队列消费分析任务并执行。

使用方式：
    # 启动单个 worker
    python -m workers.analysis_worker

    # 启动多个 worker（指定名称以区分日志）
    python -m workers.analysis_worker --name worker-1
    python -m workers.analysis_worker --name worker-2

设计：
- 每个 worker 是独立进程，可水平扩展
- 使用 Redis Stream 消费者组实现负载均衡
- 支持优雅关闭（SIGINT/SIGTERM）
- 任务失败自动重试，超过最大重试移入死信队列
"""

import argparse
import asyncio
import os
import signal
import sys
from typing import Optional

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from services.task_queue import task_queue, AnalysisTask
from services.cache_service import cache_service
from services.synthesizer import synthesizer, SynthesisContext
from services.memory_service import memory_service, layered_memory, AnalysisMemory
from services.data_router import MarketRouter
from services.market_analyst_router import MarketAnalystRouter
from services.accuracy_tracker import accuracy_tracker
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from db.models import AnalysisResult, engine
from services.rollout_manager import should_use_subgraph
from sqlmodel import Session
import json
import time

logger = structlog.get_logger(__name__)


class AnalysisWorker:
    """分析任务 Worker"""

    def __init__(self, name: str = "worker-default"):
        self.name = name
        self._running = False
        self._current_task: Optional[AnalysisTask] = None

    async def process_task(self, task: AnalysisTask) -> bool:
        """处理单个分析任务

        Args:
            task: 分析任务

        Returns:
            True 表示成功，False 表示失败
        """
        task_id = task.task_id
        symbol = task.symbol
        start_time = time.time()

        logger.info(
            "Processing analysis task",
            worker=self.name,
            task_id=task_id,
            symbol=symbol,
            analysis_level=task.analysis_level,
        )

        # 初始化任务状态
        await cache_service.set_task(task_id, {"status": "running", "symbol": symbol, "progress": 0})
        await cache_service.init_sse_task(task_id, symbol)

        try:
            # 获取历史反思信息
            historical_reflection = ""
            if memory_service.is_available():
                try:
                    reflection = await memory_service.generate_reflection(symbol)
                    if reflection:
                        historical_reflection = f"""
## 历史分析反思 (基于 {len(reflection.historical_analyses)} 条历史记录)

### 识别的模式
{chr(10).join(f"- {p}" for p in reflection.patterns)}

### 历史教训
{chr(10).join(f"- {l}" for l in reflection.lessons)}

### 置信度调整建议: {reflection.confidence_adjustment:+d}%
"""
                except Exception as ref_err:
                    logger.warning("Failed to load reflection", error=str(ref_err))

            # 初始化 graph
            config = DEFAULT_CONFIG.copy()
            config["analysis_level"] = task.analysis_level
            config["use_planner"] = task.use_planner
            market = MarketRouter.get_market(symbol)

            # 灰度路由逻辑
            effective_use_subgraphs = should_use_subgraph(
                user_id=getattr(task, "user_id", None),
                request_id=task_id,
                force_param=getattr(task, "use_subgraphs", None),
            )
            config["use_subgraphs"] = effective_use_subgraphs
            architecture_mode = "subgraph" if effective_use_subgraphs else "monolith"

            # 选择分析师
            selected_analysts = MarketAnalystRouter.get_analysts(
                symbol=symbol,
                override_analysts=task.override_analysts,
                exclude_analysts=task.exclude_analysts,
            )

            ta = TradingAgentsGraph(
                selected_analysts=selected_analysts,
                debug=True,
                config=config,
                market=market,
            )

            # 初始化状态
            init_state = ta.propagator.create_initial_state(
                symbol, task.trade_date, market=market, historical_reflection=historical_reflection
            )
            args = ta.propagator.get_graph_args()

            agent_reports = {}

            # 执行 graph
            for chunk in ta.graph.stream(init_state, **args):
                for node_name, node_data in chunk.items():
                    logger.debug("Graph node completed", node=node_name, task_id=task_id)

                    stage_map = {
                        "Planner": "stage_analyst",
                        "Macro Analyst": "stage_analyst",
                        "Market Analyst": "stage_analyst",
                        "News Analyst": "stage_analyst",
                        "Fundamentals Analyst": "stage_analyst",
                        "Social Analyst": "stage_analyst",
                        "Sentiment Analyst": "stage_analyst",
                        "Policy Analyst": "stage_analyst",
                        "Fund_flow Analyst": "stage_analyst",
                        "Bull Researcher": "stage_debate",
                        "Bear Researcher": "stage_debate",
                        "Risk Judge": "stage_risk",
                        "Portfolio Agent": "stage_final",
                        "Trader": "stage_final"
                    }

                    current_stage = stage_map.get(node_name, "progress")

                    # 收集报告
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
                    if "retail_sentiment_report" in node_data:
                        agent_reports["retail_sentiment"] = node_data["retail_sentiment_report"]
                    if "policy_report" in node_data:
                        agent_reports["policy"] = node_data["policy_report"]

                    event_data = {
                        "node": node_name,
                        "stage": current_stage,
                        "status": "completed",
                        "message": f"Node {node_name} finished"
                    }
                    await cache_service.push_sse_event(task_id, current_stage, event_data)

                    # 收集 Planner 决策信息（如有）
                    if "recommended_analysts" in node_data:
                        planner_decision = f"Planner 推荐使用: {', '.join(node_data['recommended_analysts'])}"
                    elif "planner_decision" not in locals():
                        planner_decision = None

            # 计算耗时
            elapsed_seconds = round(time.time() - start_time, 2)

            # 构建合成上下文
            historical_cases_count = None
            if 'reflection' in locals() and reflection:
                historical_cases_count = len(reflection.historical_analyses)

            synthesis_context = SynthesisContext(
                analysis_level=task.analysis_level,
                task_id=task_id,
                elapsed_seconds=elapsed_seconds,
                analysts_used=selected_analysts,
                planner_decision=planner_decision if 'planner_decision' in locals() else None,
                data_quality_issues=None,
                historical_cases_count=historical_cases_count,
                market=market,
            )

            # 最终合成
            logger.info("Starting final synthesis", symbol=symbol, task_id=task_id)
            final_json = await synthesizer.synthesize(symbol, agent_reports, synthesis_context)

            elapsed_seconds = round(time.time() - start_time, 2)

            # 保存到数据库
            with Session(engine) as session:
                analysis_result = AnalysisResult(
                    symbol=symbol,
                    date=task.trade_date,
                    signal=final_json.get("signal", "Hold"),
                    confidence=final_json.get("confidence", 50),
                    full_report_json=json.dumps(final_json, ensure_ascii=False),
                    anchor_script=final_json.get("anchor_script", ""),
                    task_id=task_id,
                    status="completed",
                    elapsed_seconds=elapsed_seconds,
                    architecture_mode=architecture_mode,
                )
                session.add(analysis_result)
                session.commit()
                session.refresh(analysis_result)

            # 记录预测
            try:
                recommendation = final_json.get("recommendation", {})
                await accuracy_tracker.record_prediction(
                    analysis_id=analysis_result.id,
                    symbol=symbol,
                    signal=final_json.get("signal", "Hold"),
                    confidence=final_json.get("confidence", 50),
                    target_price=recommendation.get("target_price"),
                    stop_loss=recommendation.get("stop_loss"),
                    entry_price=recommendation.get("entry_price"),
                    agent_key="overall",
                )
            except Exception as pred_err:
                logger.warning("Failed to record prediction", error=str(pred_err))

            # 存储到向量记忆库
            try:
                analysis_memory = AnalysisMemory(
                    symbol=symbol,
                    date=task.trade_date,
                    signal=final_json.get("signal", "Hold"),
                    confidence=final_json.get("confidence", 50),
                    reasoning_summary=final_json.get("recommendation", {}).get("reasoning", "")[:500],
                    debate_winner=final_json.get("debate_summary", {}).get("winner"),
                    risk_score=final_json.get("risk_assessment", {}).get("score"),
                    entry_price=final_json.get("recommendation", {}).get("entry_price"),
                    target_price=final_json.get("recommendation", {}).get("target_price"),
                    stop_loss=final_json.get("recommendation", {}).get("stop_loss"),
                )

                # 使用分层记忆存储
                sector = final_json.get("company_overview", {}).get("sector")
                await layered_memory.store_layered_analysis(
                    analysis_memory,
                    sector=sector,
                    macro_cycle=None,
                    pattern_type=None,
                )
            except Exception as mem_err:
                logger.warning("Failed to store analysis to memory", error=str(mem_err))

            # 添加诊断信息
            final_json["diagnostics"] = {
                "task_id": task_id,
                "elapsed_seconds": elapsed_seconds,
                "worker": self.name,
            }

            await cache_service.push_sse_event(task_id, "stage_final", final_json)
            await cache_service.set_sse_status(task_id, "completed")
            await cache_service.set_task(task_id, {"status": "completed", "symbol": symbol})

            logger.info(
                "Analysis task completed",
                worker=self.name,
                task_id=task_id,
                symbol=symbol,
                elapsed_seconds=elapsed_seconds,
            )

            return True

        except Exception as e:
            elapsed_seconds = round(time.time() - start_time, 2)
            logger.error(
                "Analysis task failed",
                worker=self.name,
                task_id=task_id,
                symbol=symbol,
                error=str(e),
                retry_count=task.retry_count,
            )

            # 保存失败记录
            with Session(engine) as session:
                analysis_result = AnalysisResult(
                    symbol=symbol,
                    date=task.trade_date,
                    signal="Error",
                    confidence=0,
                    full_report_json="{}",
                    anchor_script="",
                    task_id=task_id,
                    status="failed",
                    error_message=str(e),
                    elapsed_seconds=elapsed_seconds,
                    architecture_mode=architecture_mode if 'architecture_mode' in locals() else "unknown",
                )
                session.add(analysis_result)
                session.commit()

            await cache_service.push_sse_event(task_id, "error", {"message": str(e)})
            await cache_service.set_sse_status(task_id, "failed")
            await cache_service.set_task(task_id, {"status": "failed", "symbol": symbol, "error": str(e)})

            return False

    async def run(self):
        """运行 worker 主循环"""
        self._running = True
        logger.info("Analysis worker starting", name=self.name)

        while self._running:
            try:
                # 从队列获取任务
                result = await task_queue.dequeue(self.name, block_ms=5000)

                if result is None:
                    continue

                message_id, task = result
                self._current_task = task

                # 处理任务
                success = await self.process_task(task)

                if success:
                    await task_queue.ack(message_id)
                else:
                    await task_queue.nack(message_id, task)

                self._current_task = None

            except asyncio.CancelledError:
                logger.info("Worker cancelled", name=self.name)
                break
            except Exception as e:
                logger.error("Worker loop error", name=self.name, error=str(e))
                await asyncio.sleep(5)  # 错误后等待一段时间

        logger.info("Analysis worker stopped", name=self.name)

    def stop(self):
        """停止 worker"""
        self._running = False


async def main(worker_name: str):
    """主函数"""
    worker = AnalysisWorker(name=worker_name)

    # 设置信号处理
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Received shutdown signal", worker=worker_name)
        worker.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await worker.run()
    finally:
        await cache_service.close()
        await task_queue.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analysis Worker")
    parser.add_argument(
        "--name",
        type=str,
        default=f"worker-{os.getpid()}",
        help="Worker name for logging and consumer identification"
    )
    args = parser.parse_args()

    asyncio.run(main(args.name))
