"""
数据修补器 - Data Fixer
处理数据导入过程中的数据质量问题，支持自动检测和修补

功能：
1. 换手率修补：检测异常低的换手率并乘以修正系数
2. 幂等性：多次执行结果一致
3. 可回滚：支持撤销修补操作
4. 状态追踪：记录所有修补操作
"""
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal
import pandas as pd
from sqlalchemy import func
from app.database import SessionLocal
from app.db_models import DailyStockData
from import_state_manager import ImportStateManager

logger = logging.getLogger(__name__)


class DataFixConfig:
    """数据修补配置"""
    
    # 换手率修补配置
    TURNOVER_FIX = {
        'enabled': True,          # 是否启用
        'auto_fix': True,         # 是否自动修补
        'threshold': 0.01,        # 检测阈值（1%）
        'multiplier': 10000,      # 修补倍数
        'min_normal': 0.001,      # 正常换手率最小值（0.1%）
        'max_normal': 0.5,        # 正常换手率最大值（50%）
        'sample_ratio': 0.8       # 样本比例（80%以上异常才修补）
    }
    
    @classmethod
    def get_fix_config(cls, fix_type: str) -> Dict:
        """获取修补配置"""
        configs = {
            'turnover_rate': cls.TURNOVER_FIX
        }
        return configs.get(fix_type, {})


