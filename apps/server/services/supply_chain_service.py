"""产业链知识图谱服务

建立 A 股产业链上下游关系，支持产业链穿透分析。
数据来源：静态知识库 + AkShare 行业分类 + LLM 增强。
"""

import json
import time
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

# ============ 缓存 ============

_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = 3600  # 1 小时


def _get_cache(key: str) -> Optional[Any]:
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["timestamp"] < _CACHE_TTL:
            return entry["data"]
        del _cache[key]
    return None


def _set_cache(key: str, data: Any) -> None:
    _cache[key] = {"data": data, "timestamp": time.time()}


# ============ 静态产业链知识库 ============

# 预定义 A 股核心产业链（10+ 条链）
SUPPLY_CHAINS: Dict[str, Dict[str, Any]] = {
    "semiconductor": {
        "name": "半导体产业链",
        "description": "从设计到封测的完整半导体产业链",
        "upstream": [
            {"name": "硅片/晶圆", "companies": ["沪硅产业.688126", "立昂微.605358", "中环股份.002129"]},
            {"name": "光刻胶/材料", "companies": ["南大光电.300346", "雅克科技.002409", "晶瑞电材.300655"]},
            {"name": "EDA/IP", "companies": ["华大九天.301269", "概伦电子.688206"]},
        ],
        "midstream": [
            {"name": "芯片设计", "companies": ["韦尔股份.603501", "兆易创新.603986", "卓胜微.300782", "北京君正.300223"]},
            {"name": "晶圆代工", "companies": ["中芯国际.688981", "华虹半导体.688347"]},
        ],
        "downstream": [
            {"name": "封装测试", "companies": ["长电科技.600584", "通富微电.002156", "华天科技.002185"]},
            {"name": "设备", "companies": ["北方华创.002371", "中微公司.688012", "盛美上海.688082"]},
        ],
    },
    "ev": {
        "name": "新能源汽车产业链",
        "description": "从锂矿到整车的新能源汽车全产业链",
        "upstream": [
            {"name": "锂矿/锂盐", "companies": ["天齐锂业.002466", "赣锋锂业.002460", "盐湖股份.000792"]},
            {"name": "正极材料", "companies": ["容百科技.688005", "当升科技.300073", "德方纳米.300769"]},
            {"name": "负极材料", "companies": ["璞泰来.603659", "杉杉股份.600884"]},
            {"name": "电解液", "companies": ["天赐材料.002709", "新宙邦.300037"]},
            {"name": "隔膜", "companies": ["恩捷股份.002812", "星源材质.300568"]},
        ],
        "midstream": [
            {"name": "动力电池", "companies": ["宁德时代.300750", "比亚迪.002594", "亿纬锂能.300014", "国轩高科.002074"]},
            {"name": "电机电控", "companies": ["汇川技术.300124", "卧龙电驱.600580"]},
        ],
        "downstream": [
            {"name": "整车制造", "companies": ["比亚迪.002594", "长城汽车.601633", "广汽集团.601238", "理想汽车.02015.HK"]},
            {"name": "充电桩", "companies": ["特锐德.300001", "盛弘股份.300693"]},
        ],
    },
    "consumer_electronics": {
        "name": "消费电子产业链",
        "description": "智能手机、PC 等消费电子产业链",
        "upstream": [
            {"name": "面板/显示", "companies": ["京东方A.000725", "TCL科技.000100", "维信诺.002387"]},
            {"name": "被动元件", "companies": ["三环集团.300408", "风华高科.000636"]},
            {"name": "PCB", "companies": ["鹏鼎控股.002938", "深南电路.002916", "沪电股份.002463"]},
        ],
        "midstream": [
            {"name": "摄像头模组", "companies": ["舜宇光学.02382.HK", "欧菲光.002456"]},
            {"name": "声学器件", "companies": ["歌尔股份.002241", "瑞声科技.02018.HK"]},
            {"name": "连接器", "companies": ["立讯精密.002475", "长盈精密.300115"]},
        ],
        "downstream": [
            {"name": "品牌终端", "companies": ["小米集团.01810.HK", "传音控股.688036"]},
            {"name": "代工制造", "companies": ["富士康.601138", "比亚迪电子.00285.HK"]},
        ],
    },
    "photovoltaic": {
        "name": "光伏产业链",
        "description": "从硅料到电站的光伏全产业链",
        "upstream": [
            {"name": "多晶硅", "companies": ["通威股份.600438", "大全能源.688303", "协鑫科技.03800.HK"]},
            {"name": "硅片", "companies": ["隆基绿能.601012", "TCL中环.002129"]},
        ],
        "midstream": [
            {"name": "电池片", "companies": ["通威股份.600438", "爱旭股份.600732", "钧达股份.002865"]},
            {"name": "组件", "companies": ["隆基绿能.601012", "晶澳科技.002459", "天合光能.688599", "晶科能源.688223"]},
        ],
        "downstream": [
            {"name": "逆变器", "companies": ["阳光电源.300274", "锦浪科技.300763", "固德威.688390"]},
            {"name": "电站运营", "companies": ["太阳能.000591", "晶科科技.601778"]},
        ],
    },
    "ai_computing": {
        "name": "AI 算力产业链",
        "description": "AI 大模型相关的算力基础设施产业链",
        "upstream": [
            {"name": "GPU/AI芯片", "companies": ["寒武纪.688256", "海光信息.688041", "景嘉微.300474"]},
            {"name": "存储芯片", "companies": ["兆易创新.603986", "北京君正.300223"]},
        ],
        "midstream": [
            {"name": "服务器", "companies": ["浪潮信息.000977", "中科曙光.603019", "紫光股份.000938"]},
            {"name": "交换机/网络", "companies": ["中兴通讯.000063", "锐捷网络.301165"]},
            {"name": "光模块", "companies": ["中际旭创.300308", "新易盛.300502", "天孚通信.300394"]},
        ],
        "downstream": [
            {"name": "云计算/IDC", "companies": ["万国数据.GDS", "数据港.603881", "奥飞数据.300738"]},
            {"name": "AI应用", "companies": ["科大讯飞.002230", "金山办公.688111"]},
        ],
    },
    "liquor": {
        "name": "白酒产业链",
        "description": "白酒酿造全产业链",
        "upstream": [
            {"name": "粮食/原料", "companies": ["金健米业.600127", "北大荒.600598"]},
            {"name": "包装材料", "companies": ["山东药玻.600529", "中粮包装.00906.HK"]},
        ],
        "midstream": [
            {"name": "高端白酒", "companies": ["贵州茅台.600519", "五粮液.000858", "泸州老窖.000568"]},
            {"name": "次高端白酒", "companies": ["山西汾酒.600809", "洋河股份.002304", "古井贡酒.000596"]},
            {"name": "区域白酒", "companies": ["今世缘.603369", "口子窖.603589", "迎驾贡酒.603198"]},
        ],
        "downstream": [
            {"name": "经销商/零售", "companies": ["华致酒行.300755", "壹玖壹玖.830993"]},
        ],
    },
    "medical_device": {
        "name": "医疗器械产业链",
        "description": "医疗器械研发制造产业链",
        "upstream": [
            {"name": "医用材料", "companies": ["奥美医疗.002950", "振德医疗.603301"]},
            {"name": "传感器/元件", "companies": ["翠微股份.603123"]},
        ],
        "midstream": [
            {"name": "高值耗材", "companies": ["微创医疗.00853.HK", "乐普医疗.300003", "惠泰医疗.688617"]},
            {"name": "医学影像", "companies": ["联影医疗.688271", "万东医疗.600055", "开立医疗.300633"]},
            {"name": "IVD诊断", "companies": ["迈瑞医疗.300760", "安图生物.603658", "新产业.300832"]},
        ],
        "downstream": [
            {"name": "医院/渠道", "companies": ["国药控股.01099.HK", "润达医疗.603108"]},
        ],
    },
    "military": {
        "name": "军工产业链",
        "description": "国防军工产业链",
        "upstream": [
            {"name": "特种材料", "companies": ["光威复材.300699", "中简科技.300777", "西部超导.688122"]},
            {"name": "电子元器件", "companies": ["振华科技.000733", "紫光国微.002049"]},
        ],
        "midstream": [
            {"name": "航空发动机", "companies": ["航发动力.600893", "航发控制.000738"]},
            {"name": "导弹/武器", "companies": ["航天电器.002025", "中航光电.002179"]},
            {"name": "军用电子", "companies": ["中航电子.600372", "航天发展.000547"]},
        ],
        "downstream": [
            {"name": "主机厂", "companies": ["中航沈飞.600760", "航天彩虹.002389", "中直股份.600038"]},
            {"name": "卫星/航天", "companies": ["中国卫星.600118", "航天宏图.688066"]},
        ],
    },
    "real_estate": {
        "name": "房地产产业链",
        "description": "房地产开发全产业链",
        "upstream": [
            {"name": "水泥建材", "companies": ["海螺水泥.600585", "中国建材.03323.HK"]},
            {"name": "钢铁", "companies": ["宝钢股份.600019", "中信特钢.000708"]},
            {"name": "玻璃", "companies": ["旗滨集团.601636", "信义玻璃.00868.HK"]},
        ],
        "midstream": [
            {"name": "房地产开发", "companies": ["万科A.000002", "保利发展.600048", "招商蛇口.001979"]},
            {"name": "建筑施工", "companies": ["中国建筑.601668", "中国中铁.601390"]},
        ],
        "downstream": [
            {"name": "家居装修", "companies": ["欧派家居.603833", "顾家家居.603816"]},
            {"name": "物业管理", "companies": ["碧桂园服务.06098.HK", "华润万象生活.01209.HK"]},
            {"name": "家电", "companies": ["美的集团.000333", "格力电器.000651", "海尔智家.600690"]},
        ],
    },
    "cxo_pharma": {
        "name": "CXO/创新药产业链",
        "description": "创新药研发外包服务产业链",
        "upstream": [
            {"name": "CRO(临床前)", "companies": ["药明康德.603259", "康龙化成.300759", "昭衍新药.603127"]},
            {"name": "原料药/中间体", "companies": ["凯莱英.002821", "博腾股份.300363"]},
        ],
        "midstream": [
            {"name": "CDMO(工艺开发)", "companies": ["药明康德.603259", "凯莱英.002821", "九洲药业.603456"]},
            {"name": "创新药企", "companies": ["恒瑞医药.600276", "百济神州.688235", "信达生物.01801.HK"]},
        ],
        "downstream": [
            {"name": "CSO(商业化)", "companies": ["泰格医药.300347", "百诚医药.301096"]},
            {"name": "医药流通", "companies": ["国药控股.01099.HK", "上海医药.601607", "华东医药.000963"]},
        ],
    },
}

