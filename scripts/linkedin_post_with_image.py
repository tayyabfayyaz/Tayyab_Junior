"""Post to LinkedIn with an AI-generated image about 'The Future of AI Native'."""
import json
import os
import sys
import math
import random
import httpx
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent
MEMORY_DIR = ROOT / "memory"
IMAGE_PATH = ROOT / "scripts" / "ai_native_post.png"

# ── Post content ────────────────────────────────────────────────────────────
POST_TEXT = """🚀 The Future is AI Native

We're not just adding AI to existing products — we're reimagining what software looks like when intelligence is the foundation, not the feature.

AI Native means:
🧠 Every workflow is autonomous by default
⚡ Systems that learn, adapt, and act — not just respond
🔗 Humans and AI collaborating as equal partners
📡 Real-time reasoning embedded at every layer

At FTE (Future Talent Engine), we're building this future today — where AI doesn't sit on the side, it sits at the center.

The question isn't whether AI will transform your industry. It's whether you'll be the one who shapes that transformation.

What does "AI Native" mean to you? Drop your thoughts below 👇

#AINative #FutureOfWork #ArtificialIntelligence #Innovation #AIFirst #TechLeadership"""


# ── Image generation ─────────────────────────────────────────────────────────
def generate_image(path: Path):
    W, H = 1200, 628
    img = Image.new("RGB", (W, H), color=(8, 12, 28))
    draw = ImageDraw.Draw(img)

    # Background gradient (manual horizontal strips)
    for y in range(H):
        ratio = y / H
        r = int(8 + ratio * 20)
        g = int(12 + ratio * 15)
        b = int(28 + ratio * 40)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Neural network nodes
    random.seed(42)
    nodes = []
    for _ in range(45):
        x = random.randint(40, W - 40)
        y = random.randint(40, H - 40)
        nodes.append((x, y))

    # Draw connections first (faint)
    for i, (x1, y1) in enumerate(nodes):
        for x2, y2 in nodes[i + 1:]:
            dist = math.hypot(x2 - x1, y2 - y1)
            if dist < 200:
                alpha = max(20, int(60 * (1 - dist / 200)))
                draw.line([(x1, y1), (x2, y2)], fill=(0, 180, 255, alpha), width=1)

    # Draw nodes
    for x, y in nodes:
        r = random.randint(3, 7)
        draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=(0, 210, 255))
        # glow ring
        draw.ellipse(
            [(x - r - 3, y - r - 3), (x + r + 3, y + r + 3)],
            outline=(0, 150, 220), width=1,
        )

    # Dark semi-transparent overlay panel for text
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(panel)
    pdraw.rectangle([(60, 80), (W - 60, H - 80)], fill=(5, 10, 25, 190))
    img = Image.alpha_composite(img.convert("RGBA"), panel).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Try to load system fonts, fall back to default
    def get_font(size, bold=False):
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        for c in candidates:
            if Path(c).exists():
                return ImageFont.truetype(c, size)
        return ImageFont.load_default()

    # Accent line
    draw.rectangle([(90, 115), (190, 120)], fill=(0, 180, 255))
    draw.rectangle([(200, 115), (230, 120)], fill=(100, 80, 255))

    # Main headline
    font_headline = get_font(62, bold=True)
    draw.text((90, 130), "The Future is", font=font_headline, fill=(255, 255, 255))
    draw.text((90, 205), "AI Native", font=font_headline, fill=(0, 210, 255))

    # Subtitle
    font_sub = get_font(26)
    subtitle = "Intelligence at the foundation — not the feature."
    draw.text((90, 295), subtitle, font=font_sub, fill=(160, 200, 240))

    # Three pillars
    font_pill = get_font(22, bold=True)
    font_desc = get_font(19)

    pillars = [
        ("⚡ Autonomous", "Workflows that act,\nnot just respond"),
        ("🧠 Adaptive", "Systems that learn\nand evolve in real-time"),
        ("🤝 Collaborative", "Humans + AI as\nequal partners"),
    ]

    col_x = [90, 430, 770]
    for i, (title, desc) in enumerate(pillars):
        x = col_x[i]
        draw.rectangle([(x, 355), (x + 310, 360)], fill=(0, 150, 220))
        draw.text((x, 368), title, font=font_pill, fill=(0, 210, 255))
        draw.text((x, 400), desc, font=font_desc, fill=(180, 210, 240))

    # Brand tag
    font_brand = get_font(20, bold=True)
    draw.text((90, H - 100), "FTE · Future Talent Engine", font=font_brand, fill=(0, 180, 255))
    draw.text((90, H - 72), "#AINative  #FutureOfWork  #AIFirst", font=font_desc, fill=(100, 140, 180))

    img.save(path, "PNG", optimize=True)
    print(f"[image] Saved → {path}")


