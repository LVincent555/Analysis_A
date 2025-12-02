"""临时脚本：清除失败的导入记录"""
import json
from pathlib import Path

# 读取状态文件
state_file = Path('data/data_import_state.json')
with open(state_file, 'r', encoding='utf-8') as f:
    state = json.load(f)

# 删除失败的记录
removed = []
if '20251107' in state['imports']:
    removed.append('20251107')
    del state['imports']['20251107']

if '~$20251107' in state['imports']:
    removed.append('~$20251107')
    del state['imports']['~$20251107']

# 保存
with open(state_file, 'w', encoding='utf-8') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

print(f"✅ 已清除失败记录: {', '.join(removed)}")
