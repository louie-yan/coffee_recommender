# 向量维度修复文档

## 问题描述

部署时出现以下错误：
```
ERROR: expected 1536 dimensions, not 2048 (SQLSTATE 22000)
```

### 根本原因

1. 嵌入模型（Embedding Model）生成 **2048 维**向量
2. 数据库中的 `coffee_embeddings` 表的 `embedding` 列可能被错误地设置为 **1536 维**
3. 部署系统在同步数据库时，尝试复制或检查向量数据时发现维度不匹配

## 修复步骤

### 1. 运行修复脚本

```bash
python scripts/fix_vector_dimension.py
```

该脚本会：
- 检查当前向量维度
- 如果维度不匹配，清空表数据
- 删除并重建表为 2048 维
- 重新创建索引

### 2. 重新生成向量数据

```bash
python scripts/regenerate_embeddings.py
```

该脚本会：
- 从 `coffee_products` 表读取所有产品数据
- 为每个产品生成 2048 维向量
- 将向量存储到 `coffee_embeddings` 表

### 3. 验证修复

测试 Agent 是否能正常工作：
```bash
python -m src.main
```

或使用测试工具：
```bash
python -c "from tools.coffee.coffee_recommender import vector_search_products; print(vector_search_products('花香', {}, 5))"
```

## 预防措施

### 1. 数据库初始化脚本

创建了 `scripts/init_database.py` 脚本，用于初始化数据库表结构。

在首次部署或需要重置数据库时，运行：
```bash
python scripts/init_database.py
```

该脚本确保：
- 所有表使用正确的结构
- `coffee_embeddings` 表的 `embedding` 列为 `vector(2048)`
- 不创建可能不兼容的向量索引（2048 维超过某些 pgvector 版本的限制）

### 2. 向量维度检查

在 `scripts/regenerate_embeddings.py` 中内置了维度检查：

```python
def verify_and_recreate_vector_table():
    """验证并重建向量表，确保维度正确"""
    # 检查当前向量列的维度
    # 如果不是 2048 维，自动重建表
```

### 3. 嵌入模型配置

确保嵌入模型的维度与数据库表结构一致：

```python
# 当前配置
embed_dimension = 2048  # coze-coding-dev-sdk 默认输出维度
```

## 技术细节

### 向量表结构

```sql
CREATE TABLE coffee_embeddings (
    id SERIAL PRIMARY KEY,
    coffee_id INTEGER REFERENCES coffee_products(id) ON DELETE CASCADE,
    embedding vector(2048),  -- 必须是 2048 维
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引（不创建向量索引）
CREATE INDEX idx_coffee_embeddings_coffee_id ON coffee_embeddings(coffee_id);
CREATE INDEX idx_coffee_embeddings_created_at ON coffee_embeddings(created_at);
```

### 为什么不创建向量索引？

由于 pgvector 对 2000+ 维度的支持有限，创建向量索引可能导致性能问题或失败。对于小规模数据（< 1000 条），使用全表扫描的线性搜索已经足够快。

### 向量生成

```python
from coze_coding_dev_sdk import EmbeddingClient

client = EmbeddingClient()
embedding = client.embed_text(text)  # 返回 2048 维向量
```

## 常见问题

### Q1: 为什么会出现维度不匹配？

A: 可能的原因：
- 之前使用了不同的嵌入模型（如 OpenAI 的 text-embedding-ada-002，1536 维）
- 手动创建表时使用了错误的维度
- 数据库迁移时没有正确更新表结构

### Q2: 如何避免以后再出现这个问题？

A:
1. 使用 `scripts/init_database.py` 初始化数据库
2. 在修改嵌入模型时，同时更新表结构
3. 运行 `scripts/regenerate_embeddings.py` 时会自动检查维度

### Q3: 1536 维的向量数据能自动转换为 2048 维吗？

A: 不能。向量维度是固定的，无法直接转换。必须：
1. 删除旧的向量数据
2. 使用新模型重新生成向量
3. 存储到表中

### Q4: 如果有大量产品，重新生成向量需要多久？

A: 大约每个产品需要 1-2 秒（包括 API 调用和数据库写入）。1000 个产品大约需要 15-30 分钟。

## 相关脚本

| 脚本 | 用途 |
|------|------|
| `scripts/init_database.py` | 初始化数据库表结构 |
| `scripts/fix_vector_dimension.py` | 修复向量维度问题 |
| `scripts/regenerate_embeddings.py` | 重新生成所有产品向量 |

## 验证清单

修复完成后，验证以下项目：

- [ ] `coffee_embeddings` 表的 `embedding` 列为 `vector(2048)`
- [ ] 所有产品都有对应的向量数据
- [ ] 向量搜索功能正常工作
- [ ] Agent 能够推荐产品
- [ ] 部署时不再出现维度错误

## 联系支持

如果问题仍然存在，请检查：
1. PostgreSQL 版本是否支持 pgvector
2. pgvector 扩展是否已安装：`CREATE EXTENSION IF NOT EXISTS vector;`
3. 数据库连接和权限是否正常
