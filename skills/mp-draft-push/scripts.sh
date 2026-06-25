#!/bin/bash
# 微信公众号草稿箱发布工具 - 辅助脚本
# 使用方法: source scripts.sh
#
# 默认优先走 wx-publish-gateway：
#   WXPG_GATEWAY_URL="http://100.64.0.9:38000"
#   WXPG_API_KEY="..."
#   WXPG_ACCOUNT="main"   # 可选
#
# 未配置 WXPG_GATEWAY_URL/WXPG_API_KEY 时，才 fallback 到旧的微信直连模式：
#   WECHAT_APPID / WECHAT_SECRET / PROXY_URL

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "ERROR: missing command: $1" >&2
        return 1
    }
}

require_env() {
    local name=$1
    local val
    eval "val=\${${name}:-}"
    if [[ -z "$val" ]]; then
        echo "ERROR: missing env var: ${name}" >&2
        return 1
    fi
}

# 是否启用 wx-publish-gateway
is_wxpg_enabled() {
    [[ -n "${WXPG_GATEWAY_URL:-}" && -n "${WXPG_API_KEY:-}" ]]
}

# 网关配置是否半残缺（只配了其中一个）
is_wxpg_partial() {
    [[ -n "${WXPG_GATEWAY_URL:-}${WXPG_API_KEY:-}" ]] && ! is_wxpg_enabled
}

wxpg_base_url() {
    printf "%s" "${WXPG_GATEWAY_URL%/}"
}

require_wxpg() {
    require_env WXPG_GATEWAY_URL || return 1
    require_env WXPG_API_KEY     || return 1
}

# 获取代理参数（旧直连 fallback 用）
get_proxy_args() {
    if [[ -n "${PROXY_URL:-}" ]]; then
        echo "-x ${PROXY_URL}"
    else
        echo ""
    fi
}

# ============ 公众号 API ============

# 获取 access_token
# 用法: get_wechat_token
#
# 网关模式：不暴露真实 token，只返回哨兵值；后续 upload/create 函数会忽略该参数并直接调用网关。
# 直连模式：返回微信 access_token。
get_wechat_token() {
    require_cmd curl || return 1
    require_cmd jq   || return 1

    if is_wxpg_enabled; then
        echo "__WXPG_GATEWAY__"
        return 0
    fi
    if is_wxpg_partial; then
        echo "ERROR: WXPG_GATEWAY_URL/WXPG_API_KEY must be configured together" >&2
        return 1
    fi

    require_env WECHAT_APPID  || return 1
    require_env WECHAT_SECRET || return 1

    local proxy_args
    proxy_args=$(get_proxy_args)
    curl -sS ${proxy_args} "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=${WECHAT_APPID}&secret=${WECHAT_SECRET}" \
        | jq -r '.access_token'
}

# 上传图片到公众号永久素材库（封面图专用）
# 用法: upload_wechat_image <token> <image_path>
# 返回: JSON，含 media_id 字段
upload_wechat_image() {
    require_cmd curl || return 1
    local token=$1
    local image_path=$2

    if is_wxpg_enabled; then
        require_wxpg || return 1
        local account_args=()
        if [[ -n "${WXPG_ACCOUNT:-}" ]]; then
            account_args=(-F "account=${WXPG_ACCOUNT}")
        fi
        curl -sS -X POST \
            "$(wxpg_base_url)/v1/media/cover" \
            -H "X-API-Key: ${WXPG_API_KEY}" \
            "${account_args[@]}" \
            -F "file=@${image_path}"
        return $?
    fi
    if is_wxpg_partial; then
        echo "ERROR: WXPG_GATEWAY_URL/WXPG_API_KEY must be configured together" >&2
        return 1
    fi

    local proxy_args
    proxy_args=$(get_proxy_args)
    curl -sS -X POST ${proxy_args} \
        "https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=${token}&type=image" \
        -F "media=@${image_path}"
}

