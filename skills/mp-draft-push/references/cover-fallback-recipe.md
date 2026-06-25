# 公众号封面图 Pillow 兜底方案

当 `gen_image` / gpt-image-2 API 不可用时，用 Python Pillow 快速生成一张有基本视觉感的封面。

## 前提

```bash
pip install Pillow  # 通常已预装
```

## 基础模板

```python
from PIL import Image, ImageDraw, ImageFont

img = Image.new('RGB', (900, 383), '#0f172a')
draw = ImageDraw.Draw(img)

# 简易渐变背景
for y in range(383):
    r = int(15 + y * 5 / 383)
    g = int(23 + y * 8 / 383)
    b = int(42 + y * 10 / 383)
    draw.line([(0, y), (900, y)], fill=(r, g, b))

# 装饰圆点
import random
random.seed(42)
for _ in range(30):
    x = random.randint(50, 400)
    y = random.randint(50, 330)
    r = random.randint(2, 6)
    draw.ellipse([x-r, y-r, x+r, y+r], fill='#38bdf8')

# 手机图标
draw.rounded_rectangle([80, 100, 200, 300], radius=20, fill='#1e293b')
draw.rounded_rectangle([85, 105, 195, 295], radius=16, fill='#0f172a')
draw.text((140, 190), '👉', fill='#38bdf8')

# 右侧文字（用系统字体）
try:
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 32)
    font2 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
except OSError:
    font = font2 = ImageFont.load_default()
draw.text((280, 150), 'AI Topic', fill='#38bdf8', font=font)
draw.text((280, 195), '副标题', fill='#94a3b8', font=font2)

img.save('/tmp/wechat_cover.png')  # 7-10KB
```

## 关键参数
- 尺寸：**900×383**（公众号头条封面标准比例）
- 右侧 30-40% 区域留白/padding，方便标题叠字
- 颜色：深色系（`#0f172a` / `#1e293b` / `#38bdf8`）适合科技/AI选题
- 暖色系（`#f8f0e3` / `#d4a574`）适合生活/情感选题
- 文字不宜多，2-3 个词即可，重点靠图片传递基调
