"""产业链服务测试"""

import pytest


class TestSupplyChainService:
    """测试产业链知识图谱服务"""

    def test_get_chain_list(self):
        """应返回产业链列表"""
        from services.supply_chain_service import supply_chain_service

        result = supply_chain_service.get_chain_list()
        assert "chains" in result
        assert "total" in result
        assert result["total"] > 0

        # 验证每条链的结构
        for chain in result["chains"]:
            assert "id" in chain
            assert "name" in chain
            assert "total_companies" in chain
            assert chain["total_companies"] > 0

    def test_known_chains_exist(self):
        """应包含预定义的核心产业链"""
        from services.supply_chain_service import supply_chain_service

        result = supply_chain_service.get_chain_list()
        chain_ids = [c["id"] for c in result["chains"]]

        assert "semiconductor" in chain_ids
        assert "ev" in chain_ids
        assert "photovoltaic" in chain_ids
        assert "ai_computing" in chain_ids

    def test_get_chain_graph(self):
        """应返回产业链图谱数据"""
        from services.supply_chain_service import supply_chain_service

        result = supply_chain_service.get_chain_graph("semiconductor")
        assert "nodes" in result
        assert "edges" in result
        assert "stats" in result
        assert len(result["nodes"]) > 0
        assert len(result["edges"]) > 0

    def test_get_chain_graph_invalid(self):
        """无效的产业链 ID 应返回错误"""
        from services.supply_chain_service import supply_chain_service

        result = supply_chain_service.get_chain_graph("nonexistent")
        assert "error" in result

    def test_graph_node_structure(self):
        """图谱节点应有正确的结构"""
        from services.supply_chain_service import supply_chain_service

        result = supply_chain_service.get_chain_graph("ev")
        nodes = result["nodes"]

        # 应有不同类型的节点
        node_types = set(n["type"] for n in nodes)
        assert "chain" in node_types
        assert "segment" in node_types
        assert "company" in node_types

        # 应有不同位置的节点
        positions = set(n.get("position") for n in nodes if n["type"] == "segment")
        assert "upstream" in positions
        assert "midstream" in positions
        assert "downstream" in positions

    def test_get_stock_chain_position_found(self):
        """已知股票应能找到产业链位置"""
        from services.supply_chain_service import supply_chain_service

        # 宁德时代应在新能源车产业链中
        result = supply_chain_service.get_stock_chain_position("300750")
        assert result["found"] is True
        assert len(result.get("chains", [])) > 0

        chain_names = [c["chain_name"] for c in result["chains"]]
        assert any("新能源" in name for name in chain_names)

    def test_get_stock_chain_position_not_found(self):
        """未知股票应返回未找到"""
        from services.supply_chain_service import supply_chain_service

        result = supply_chain_service.get_stock_chain_position("999999")
        assert result["found"] is False

    def test_analyze_supply_chain_impact(self):
        """应返回产业链传导效应分析"""
        from services.supply_chain_service import supply_chain_service

        result = supply_chain_service.analyze_supply_chain_impact("300750")
        assert "analyses" in result
        assert len(result["analyses"]) > 0

        analysis = result["analyses"][0]
        assert "chain_name" in analysis
        assert "position" in analysis
        assert "impact_analysis" in analysis

    def test_analyze_unknown_stock(self):
        """未知股票应返回空分析"""
        from services.supply_chain_service import supply_chain_service

        result = supply_chain_service.analyze_supply_chain_impact("999999")
        assert "analysis" in result or len(result.get("analyses", [])) == 0


class TestSupplyChainData:
    """测试产业链静态数据完整性"""

    def test_all_chains_have_three_levels(self):
        """每条产业链应有上中下游三个层级"""
        from services.supply_chain_service import SUPPLY_CHAINS

        for chain_id, chain in SUPPLY_CHAINS.items():
            assert "upstream" in chain, f"{chain_id} missing upstream"
            assert "midstream" in chain, f"{chain_id} missing midstream"
            assert "downstream" in chain, f"{chain_id} missing downstream"
            assert len(chain["upstream"]) > 0, f"{chain_id} has empty upstream"
            assert len(chain["midstream"]) > 0, f"{chain_id} has empty midstream"
            assert len(chain["downstream"]) > 0, f"{chain_id} has empty downstream"

    def test_all_segments_have_companies(self):
        """每个环节应有至少一家公司"""
        from services.supply_chain_service import SUPPLY_CHAINS

        for chain_id, chain in SUPPLY_CHAINS.items():
            for position in ["upstream", "midstream", "downstream"]:
                for segment in chain[position]:
                    assert "name" in segment
                    assert "companies" in segment
                    assert len(segment["companies"]) > 0, \
                        f"{chain_id}/{position}/{segment['name']} has no companies"