class TurnoverRateFixer:
    """换手率修补器"""
    
    def __init__(self, date_str: str, data_type: str = 'stock'):
        """
        Args:
            date_str: 日期字符串 YYYYMMDD
            data_type: 数据类型（stock/sector）
        """
        self.date_str = date_str
        self.data_type = data_type
        self.config = DataFixConfig.get_fix_config('turnover_rate')
        
        # 状态管理
        state_file = (
            "data_import_state.json" if data_type == 'stock' 
            else "sector_import_state.json"
        )
        self.state_manager = ImportStateManager(state_file)
        
        # 修补信息
        self.fix_info = {}
    
    def detect_anomaly(self, df: pd.DataFrame) -> Tuple[bool, Dict]:
        """
        检测换手率异常
        
        Args:
            df: DataFrame，必须包含 turnover_rate_percent 或 换手率% 列
            
        Returns:
            (is_anomaly, detection_info)
        """
        # 支持中文列名和英文列名
        turnover_col = None
        if 'turnover_rate_percent' in df.columns:
            turnover_col = 'turnover_rate_percent'
        elif '换手率%' in df.columns:
            turnover_col = '换手率%'
        else:
            logger.warning("DataFrame中没有换手率列（turnover_rate_percent 或 换手率%）")
            return False, {}
        
        # 过滤掉空值
        turnover_data = df[turnover_col].dropna()
        
        if len(turnover_data) == 0:
            logger.warning("没有有效的换手率数据")
            return False, {}
        
        # 统计数据
        avg_turnover = float(turnover_data.mean())
        median_turnover = float(turnover_data.median())
        max_turnover = float(turnover_data.max())
        min_turnover = float(turnover_data.min())
        
        # 计算异常比例
        threshold = self.config['threshold']
        abnormal_count = (turnover_data < threshold).sum()
        abnormal_ratio = abnormal_count / len(turnover_data)
        
        # 判断是否异常
        is_anomaly = (
            avg_turnover < threshold and 
            abnormal_ratio > self.config['sample_ratio']
        )
        
        detection_info = {
            'avg_turnover': float(avg_turnover),
            'median_turnover': float(median_turnover),
            'max_turnover': float(max_turnover),
            'min_turnover': float(min_turnover),
            'total_rows': int(len(turnover_data)),
            'abnormal_count': int(abnormal_count),
            'abnormal_ratio': float(abnormal_ratio),
            'threshold': float(threshold),
            'is_anomaly': bool(is_anomaly),
            'detected_at': datetime.now().isoformat()
        }
        
        if is_anomaly:
            logger.warning(
                f"检测到换手率异常！"
                f"平均值={avg_turnover:.6f}, "
                f"中位数={median_turnover:.6f}, "
                f"异常比例={abnormal_ratio:.1%}"
            )
        
        return is_anomaly, detection_info
    
    def fix_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        修补DataFrame中的换手率（幂等操作）
        
        Args:
            df: DataFrame
            
        Returns:
            (fixed_df, fix_info)
        """
        # 支持中文列名和英文列名
        turnover_col = None
        if 'turnover_rate_percent' in df.columns:
            turnover_col = 'turnover_rate_percent'
        elif '换手率%' in df.columns:
            turnover_col = '换手率%'
        else:
            return df, {'applied': False, 'reason': 'column_not_found'}
        
        # 检测异常
        is_anomaly, detection_info = self.detect_anomaly(df)
        
        if not is_anomaly:
            logger.info("换手率数据正常，无需修补")
            return df, {
                'applied': False, 
                'reason': 'no_anomaly_detected',
                'detection_info': detection_info
            }
        
        # 执行修补（创建副本，避免修改原始数据）
        fixed_df = df.copy()
        multiplier = self.config['multiplier']
        
        # 只修补异常的换手率（幂等性保证）
        mask = fixed_df[turnover_col] < self.config['threshold']
        affected_rows = mask.sum()
        
        # 乘以修正系数
        fixed_df.loc[mask, turnover_col] *= multiplier
        
        # 验证修补后的数据
        avg_after = float(fixed_df[turnover_col].mean())
        median_after = float(fixed_df[turnover_col].median())
        
        fix_info = {
            'applied': True,
            'fix_type': 'multiply_by_multiplier',
            'multiplier': multiplier,
            'affected_rows': int(affected_rows),
            'detection_info': detection_info,
            'avg_before': detection_info['avg_turnover'],
            'avg_after': avg_after,
            'median_before': detection_info['median_turnover'],
            'median_after': median_after,
            'fixed_at': datetime.now().isoformat()
        }
        
        logger.info(
            f"✅ 换手率修补完成！"
            f"影响行数={affected_rows}, "
            f"平均值: {detection_info['avg_turnover']:.6f} → {avg_after:.4f}"
        )
        
        self.fix_info = fix_info
        return fixed_df, fix_info
    
    def fix_database(self, dry_run: bool = False) -> Dict:
        """
        修补数据库中已导入的数据（幂等操作）
        
        Args:
            dry_run: 预演模式
            
        Returns:
            fix_result
        """
        db = SessionLocal()
        try:
            # 查询该日期的数据
            from datetime import datetime
            target_date = datetime.strptime(self.date_str, '%Y%m%d').date()
            
            records = db.query(DailyStockData).filter(
                DailyStockData.date == target_date
            ).all()
            
            if not records:
                logger.warning(f"数据库中没有找到 {self.date_str} 的数据")
                return {'applied': False, 'reason': 'no_data_found'}
            
            # 转换为DataFrame进行检测
            data = [{
                'id': r.id,
                'turnover_rate_percent': float(r.turnover_rate_percent) if r.turnover_rate_percent else None
            } for r in records]
            df = pd.DataFrame(data)
            
            # 检测异常
            is_anomaly, detection_info = self.detect_anomaly(df)
            
            if not is_anomaly:
                logger.info("数据库中的换手率数据正常，无需修补")
                return {
                    'applied': False,
                    'reason': 'no_anomaly_detected',
                    'detection_info': detection_info
                }
            
            if dry_run:
                logger.info("[预演模式] 将修补换手率数据")
                threshold = self.config['threshold']
                affected = sum(1 for r in records 
                              if r.turnover_rate_percent and 
                              float(r.turnover_rate_percent) < threshold)
                return {
                    'dry_run': True,
                    'would_affect': affected,
                    'detection_info': detection_info
                }
            
            # 执行修补
            multiplier = self.config['multiplier']
            threshold = self.config['threshold']
            affected_count = 0
            
            for record in records:
                if record.turnover_rate_percent is not None:
                    current_value = float(record.turnover_rate_percent)
                    if current_value < threshold:
                        # 幂等性：只修补异常值
                        record.turnover_rate_percent = Decimal(str(current_value * multiplier))
                        affected_count += 1
            
            db.commit()
            
            # 重新计算统计数据
            avg_after = db.query(
                func.avg(DailyStockData.turnover_rate_percent)
            ).filter(DailyStockData.date == target_date).scalar()
            
            fix_result = {
                'applied': True,
                'fix_type': 'database_update',
                'multiplier': multiplier,
                'affected_rows': affected_count,
                'total_rows': len(records),
                'detection_info': detection_info,
                'avg_before': detection_info['avg_turnover'],
                'avg_after': float(avg_after) if avg_after else 0,
                'fixed_at': datetime.now().isoformat()
            }
            
            logger.info(
                f"✅ 数据库换手率修补完成！"
                f"影响行数={affected_count}/{len(records)}"
            )
            
            return fix_result
            
        except Exception as e:
            db.rollback()
            logger.error(f"修补数据库失败: {str(e)}")
            raise
        finally:
            db.close()
    
    def rollback_database(self, dry_run: bool = False) -> Dict:
        """
        回滚数据库中的修补（撤销修补）
        
        Args:
            dry_run: 预演模式
            
        Returns:
            rollback_result
        """
        # 检查是否有修补记录
        import_info = self.state_manager.state['imports'].get(self.date_str)
        if not import_info:
            logger.warning(f"没有找到 {self.date_str} 的导入记录")
            return {'success': False, 'reason': 'no_import_record'}
        
        data_fixes = import_info.get('data_fixes', {})
        turnover_fix = data_fixes.get('turnover_rate_fix')
        
        if not turnover_fix or not turnover_fix.get('applied'):
            logger.warning(f"{self.date_str} 没有换手率修补记录")
            return {'success': False, 'reason': 'no_fix_record'}
        
        multiplier = turnover_fix.get('multiplier', 10000)
        
        db = SessionLocal()
        try:
            # 查询该日期的数据
            from datetime import datetime
            target_date = datetime.strptime(self.date_str, '%Y%m%d').date()
            
            records = db.query(DailyStockData).filter(
                DailyStockData.date == target_date
            ).all()
            
            if not records:
                logger.warning(f"数据库中没有找到 {self.date_str} 的数据")
                return {'success': False, 'reason': 'no_data_found'}
            
            if dry_run:
                logger.info(f"[预演模式] 将回滚 {len(records)} 条记录的换手率修补")
                return {
                    'dry_run': True,
                    'would_affect': len(records),
                    'multiplier': multiplier
                }
            
            # 执行回滚：除以修正系数
            affected_count = 0
            for record in records:
                if record.turnover_rate_percent is not None:
                    current_value = float(record.turnover_rate_percent)
                    # 回滚：除以倍数
                    record.turnover_rate_percent = Decimal(str(current_value / multiplier))
                    affected_count += 1
            
            db.commit()
            
            rollback_result = {
                'success': True,
                'rollback_type': 'database_rollback',
                'affected_rows': affected_count,
                'total_rows': len(records),
                'multiplier': multiplier,
                'rolled_back_at': datetime.now().isoformat()
            }
            
            logger.info(f"✅ 换手率修补回滚完成！影响行数={affected_count}")
            
            return rollback_result
            
        except Exception as e:
            db.rollback()
            logger.error(f"回滚失败: {str(e)}")
            raise
        finally:
            db.close()
    
    def record_fix_to_state(self, fix_info: Dict):
        """记录修补信息到状态文件"""
        import_info = self.state_manager.state['imports'].get(self.date_str)
        if not import_info:
            logger.warning(f"没有找到 {self.date_str} 的导入记录，无法记录修补信息")
            return
        
        # 确保 data_fixes 字段存在
        if 'data_fixes' not in import_info:
            import_info['data_fixes'] = {}
        
        # 记录修补信息
        import_info['data_fixes']['turnover_rate_fix'] = fix_info
        
        # 保存状态
        self.state_manager.save()
        logger.info(f"✅ 修补信息已记录到状态文件")
    
    def record_rollback_to_state(self, rollback_info: Dict):
        """记录回滚信息到状态文件"""
        import_info = self.state_manager.state['imports'].get(self.date_str)
        if not import_info:
            logger.warning(f"没有找到 {self.date_str} 的导入记录")
            return
        
        # 清除修补记录
        if 'data_fixes' in import_info:
            if 'turnover_rate_fix' in import_info['data_fixes']:
                import_info['data_fixes']['turnover_rate_fix'] = {
                    'applied': False,
                    'rolled_back': True,
                    'rollback_info': rollback_info
                }
        
        # 保存状态
        self.state_manager.save()
        logger.info(f"✅ 回滚信息已记录到状态文件")


def main():
    """独立测试"""
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    sys.path.insert(0, str(Path(__file__).parent))
    
    parser = argparse.ArgumentParser(description='数据修补工具')
    parser.add_argument('--date', required=True, help='日期 YYYYMMDD')
    parser.add_argument('--action', choices=['fix', 'rollback'], default='fix', help='操作类型')
    parser.add_argument('--dry-run', action='store_true', help='预演模式')
    
    args = parser.parse_args()
    
    fixer = TurnoverRateFixer(args.date)
    
    if args.action == 'fix':
        result = fixer.fix_database(dry_run=args.dry_run)
        if not args.dry_run and result.get('applied'):
            fixer.record_fix_to_state(result)
    elif args.action == 'rollback':
        result = fixer.rollback_database(dry_run=args.dry_run)
        if not args.dry_run and result.get('success'):
            fixer.record_rollback_to_state(result)
    
    print("\n结果:", result)


if __name__ == '__main__':
    main()
