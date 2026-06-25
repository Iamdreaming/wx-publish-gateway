# 微信草稿箱 API 限制

> 截止 2026-05-24 确认。后续微信 API 更新后需要重新验证。

## 草稿 API (`/cgi-bin/draft/add`) 支持的字段

```
title, author, digest, content,
content_source_url, thumb_media_id,
need_open_comment (0/1), only_fans_can_comment (0/1),
pic_crop_235_1, pic_crop_1_1,
article_type ("news"/"newspic"),
image_info, cover_info, product_info
```

## 不支持的功能（需发布后在后台手动操作）

| 功能 | 替代方案 |
|------|---------|
| **合集/专辑** | 发布后登录 mp.weixin.qq.com → 文章编辑页面 → 添加到合集 |
| **原创声明** | 发布时系统自动检测。API 草稿不支持预设原创声明。发布后在后台查看原创检测结果 |
| **AI声明/AI生成标注** | 发布时在后台手动勾选 |

## 用户沟通话术

当用户问到 API 是否支持上述功能时，直接回答：

> 这三个 API 都支持不了。合集、原创声明、AI声明都是发布环节在后台手动操作的，微信草稿 API 没有对应字段。先推草稿箱，你登录后台后补充这些设置再发布。
