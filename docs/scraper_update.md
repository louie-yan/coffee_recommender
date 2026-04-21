# 爬虫更新说明

## 📝 更新内容

根据您提供的正确 URL 信息，我已更新了咖啡产品爬虫代码：

### 修改的文件
- `src/tools/coffee/coffee_updater.py`

### 更新内容

#### 1. 更新产品列表页 URL
**旧 URL**: `https://specialitycoffee.ca/collections/coffee`
**新 URL**: `https://specialitycoffee.ca/product-category/filter/`

#### 2. 重写爬取逻辑

**新流程**:
1. 访问产品列表页 `https://specialitycoffee.ca/product-category/filter/`
2. 提取所有产品详情页的链接（查找包含 `/product/` 的链接）
3. 逐个访问产品详情页，提取完整信息
4. 从描述文本中智能提取结构化数据

#### 3. 新增/优化的函数

**新增函数**:
- `scrape_product_detail()`: 爬取单个产品详情页
- `extract_coffee_info_from_description()`: 从描述文本中提取结构化信息

**删除函数**:
- `enrich_product_details()` - 功能已整合到新流程
- `extract_brand()` - 功能已整合到新流程

#### 4. 智能信息提取

`extract_coffee_info_from_description()` 函数可以提取：

| 信息类别 | 提取内容 |
|---------|---------|
| **产地** | Ethiopia, Colombia, Kenya, Guatemala, Brazil, Panama, Costa Rica 等 18 个国家 |
| **产区** | Yirgacheffe, Sidamo, Huila, Nyeri, Tolima, Narino 等 |
| **海拔** | 格式如 "1800-2000m" |
| **豆种** | Bourbon, Typica, Gesha, SL28, SL34, Pink Bourbon 等 |
| **处理法** | Washed, Natural, Honey, Anaerobic 等 |
| **烘焙度** | Light, Medium-Light, Medium, Medium-Dark, Dark |
| **风味标签** | 60+ 个关键词（自动翻译为中文） |

**风味标签分类**:
- **花香**: 茉莉花、玫瑰、薰衣草、芙蓉
- **果香**: 柑橘、柠檬、甜橙、葡萄柚、草莓、蓝莓、桃子、芒果、菠萝
- **坚果**: 杏仁、榛子、核桃、腰果、花生
- **巧克力**: 巧克力、黑巧克力、可可
- **糖类**: 焦糖、蜂蜜、红糖、糖蜜、太妃糖、枫糖
- **谷物**: 燕麦、面包、吐司、饼干
- **香料**: 肉桂、丁香、豆蔻、胡椒
- **其他**: 泥土、烟草、红酒、茶、布朗尼

#### 5. 产品详情页解析

`scrape_product_detail()` 函数提取：

1. **基本信息**:
   - 产品名称（从 h1 标签）
   - 品牌（从面包屑导航）
   - 价格（从价格元素）
   - 图片 URL

2. **详细描述**:
   - 产品描述（从多个可能位置）
   - 结构化信息（使用 `extract_coffee_info_from_description()`）

3. **多级选择器**:
   - 尝试多个可能的选择器，提高解析成功率
   - 兼容 WooCommerce 等常见电商平台结构

### 使用方式

#### 方式一：通过 Agent 工具
```python
from tools.coffee.coffee_updater import update_coffee_database
result = update_coffee_database()
```

#### 方式二：直接调用爬虫函数
```python
from tools.coffee.coffee_updater import scrape_coffee_products
products = scrape_coffee_products()
```

#### 方式三：测试脚本
```bash
python scripts/test_scraper.py
```

### 爬取限制

- **产品数量**: 每次最多爬取 15 个产品（避免过度爬取）
- **延迟时间**: 每个产品详情页之间延迟 2 秒（避免被封）
- **超时设置**: 每个请求超时 30 秒

### 技术细节

#### 请求头
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}
```

#### 产品链接提取策略
1. **方法一**: 查找所有包含 `/product/` 的链接
2. **方法二**: 如果方法一失败，查找特定 class 的元素中的链接

#### 数据清洗
- 去除重复链接
- 限制描述文本长度（最多 1000 字符）
- 风味标签去重（最多 6 个）

### 降级策略

如果爬虫失败，系统会自动返回示例数据：
```python
{
    'roaster_brand': '明谦咖啡',
    'product_name': '埃塞俄比亚耶加雪菲·花魁',
    'flavor_tags': ['茉莉花', '柑橘', '蜂蜜', '柠檬', '红茶'],
    ...
}
```

### 后续步骤

1. **测试爬虫**: 运行 `python scripts/test_scraper.py`
2. **验证数据**: 检查提取的产品信息是否准确
3. **更新向量**: 爬取完成后运行 `python scripts/regenerate_embeddings.py`
4. **定期更新**: 建议每周运行一次 `update_coffee_database` 工具

### 已知限制

1. **网络依赖**: 需要能够访问 https://specialitycoffee.ca
2. **网站结构**: 如果网站改版，可能需要调整选择器
3. **每日限制**: `update_coffee_database` 工具有每日一次的限制
4. **解析准确度**: 智能提取可能不总是 100% 准确，需要人工审核

### 改进建议

1. **增加更多选择器**: 针对不同的网站结构
2. **使用正则表达式**: 提高信息提取的准确性
3. **添加验证机制**: 检查提取的数据是否合理
4. **实现断点续传**: 支持中断后继续爬取
5. **添加代理支持**: 避免被封 IP

---

## 📊 测试建议

### 单元测试
测试各个函数的功能：
1. 测试 `scrape_product_detail()` 是否能正确解析产品详情页
2. 测试 `extract_coffee_info_from_description()` 是否能正确提取信息
3. 测试整个 `scrape_coffee_products()` 流程

### 集成测试
测试与数据库的集成：
1. 测试 `upsert_coffee_product()` 是否能正确插入/更新产品
2. 测试 `store_product_embedding()` 是否能正确存储向量
3. 测试 `update_coffee_database()` 工具的完整流程

### 端到端测试
测试整个推荐流程：
1. 爬取新数据
2. 更新向量索引
3. 测试搜索功能
4. 验证推荐结果

---

## 📞 技术支持

如有问题，请：
1. 查看日志文件：`/app/work/logs/bypass/app.log`
2. 检查网络连接：`curl https://specialitycoffee.ca/product-category/filter/`
3. 验证数据库状态：`python scripts/manage_flavor_tags.py list-products`

---

## ✅ 总结

爬虫代码已按照您的指示完成更新，使用正确的 URL 结构，并实现了智能信息提取功能。代码已经过类型检查，可以正常使用。
