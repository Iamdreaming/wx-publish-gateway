# 微信公众号文章 API 概览

## 两套系统

| 系统 | API | 权限要求 | 适用场景 |
|------|-----|---------|---------|
| 素材库 | `/cgi-bin/material/batchget_material` | 无特殊要求 | 获取存入素材库的图文 |
| 已发布文章 | `/cgi-bin/freepublish/batchget` | **需要公众号认证** | 获取直接发布的文章 |

## 关键发现

- 直接发布（不存素材库）的文章：用 `freepublish` API
- 未认证账号调用 `freepublish`：返回 `48001 api unauthorized`
- mp-draft-push skill 只支持**发布**，不支持读取已发布文章

## 替代方案

API 不可用时：
1. 让用户提供文章内容
2. 手动从公众号后台复制