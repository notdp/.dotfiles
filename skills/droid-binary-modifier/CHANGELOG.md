# Droid Binary Modifier Changelog

## 2025-01-11 - v0.46.0 首次修改

### 修改内容

| 修改项   | 原始                                      | 修改后                   | 说明           |
| -------- | ----------------------------------------- | ------------------------ | -------------- |
| 截断条件 | `if(!H&&!Q)return{text:A,isTruncated:!1}` | `if(!0\|\|!Q)...`        | 永远返回原文   |
| 截断返回 | `isTruncated:!0`                          | `isTruncated:!1`         | 不显示截断提示 |
| 截断参数 | `R=80,T=3`                                | `R=99,T=9`               | 宽度 99/行数 9 |
| 输出预览 | `slice(0,4)`                              | `slice(0,99)`            | 99 行预览      |
| 命令阈值 | `length>50, slice(0,47)`                  | `length>99, slice(0,96)` | 更长命令       |

### 备份

- `~/.local/bin/droid.backup.0.46.0`

### 签名

```bash
codesign --remove-signature ~/.local/bin/droid
# ... 修改 ...
codesign -s - ~/.local/bin/droid
```

---

## 模板

```markdown
## YYYY-MM-DD - vX.X.X

### 修改内容

(列出修改项)

### 备份

- `~/.local/bin/droid.backup.X.X.X`

### 备注

(版本特殊情况，如混淆变量名变化等)
```
