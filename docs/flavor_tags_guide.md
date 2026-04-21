# 风味标签管理指南

## 📖 概述

本指南介绍如何在咖啡推荐系统中添加和管理风味标签。风味标签是咖啡产品的重要属性，用于帮助用户根据风味偏好搜索咖啡豆。

## 🔧 管理方式

### 方式一：使用 `update_coffee_database` 工具（自动）

这是最简单的方式，工具会自动爬取网站并更新产品信息，包括风味标签。

**使用方法**：
```
通过 Agent 调用 update_coffee_database 工具
```

**限制**：
- 每日限流一次（防止过度爬取）
- 依赖外部网站的数据质量

---

### 方式二：使用管理脚本（推荐）

我们提供了一个便捷的管理脚本 `scripts/manage_flavor_tags.py`，可以批量管理风味标签。

**功能**：
- 列出所有产品
- 列出所有风味标签
- 为产品添加风味标签
- 从产品移除风味标签

#### 1. 列出所有产品

```bash
python scripts/manage_flavor_tags.py list-products
```

**输出示例**：
```
================================================================================
ID    品牌              产品名称                           风味标签
================================================================================
1     明谦咖啡            埃塞俄比亚耶加雪菲·花魁                   茉莉花, 柑橘, 蜂蜜, 柠檬, 红茶, 甜橙
2     明谦咖啡            哥伦比亚慧兰·粉红波旁                    红酒, 草莓, 甜橙, 可可, 杏仁, 焦糖
3     明谦咖啡            肯尼亚AA·水洗                       黑醋栗, 葡萄柚, 布朗尼, 柠檬
================================================================================
```

#### 2. 列出所有风味标签

```bash
python scripts/manage_flavor_tags.py list-tags
```

**输出示例**：
```
============================================================
所有风味标签:
============================================================
  1. 布朗尼
  2. 柑橘
  3. 柠檬
  4. 焦糖
  5. 甜橙
  6. 红茶
  7. 红酒
  8. 茉莉花
  9. 草莓
 10. 葡萄柚
 11. 蜂蜜
 12. 黑醋栗
 13. 可可
 14. 杏仁
============================================================
共 14 个风味标签
```

#### 3. 添加风味标签

```bash
python scripts/manage_flavor_tags.py add --id <产品ID> --tags <标签1> <标签2> ...
```

**示例**：
```bash
# 为产品 2 添加"可可"和"杏仁"风味标签
python scripts/manage_flavor_tags.py add --id 2 --tags 可可 杏仁
```

**输出示例**：
```
✅ 产品 2 的风味标签已更新
   原标签: ['草莓', '焦糖', '甜橙', '红酒']
   新标签: ['红酒', '草莓', '甜橙', '可可', '杏仁', '焦糖']
```

#### 4. 移除风味标签

```bash
python scripts/manage_flavor_tags.py remove --id <产品ID> --tags <标签1> <标签2> ...
```

**示例**：
```bash
# 从产品 2 移除"红酒"风味标签
python scripts/manage_flavor_tags.py remove --id 2 --tags 红酒
```

---

### 方式三：直接使用 SQL

如果你熟悉 SQL，可以直接操作数据库。

#### 查看风味标签

```sql
-- 查看所有产品的风味标签
SELECT id, roaster_brand, product_name, flavor_tags
FROM coffee_products
ORDER BY id;

-- 查看所有唯一的风味标签
SELECT DISTINCT unnest(flavor_tags) as flavor_tag
FROM coffee_products
WHERE flavor_tags IS NOT NULL
ORDER BY flavor_tag;
```

#### 添加风味标签

```sql
-- 为指定产品添加单个风味标签
UPDATE coffee_products
SET flavor_tags = array_append(flavor_tags, '新标签')
WHERE id = 1
AND '新标签' != ANY(flavor_tags);  -- 避免重复添加

-- 为指定产品添加多个风味标签
UPDATE coffee_products
SET flavor_tags = array_cat(
    flavor_tags,
    ARRAY['标签1', '标签2', '标签3']
)
WHERE id = 1;
```

#### 移除风味标签

```sql
-- 从指定产品移除单个风味标签
UPDATE coffee_products
SET flavor_tags = array_remove(flavor_tags, '要移除的标签')
WHERE id = 1;

-- 从指定产品移除多个风味标签
UPDATE coffee_products
SET flavor_tags = (
    SELECT array_agg(tag)
    FROM unnest(flavor_tags) AS tag
    WHERE tag NOT IN ('要移除的标签1', '要移除的标签2')
)
WHERE id = 1;
```

#### 替换所有风味标签

```sql
-- 替换产品的所有风味标签
UPDATE coffee_products
SET flavor_tags = ARRAY['新标签1', '新标签2', '新标签3']
WHERE id = 1;
```

---

### 方式四：通过代码批量导入

如果你有大量产品需要导入，可以编写 Python 脚本。

**示例脚本** (`scripts/batch_import.py`):