# 公司到产业链的反向索引
_company_chain_index: Dict[str, List[Dict[str, str]]] = {}


def _build_company_index():
    """构建公司到产业链的反向索引"""
    global _company_chain_index
    if _company_chain_index:
        return

    for chain_id, chain in SUPPLY_CHAINS.items():
        for position in ["upstream", "midstream", "downstream"]:
            for segment in chain.get(position, []):
                for company in segment.get("companies", []):
                    # 提取代码部分
                    parts = company.rsplit(".", 1)
                    if len(parts) == 2:
                        name_code = parts[0]
                        # 尝试提取纯代码
                        code_parts = name_code.split(".")
                        code = code_parts[-1] if len(code_parts) > 1 else name_code

                        entry = {
                            "chain_id": chain_id,
                            "chain_name": chain["name"],
                            "position": position,
                            "segment": segment["name"],
                            "full_name": company,
                        }

                        # 用多种格式索引
                        for key in [company, code, name_code]:
                            if key not in _company_chain_index:
                                _company_chain_index[key] = []
                            _company_chain_index[key].append(entry)


# ============ 产业链服务 ============

class SupplyChainService:
    """产业链知识图谱服务"""

    def __init__(self):
        _build_company_index()

    def get_chain_list(self) -> Dict[str, Any]:
        """获取所有产业链列表"""
        chains = []
        for chain_id, chain in SUPPLY_CHAINS.items():
            total_companies = sum(
                len(seg.get("companies", []))
                for pos in ["upstream", "midstream", "downstream"]
                for seg in chain.get(pos, [])
            )
            chains.append({
                "id": chain_id,
                "name": chain["name"],
                "description": chain["description"],
                "total_companies": total_companies,
                "segments": {
                    "upstream": len(chain.get("upstream", [])),
                    "midstream": len(chain.get("midstream", [])),
                    "downstream": len(chain.get("downstream", [])),
                },
            })

        return {
            "chains": chains,
            "total": len(chains),
            "timestamp": datetime.now().isoformat(),
        }

    def get_chain_graph(self, chain_id: str) -> Dict[str, Any]:
        """获取产业链图谱数据（用于前端可视化）

        Args:
            chain_id: 产业链 ID（如 semiconductor, ev）

        Returns:
            节点和边的图谱数据
        """
        cache_k = f"chain_graph_{chain_id}"
        cached = _get_cache(cache_k)
        if cached:
            return cached

        chain = SUPPLY_CHAINS.get(chain_id)
        if not chain:
            return {"error": f"Chain '{chain_id}' not found", "nodes": [], "edges": []}

        nodes = []
        edges = []
        node_id = 0

        # 添加产业链中心节点
        center_id = f"center_{chain_id}"
        nodes.append({
            "id": center_id,
            "type": "chain",
            "label": chain["name"],
            "position": "center",
        })

        for position in ["upstream", "midstream", "downstream"]:
            for segment in chain.get(position, []):
                # 添加环节节点
                segment_id = f"seg_{node_id}"
                node_id += 1
                nodes.append({
                    "id": segment_id,
                    "type": "segment",
                    "label": segment["name"],
                    "position": position,
                })

                # 连接到中心
                edges.append({
                    "source": center_id if position == "upstream" else segment_id,
                    "target": segment_id if position == "upstream" else center_id,
                    "relation": position,
                })

                # 添加公司节点
                for company in segment.get("companies", []):
                    company_id = f"comp_{node_id}"
                    node_id += 1

                    # 解析公司名和代码
                    parts = company.rsplit(".", 1)
                    name = parts[0] if len(parts) >= 1 else company
                    code = parts[1] if len(parts) == 2 else ""

                    # 尝试获取实时价格数据
                    price_data = self._get_stock_price_safe(company)

                    nodes.append({
                        "id": company_id,
                        "type": "company",
                        "label": name,
                        "symbol": company,
                        "code": code,
                        "position": position,
                        "segment": segment["name"],
                        "price": price_data.get("current_price"),
                        "change_pct": price_data.get("change_pct"),
                    })

                    edges.append({
                        "source": segment_id,
                        "target": company_id,
                        "relation": "contains",
                    })

        # 添加上下游之间的供应关系边
        upstream_segments = [n for n in nodes if n.get("position") == "upstream" and n["type"] == "segment"]
        midstream_segments = [n for n in nodes if n.get("position") == "midstream" and n["type"] == "segment"]
        downstream_segments = [n for n in nodes if n.get("position") == "downstream" and n["type"] == "segment"]

        for up in upstream_segments:
            for mid in midstream_segments:
                edges.append({
                    "source": up["id"],
                    "target": mid["id"],
                    "relation": "supplies",
                    "style": "dashed",
                })

        for mid in midstream_segments:
            for down in downstream_segments:
                edges.append({
                    "source": mid["id"],
                    "target": down["id"],
                    "relation": "supplies",
                    "style": "dashed",
                })

        result = {
            "chain_id": chain_id,
            "chain_name": chain["name"],
            "description": chain["description"],
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "upstream_count": len(upstream_segments),
                "midstream_count": len(midstream_segments),
                "downstream_count": len(downstream_segments),
            },
            "timestamp": datetime.now().isoformat(),
        }

        _set_cache(cache_k, result)
        return result

    def get_stock_chain_position(self, symbol: str) -> Dict[str, Any]:
        """获取个股在产业链中的位置

        Args:
            symbol: 股票代码

        Returns:
            该股票在产业链中的位置信息
        """
        _build_company_index()

        # 清理 symbol
        clean_symbol = symbol.replace(".SH", "").replace(".SZ", "").replace(".SS", "")

        # 搜索匹配
        matches = []
        for key, entries in _company_chain_index.items():
            if clean_symbol in key or key in symbol:
                matches.extend(entries)

        if not matches:
            # 尝试通过 AkShare 获取行业信息
            industry_info = self._get_industry_info(symbol)
            return {
                "symbol": symbol,
                "found": False,
                "industry_info": industry_info,
                "suggestion": "该股票不在预定义产业链中，可通过行业分类查找相关产业链。",
            }

        # 去重
        seen = set()
        unique_matches = []
        for m in matches:
            key = f"{m['chain_id']}_{m['segment']}"
            if key not in seen:
                seen.add(key)
                unique_matches.append(m)

        return {
            "symbol": symbol,
            "found": True,
            "chains": unique_matches,
            "chain_count": len(set(m["chain_id"] for m in unique_matches)),
            "timestamp": datetime.now().isoformat(),
        }

    def analyze_supply_chain_impact(self, symbol: str) -> Dict[str, Any]:
        """分析产业链传导效应

        Args:
            symbol: 股票代码

        Returns:
            产业链传导效应分析
        """
        position = self.get_stock_chain_position(symbol)
        if not position.get("found"):
            return {
                "symbol": symbol,
                "analysis": "该股票不在已知产业链中，无法进行传导效应分析。",
                "chains": [],
            }

        analyses = []
        for chain_info in position.get("chains", []):
            chain_id = chain_info["chain_id"]
            chain = SUPPLY_CHAINS.get(chain_id, {})
            pos = chain_info["position"]

            # 获取上下游公司
            upstream_companies = []
            downstream_companies = []

            if pos == "midstream" or pos == "downstream":
                for seg in chain.get("upstream", []):
                    upstream_companies.extend(seg.get("companies", []))

            if pos == "upstream" or pos == "midstream":
                for seg in chain.get("downstream", []):
                    downstream_companies.extend(seg.get("companies", []))

            analyses.append({
                "chain_id": chain_id,
                "chain_name": chain.get("name", ""),
                "position": pos,
                "segment": chain_info["segment"],
                "upstream_companies": upstream_companies[:10],
                "downstream_companies": downstream_companies[:10],
                "impact_analysis": {
                    "upstream_risk": f"上游 {len(upstream_companies)} 家供应商，供应链集中度需关注",
                    "downstream_demand": f"下游 {len(downstream_companies)} 家客户，需求端分散度分析",
                    "position_advantage": self._assess_position_advantage(pos),
                },
            })

        return {
            "symbol": symbol,
            "analyses": analyses,
            "timestamp": datetime.now().isoformat(),
        }

    def _assess_position_advantage(self, position: str) -> str:
        """评估产业链位置优势"""
        assessments = {
            "upstream": "上游位置：掌握原材料/核心技术，议价能力较强，但受大宗商品价格波动影响",
            "midstream": "中游位置：承上启下，技术壁垒和规模效应是核心竞争力",
            "downstream": "下游位置：贴近终端需求，品牌和渠道是核心竞争力，受消费周期影响",
        }
        return assessments.get(position, "位置未知")

    def _get_stock_price_safe(self, company: str) -> Dict[str, Any]:
        """安全获取股票价格（不抛异常）"""
        try:
            from services.data_router import MarketRouter
            router = MarketRouter()
            data = router.get_price(company)
            if data:
                return {
                    "current_price": data.get("current_price"),
                    "change_pct": data.get("change_pct"),
                }
        except Exception:
            pass
        return {}

    def _get_industry_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """通过 AkShare 获取行业分类信息"""
        try:
            import akshare as ak

            # 获取行业分类
            df = ak.stock_board_industry_name_em()
            if df is not None and not df.empty:
                return {
                    "source": "akshare",
                    "industries": df.head(20).to_dict("records"),
                }
        except Exception as e:
            logger.debug("Failed to get industry info", error=str(e))
        return None


# 单例
supply_chain_service = SupplyChainService()
