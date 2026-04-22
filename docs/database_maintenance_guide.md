# 数据库维护脚本使用指南

## 脚本列表

| 脚本 | 用途 | 运行时机 |
|------|------|----------|
| `scripts/init_database.py` | 初始化数据库表结构 | 首次部署或重置数据库 |
| `scripts/deploy_pre_check.py` | 部署前检查 | 每次部署前运行 |
| `scripts/fix_vector_dimension.py` | 修复向量维度问题 | 遇到维度错误时 |
| `scripts/regenerate_embeddings.py` | 重新生成向量数据 | 向量数据缺失或需要更新时 |

## 详细说明

### 1. init_database.py - 初始化数据库

**用途**：创建所有必要的数据库表，确保表结构正确。

**运行方法**：
```bash
python scripts/init_database.py
```

**执行内容**：
- 创建 `coffee_products` 表（咖啡产品表）
- 创建 `brewing_knowledge` 表（冲煮知识表）
- 创建 `coffee_embeddings` 表（向量索引表，2048 维）
- 创建必要的索引

**注意事项**：
- 如果表已存在，不会重复创建
- 向量表会确保使用 2048 维度
- 如果表结构不正确，需要先删除表再运行此脚本

### 2. deploy_pre_check.py - 部署前检查

**用途**：在部署前检查数据库状态，确保不会因为表结构问题导致部署失败。

**运行方法**：
```bash
python scripts/deploy_pre_check.py
```

**检查内容**：
- `coffee_embeddings` 表是否存在
- 向量维度是否为 2048
- 向量数据数量
- 产品数据数量
- 数据一致性检查

**返回值**：
- 返回 0：检查通过，可以部署
- 返回 1：检查失败，需要先修复

**建议**：在每次部署前运行此脚本。

### 3. fix_vector_dimension.py - 修复向量维度

**用途**：修复向量维度不匹配的问题（如 1536 vs 2048）。

**运行方法**：
```bash
python scripts/fix_vector_dimension.py
```

**执行内容**：
- 检查当前向量维度
- 如果维度不是 2048，清空表数据
- 删除并重建表为 2048 维
- 重建索引

**注意事项**：
- 会清空所有向量数据
- 需要后续运行 `regenerate_embeddings.py` 重新生成

### 4. regenerate_embeddings.py - 重新生成向量

**用途**：为所有咖啡产品生成向量索引（2048 维）。

**运行方法**：
```bash
python scripts/regenerate_embeddings.py
```

**执行内容**：
- 从 `coffee_products` 表读取所有活跃产品
- 为每个产品生成 2048 维向量
- 存储到 `coffee_embeddings` 表
- 验证向量维度

**预计时间**：
- 每个产品约 1-2 秒
- 100 个产品约 2-3 分钟

## 典型使用场景

### 场景 1：首次部署

```bash
# 1. 初始化数据库
python scripts/init_database.py

# 2. 添加产品数据（通过 update_coffee_database 工具或其他方式）

# 3. 生成向量索引
python scripts/regenerate_embeddings.py

# 4. 部署前检查
python scripts/deploy_pre_check.py
```

### 场景 2：遇到维度错误

错误信息：
```
ERROR: expected 1536 dimensions, not 2048 (SQLSTATE 22000)
```

修复步骤：
```bash
# 1. 修复维度问题
python scripts/fix_vector_dimension.py

# 2. 重新生成向量
python scripts/regenerate_embeddings.py

# 3. 验证修复
python scripts/deploy_pre_check.py
```

### 场景 3：更新产品数据后

```bash
# 1. 更新产品数据（通过 Agent 的 update_coffee_database 工具）

# 2. 重新生成向量索引
python scripts/regenerate_embeddings.py

# 3. 验证
python scripts/deploy_pre_check.py
```

### 场景 4：每次部署前

```bash
# 部署前检查
python scripts/deploy_pre_check.py

# 如果检查通过，继续部署
# 如果检查失败，根据提示修复后再部署
```

## 验证清单

运行脚本后，验证以下项目：

### init_database.py
- [ ] `coffee_products` 表已创建
- [ ] `brewing_knowledge` 表已创建
- [ ] `coffee_embeddings` 表已创建
- [ ] `embedding` 列为 `vector(2048)`
- [ ] 索引已创建

### deploy_pre_check.py
- [ ] 向量维度为 2048
- [ ] 向量数据数量 >= 产品数据数量
- [ ] 无错误信息

### fix_vector_dimension.py
- [ ] 表已重建
- [ ] 维度为 2048
- [ ] 旧数据已清空

### regenerate_embeddings.py
- [ ] 所有产品都有向量数据
- [ ] 向量维度为 2048
- [ ] 无错误日志

## 故障排查

### 问题 1：无法连接数据库

**错误**：
```
ERROR: could not connect to server
```

**解决方案**：
1. 检查环境变量 `PGDATABASE_URL` 是否正确设置
2. 检查数据库服务是否运行
3. 检查网络连接

### 问题 2：pgvector 扩展不存在

**错误**：
```
ERROR: type "vector" does not exist
```

**解决方案**：
在数据库中安装 pgvector 扩展：
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 问题 3：向量生成失败

**错误**：
```
ERROR: 生成 embedding 失败
```

**解决方案**：
1. 检查网络连接
2. 检查 API 密钥是否正确
3. 检查 `coze_coding_dev_sdk` 是否正确安装

### 问题 4：维度检查失败

**错误**：
```
ERROR: 向量维度不匹配！期望: 2048 维，当前: 1536 维
```

**解决方案**：
```bash
python scripts/fix_vector_dimension.py
python scripts/regenerate_embeddings.py
```

## 技术细节

### 向量维度说明

- **当前模型**：coze-coding-dev-sdk
- **输出维度**：2048
- **数据库列类型**：`vector(2048)`
- **旧模型**：OpenAI text-embedding-ada-002 (1536 维)

### 为什么不创建向量索引？

由于 pgvector 对 2000+ 维度的支持有限：
- 创建索引可能失败
- 性能提升不明显
- 对于小规模数据（< 1000 条），线性搜索已经足够快

### 索引策略

当前使用：
- `idx_coffee_embeddings_coffee_id`：按产品 ID 查询
- `idx_coffee_embeddings_created_at`：按创建时间查询

向量搜索使用全表扫描 + 计算相似度。

## 联系支持

如果遇到问题：
1. 查看本文档的故障排查部分
2. 检查日志输出
3. 查看相关文档：
   - `docs/vector_dimension_fix.md`
   - `docs/scraper_update.md`
