import hashlib
from typing import Optional
from config.settings import settings

def should_use_subgraph(user_id: Optional[str] = None, request_id: Optional[str] = None, force_param: Optional[bool] = None) -> bool:
    """
    决定当前请求是否应该使用 SubGraph 架构。
    
    逻辑优先级：
    1. 如果 force_param 显式指定，则以其为准。
    2. 如果 user_id 在强制启用列表中，则启用。
    3. 根据 user_id 或 request_id 的哈希值，结合 SUBGRAPH_ROLLOUT_PERCENTAGE 决定。
    """
    # 1. 显式参数优先
    if force_param is not None:
        return force_param

    # 2. 强制启用用户列表
    if user_id and user_id in settings.SUBGRAPH_FORCE_ENABLED_USERS:
        return True

    # 3. 灰度比例逻辑
    rollout_percentage = settings.SUBGRAPH_ROLLOUT_PERCENTAGE
    if rollout_percentage <= 0:
        return False
    if rollout_percentage >= 100:
        return True

    # 使用 user_id 或 request_id 作为哈希因子
    hash_factor = user_id or request_id or "default"
    
    # 计算 MD5 哈希并取模
    hash_val = int(hashlib.md5(hash_factor.encode()).hexdigest(), 16)
    return (hash_val % 100) < rollout_percentage