```python
#!/usr/bin/env python3
"""
批量导入咖啡产品及其风味标签
"""

import sys
import os
import json

workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
sys.path.insert(0, workspace_path)

from sqlalchemy import text
from src.storage.database.db import get_engine
from sqlalchemy.orm import sessionmaker


def get_db_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def batch_import_products(products_data):
    """批量导入产品"""
    session = get_db_session()

    try:
        for product in products_data:
            # 插入或更新产品
            session.execute(
                text("""
                    INSERT INTO coffee_products (
                        roaster_brand, product_name, bean_variety,
                        origin_country, origin_region, altitude,
                        roast_level, processing_method, flavor_tags,
                        tasting_notes, brew_suggestions, price_range,
                        source_url, is_active
                    ) VALUES (
                        :brand, :name, :variety, :origin, :region, :altitude,
                        :roast, :processing, :flavor_tags, :tasting_notes,
                        :brew_suggestions, :price, :source_url, :is_active
                    )
                    ON CONFLICT (roaster_brand, product_name)
                    DO UPDATE SET
                        flavor_tags = EXCLUDED.flavor_tags,
                        tasting_notes = EXCLUDED.tasting_notes,
                        price_range = EXCLUDED.price_range
                """),
                {
                    "brand": product['brand'],
                    "name": product['name'],
                    "variety": product.get('variety'),
                    "origin": product.get('origin'),
                    "region": product.get('region'),
                    "altitude": product.get('altitude'),
                    "roast": product.get('roast'),
                    "processing": product.get('processing'),
                    "flavor_tags": product.get('flavor_tags', []),
                    "tasting_notes": product.get('tasting_notes'),
                    "brew_suggestions": json.dumps(product.get('brew_suggestions')),
                    "price": product.get('price'),
                    "source_url": product.get('source_url'),
                    "is_active": True
                }
            )

        session.commit()
        print(f"✅ 成功导入 {len(products_data)} 个产品")

    except Exception as e:
        session.rollback()
        print(f"❌ 导入失败: {e}")
    finally:
        session.close()


# 示例数据
products = [
    {
        "brand": "示例烘焙商",
        "name": "示例咖啡豆",
        "variety": "Bourbon",
        "origin": "Colombia",
        "region": "Huila",
        "altitude": "1600-1800m",
        "roast": "Medium",
        "processing": "Washed",
        "flavor_tags": ["柑橘", "焦糖", "坚果", "巧克力"],
        "tasting_notes": "平衡的酸度和甜感，尾段带有坚果和巧克力的余韵。",
        "brew_suggestions": {"method": "V60", "temp": "90-92°C", "ratio": "1:15"},
        "price": "60元/227g",
        "source_url": "https://example.com"
    }
]

if __name__ == "__main__":
    batch_import_products(products)
```

---

## 📝 风味标签规范

### 命名规范

1. **简洁明了**：使用 2-4 个字的简洁词汇
   - ✅ 正确：茉莉花、柑橘、焦糖
   - ❌ 错误：具有浓郁茉莉花香气、柑橘类水果、焦糖甜味

2. **常用词汇**：优先使用咖啡行业的通用词汇
   - 花香类：茉莉花、玫瑰、洋甘菊、薰衣草
   - 果香类：柑橘、草莓、葡萄柚、蓝莓、桃子
   - 坚果类：杏仁、榛子、核桃、腰果
   - 巧克力类：黑巧克力、牛奶巧克力、可可
   - 糖类：焦糖、蜂蜜、红糖、枫糖
   - 谷物类：燕麦、面包、吐司
   - 香料类：肉桂、丁香、胡椒、豆蔻

3. **避免重复**：同一个产品中不要添加相似的风味标签
   - ✅ 正确：柑橘
   - ❌ 错误：柑橘、橙子、橙味（太相似）

### 标签分类

| 分类 | 标签示例 |
|------|----------|
| **花香** | 茉莉花、玫瑰、洋甘菊、薰衣草、桂花 |
| **果香** | 柑橘、草莓、葡萄柚、蓝莓、桃子、芒果、菠萝 |
| **坚果** | 杏仁、榛子、核桃、腰果、花生 |
| **巧克力** | 黑巧克力、牛奶巧克力、可可 |
| **糖类** | 焦糖、蜂蜜、红糖、枫糖、太妃糖 |
| **谷物** | 燕麦、面包、吐司、饼干 |
| **香料** | 肉桂、丁香、胡椒、豆蔻、八角 |
| **茶类** | 红茶、绿茶、乌龙茶、伯爵茶 |
| **酒类** | 红酒、朗姆酒、白兰地 |

---

## 🔄 更新向量索引

添加或修改风味标签后，建议重新生成产品的向量索引，以确保搜索结果准确。

```bash
python scripts/regenerate_embeddings.py
```

---

## ✅ 最佳实践

1. **定期更新**：建议每周检查并更新产品数据
2. **质量控制**：确保添加的风味标签准确反映产品的实际风味
3. **一致性**：使用统一的风味标签命名规范
4. **适量添加**：每个产品建议添加 3-6 个风味标签
5. **测试验证**：添加后使用 `expand_flavor_keywords` 和 `search_coffee_products` 工具测试搜索效果

---

## 🐛 常见问题

### Q1: 添加的风味标签不生效？

**A**: 检查以下几点：
1. 确认标签已成功写入数据库
2. 重新生成向量索引：`python scripts/regenerate_embeddings.py`
3. 使用 `expand_flavor_keywords` 工具测试是否能识别新标签

### Q2: 如何批量更新多个产品的风味标签？

**A**: 可以：
1. 使用 SQL 的 `UPDATE` 语句批量更新
2. 编写 Python 脚本批量处理
3. 使用 `update_coffee_database` 工具重新爬取

### Q3: 风味标签数量有限制吗？

**A**: 技术上没有限制，但建议每个产品添加 3-6 个标签，以保持简洁和准确。

### Q4: 如何删除重复的风味标签？

**A**:
```sql
-- 删除产品中的重复标签
UPDATE coffee_products
SET flavor_tags = (
    SELECT array_agg(DISTINCT tag)
    FROM unnest(flavor_tags) AS tag
)
WHERE id = 1;
```

---

## 📞 技术支持

如有问题，请查看：
- 日志文件：`/app/work/logs/bypass/app.log`
- 数据库状态：使用 `list-products` 命令查看
- 向量索引：使用 `regenerate_embeddings.py` 重新生成
