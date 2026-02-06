import unittest
from services.rollout_manager import should_use_subgraph
from config.settings import settings

class TestRolloutManager(unittest.TestCase):
    def setUp(self):
        # 保存原始配置
        self.original_percentage = settings.SUBGRAPH_ROLLOUT_PERCENTAGE
        self.original_users = settings.SUBGRAPH_FORCE_ENABLED_USERS

    def tearDown(self):
        # 恢复原始配置
        settings.SUBGRAPH_ROLLOUT_PERCENTAGE = self.original_percentage
        settings.SUBGRAPH_FORCE_ENABLED_USERS = self.original_users

    def test_force_param(self):
        """测试显式参数优先级最高"""
        self.assertTrue(should_use_subgraph(force_param=True))
        self.assertFalse(should_use_subgraph(force_param=False))

    def test_force_users(self):
        """测试强制启用用户列表"""
        settings.SUBGRAPH_FORCE_ENABLED_USERS = ["user123", "admin"]
        settings.SUBGRAPH_ROLLOUT_PERCENTAGE = 0
        
        self.assertTrue(should_use_subgraph(user_id="user123"))
        self.assertTrue(should_use_subgraph(user_id="admin"))
        self.assertFalse(should_use_subgraph(user_id="other"))

    def test_rollout_percentage_0(self):
        """测试 0% 灰度"""
        settings.SUBGRAPH_ROLLOUT_PERCENTAGE = 0
        self.assertFalse(should_use_subgraph(user_id="any"))

    def test_rollout_percentage_100(self):
        """测试 100% 灰度"""
        settings.SUBGRAPH_ROLLOUT_PERCENTAGE = 100
        self.assertTrue(should_use_subgraph(user_id="any"))

    def test_hash_consistency(self):
        """测试哈希一致性（同一用户结果应一致）"""
        settings.SUBGRAPH_ROLLOUT_PERCENTAGE = 50
        
        res1 = should_use_subgraph(user_id="user_a")
        res2 = should_use_subgraph(user_id="user_a")
        self.assertEqual(res1, res2)
        
        res3 = should_use_subgraph(request_id="req_1")
        res4 = should_use_subgraph(request_id="req_1")
        self.assertEqual(res3, res4)

if __name__ == '__main__':
    unittest.main()