# 上传文章内图片（获取 mmbiz.qpic.cn URL）
# 用法: upload_inline_image <token> <image_path>
# 返回: JSON，含 url 字段
upload_inline_image() {
    require_cmd curl || return 1
    local token=$1
    local image_path=$2

    if is_wxpg_enabled; then
        require_wxpg || return 1
        local account_args=()
        if [[ -n "${WXPG_ACCOUNT:-}" ]]; then
            account_args=(-F "account=${WXPG_ACCOUNT}")
        fi
        curl -sS -X POST \
            "$(wxpg_base_url)/v1/media/inline" \
            -H "X-API-Key: ${WXPG_API_KEY}" \
            "${account_args[@]}" \
            -F "file=@${image_path}"
        return $?
    fi
    if is_wxpg_partial; then
        echo "ERROR: WXPG_GATEWAY_URL/WXPG_API_KEY must be configured together" >&2
        return 1
    fi

    local proxy_args
    proxy_args=$(get_proxy_args)
    curl -sS -X POST ${proxy_args} \
        "https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token=${token}" \
        -F "media=@${image_path}"
}

# 创建草稿
# 用法: create_draft <token> <json_file>
# 返回: JSON，含 media_id 字段（草稿 ID）
#
# json_file 兼容旧的微信 draft/add payload：{"articles":[{...}]}
# 网关模式会自动转换为 /v1/draft 需要的扁平 payload。
create_draft() {
    require_cmd curl || return 1
    require_cmd jq   || return 1
    local token=$1
    local json_file=$2

    if is_wxpg_enabled; then
        require_wxpg || return 1
        local payload
        payload=$(jq -c --arg account "${WXPG_ACCOUNT:-}" '
            .articles[0] as $a
            | {
                title: $a.title,
                content_html: $a.content,
                thumb_media_id: $a.thumb_media_id,
                need_open_comment: ($a.need_open_comment // 1),
                only_fans_can_comment: ($a.only_fans_can_comment // 0)
              }
              + (if (($a.digest // "") != "") then {digest: $a.digest} else {} end)
              + (if (($a.author // "") != "") then {author: $a.author} else {} end)
              + (if ($account != "") then {account: $account} else {} end)
        ' "$json_file") || return 1

        curl -sS -X POST \
            "$(wxpg_base_url)/v1/draft" \
            -H "X-API-Key: ${WXPG_API_KEY}" \
            -H "Content-Type: application/json; charset=utf-8" \
            --data-binary "$payload"
        return $?
    fi
    if is_wxpg_partial; then
        echo "ERROR: WXPG_GATEWAY_URL/WXPG_API_KEY must be configured together" >&2
        return 1
    fi

    local proxy_args
    proxy_args=$(get_proxy_args)
    curl -sS -X POST ${proxy_args} \
        "https://api.weixin.qq.com/cgi-bin/draft/add?access_token=${token}" \
        -H "Content-Type: application/json; charset=utf-8" \
        -d @"${json_file}"
}

echo "脚本已加载。可用函数:"
echo "  get_wechat_token     - 网关模式返回哨兵值；直连模式获取公众号 access_token"
echo "  upload_wechat_image  - 上传封面图，返回 media_id"
echo "  upload_inline_image  - 上传文章内图片，返回 mmbiz.qpic.cn URL"
echo "  create_draft         - 创建草稿，返回草稿 media_id"
echo ""
if is_wxpg_enabled; then
    echo "✅ wx-publish-gateway 已配置: $(wxpg_base_url)"
    if [[ -n "${WXPG_ACCOUNT:-}" ]]; then
        echo "✅ 默认网关账号: ${WXPG_ACCOUNT}"
    fi
elif is_wxpg_partial; then
    echo "⚠️  WXPG_GATEWAY_URL/WXPG_API_KEY 配置不完整，将无法使用网关" >&2
elif [[ -n "${PROXY_URL:-}" ]]; then
    echo "⚠️  未配置 wx-publish-gateway，fallback 到代理直连: ${PROXY_URL}"
else
    echo "⚠️  未配置 wx-publish-gateway，也未配置代理；将 fallback 到微信直连模式"
fi
