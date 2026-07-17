# SMaTCP 数据集成说明

## 完成内容

已将 `somatic_fil.csv` 中的真实数据集成到 `index.html` 的搜索功能中。

## 数据说明

- **原始数据**: somatic_fil.csv (80,965条记录)
- **已加载**: 1,000条记录
- **字段**: Chromosome, Position, Ref, Alt, VAF, Region, Gene, Subtissue, Mutation_type

## 使用方法

1. 在浏览器中打开 `index.html`
2. 页面自动显示 CSMD1 基因的数据
3. 可以搜索其他基因、组织或染色体区域

## 搜索功能

- **基因搜索**: 输入基因名称（如 CSMD1, RBFOX1）
- **组织搜索**: 输入组织名称（如 Whole_Blood, Heart_Left_Ventricle）
- **区域搜索**: 输入染色体区域（如 chr8:3959485-4000000）
- **类型搜索**: 输入突变类型（SNV, INDEL）

## 更新数据

如需加载更多数据：

```bash
# 编辑 convert_csv_to_js.py，修改数量限制
# 找到: for i, mut in enumerate(mutations[:1000]):
# 改为: for i, mut in enumerate(mutations[:5000]):

# 重新运行
python3 convert_csv_to_js.py
```

## 文件说明

- `index.html` - 主页面
- `data_output.js` - 数据文件
- `convert_csv_to_js.py` - 数据转换脚本
- `somatic_fil.csv` - 原始CSV数据