# ── LinkedIn helpers ─────────────────────────────────────────────────────────
def get_token() -> str:
    token_path = MEMORY_DIR / "linkedin_token.json"
    if token_path.exists():
        return json.loads(token_path.read_text()).get("access_token", "")
    return os.getenv("LINKEDIN_ACCESS_TOKEN", "")


def get_person_urn(headers: dict, client: httpx.Client) -> str:
    import re
    r = client.get("https://api.linkedin.com/v2/userinfo", headers=headers)
    r.raise_for_status()
    sub = r.json().get("sub", "")
    m = re.search(r":(\d+)$", sub)
    member_id = m.group(1) if m else sub
    return f"urn:li:person:{member_id}"


def register_image_upload(author_urn: str, headers: dict, client: httpx.Client) -> tuple[str, str]:
    """Register image upload, return (upload_url, asset_urn)."""
    payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": author_urn,
            "serviceRelationships": [
                {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
            ],
        }
    }
    r = client.post(
        "https://api.linkedin.com/v2/assets?action=registerUpload",
        json=payload,
        headers=headers,
    )
    if not r.is_success:
        print(f"[linkedin] Register upload error: {r.text}")
    r.raise_for_status()
    data = r.json()
    upload_url = data["value"]["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    asset_urn = data["value"]["asset"]
    return upload_url, asset_urn


def upload_image(upload_url: str, image_path: Path, token: str):
    """Upload image binary to LinkedIn's upload URL."""
    image_bytes = image_path.read_bytes()
    # LinkedIn upload requires a plain POST with binary body
    r = httpx.put(
        upload_url,
        content=image_bytes,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "image/png",
        },
        timeout=60,
    )
    if not r.is_success:
        print(f"[linkedin] Image upload error ({r.status_code}): {r.text}")
    r.raise_for_status()
    print(f"[image] Uploaded to LinkedIn ({len(image_bytes)//1024} KB)")


def publish_post(author_urn: str, asset_urn: str, text: str, headers: dict, client: httpx.Client) -> str:
    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "description": {"text": "The Future of AI Native"},
                        "media": asset_urn,
                        "title": {"text": "The Future is AI Native"},
                    }
                ],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    r = client.post("https://api.linkedin.com/v2/ugcPosts", json=payload, headers=headers)
    if not r.is_success:
        print(f"[linkedin] Post error body: {r.text}")
    r.raise_for_status()
    post_id = r.headers.get("x-linkedin-id") or r.json().get("id", "unknown")
    return post_id


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("[step 1/4] Generating AI Native image …")
    generate_image(IMAGE_PATH)

    token = get_token()
    if not token:
        sys.exit("ERROR: LinkedIn access token not found")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    with httpx.Client(timeout=30) as client:
        print("[step 2/4] Resolving LinkedIn person URN …")
        author_urn = get_person_urn(headers, client)
        print(f"           author = {author_urn}")

        print("[step 3/4] Registering image upload with LinkedIn …")
        upload_url, asset_urn = register_image_upload(author_urn, headers, client)
        print(f"           asset  = {asset_urn}")

    print("[step 3/4] Uploading image …")
    upload_image(upload_url, IMAGE_PATH, token)

    with httpx.Client(timeout=30) as client:
        print("[step 4/4] Publishing post …")
        post_id = publish_post(author_urn, asset_urn, POST_TEXT, headers, client)

    print(f"\n✅ Posted! post_id = {post_id}")
    print(f"   View: https://www.linkedin.com/feed/")


if __name__ == "__main__":
    main()
