"""板块筛选工具函数"""

def should_filter_stock(stock_code: str, board_type: str) -> bool:
    """
    判断股票是否应该被过滤
    
    Args:
        stock_code: 股票代码
        board_type: 板块类型
            - 'all': 全部板块（主板+双创+北交所）
            - 'main': 主板（过滤3/68/920开头）
            - 'bjs': 北交所（只保留920开头）
    
    Returns:
        True表示应该过滤（不包含），False表示保留
    """
    if board_type == 'all':
        return False  # 全部板块，不过滤任何股票
    
    elif board_type == 'main':
        # 主板：过滤双创板(3/68开头)和北交所(920开头)
        return (stock_code.startswith('3') or 
                stock_code.startswith('68') or 
                stock_code.startswith('920'))
    
    elif board_type == 'bjs':
        # 北交所：只保留920开头的股票
        return not stock_code.startswith('920')
    
    # 默认不过滤
    return False


def get_board_name(board_type: str) -> str:
    """获取板块名称"""
    names = {
        'all': '全部板块',
        'main': '主板',
        'bjs': '北交所'
    }
    return names.get(board_type, '未知')
