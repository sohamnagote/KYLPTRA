import re
from typing import List, Dict, Any, Optional

# Built-in restrained Apple-quality motion graphics templates
MOTION_GRAPHICS_TEMPLATES = [
    {
        "id": "template-lower-third-modern",
        "name": "Modern Minimal Lower Third",
        "category": "Lower Thirds",
        "description": "Clean, understated presenter title and subtitle.",
        "default_duration": 4.0,
        "default_fields": {"title": "Presenter Name", "subtitle": "Topic / Context"}
    },
    {
        "id": "template-key-takeaway",
        "name": "Key Takeaway Callout Box",
        "category": "Callouts",
        "description": "Elevated card highlighting vital advice or quote.",
        "default_duration": 5.0,
        "default_fields": {"heading": "CORE PRINCIPLE", "body": "Key lesson here"}
    },
    {
        "id": "template-focus-arrow",
        "name": "Focus Highlight Arrow",
        "category": "Emphasis",
        "description": "Subtle directional arrow highlighting on-screen detail.",
        "default_duration": 3.0,
        "default_fields": {"direction": "up", "color": "#8273D6"}
    },
    {
        "id": "template-social-handle",
        "name": "Social Handle Banner",
        "category": "Social",
        "description": "Refined Instagram / YouTube / TikTok handle reminder.",
        "default_duration": 4.0,
        "default_fields": {"platform": "instagram", "handle": "@creator"}
    },
    {
        "id": "template-progress-bar",
        "name": "Gradient Progress Indicator",
        "category": "Timeline",
        "description": "Discrete video progress line at bottom of frame.",
        "default_duration": 0.0,  # Matches clip duration
        "default_fields": {"color": "#8273D6"}
    },
    {
        "id": "template-quote-card",
        "name": "Animated Quote Card",
        "category": "Callouts",
        "description": "Spacious card for impactful one-liners.",
        "default_duration": 5.0,
        "default_fields": {"quote": "Simplicity is the ultimate sophistication."}
    },
    {
        "id": "template-warning-box",
        "name": "Notice / Warning Callout",
        "category": "Callouts",
        "description": "Subtle amber notice callout for common mistakes.",
        "default_duration": 4.0,
        "default_fields": {"alert": "Common Pitfall", "detail": "Avoid doing this"}
    },
    {
        "id": "template-subscribe-prompt",
        "name": "Follow & Save Prompt",
        "category": "Social",
        "description": "Elegant Apple-styled pill reminding viewers to save.",
        "default_duration": 3.5,
        "default_fields": {"text": "Save this reel for later"}
    }
]

def match_broll_suggestions(
    transcript_text: str,
    available_assets: List[Dict[str, Any]],
    max_suggestions: int = 5
) -> List[Dict[str, Any]]:
    """
    Analyzes transcript keywords and ranks imported local B-roll assets
    by relevance score based on tags, name, and category.
    """
    if not available_assets or not transcript_text:
        return []

    words = set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", transcript_text.lower()))

    ranked = []
    for asset in available_assets:
        asset_tags = [t.strip().lower() for t in (asset.get("tags") or "").split(",") if t.strip()]
        asset_name = asset.get("name", "").lower()
        asset_cat = asset.get("category", "").lower()

        match_score = 0
        matched_terms = []

        for tag in asset_tags:
            if tag in words or any(tag in w for w in words):
                match_score += 15
                matched_terms.append(tag)

        if asset_cat in words:
            match_score += 10
            matched_terms.append(asset_cat)

        for w in words:
            if w in asset_name:
                match_score += 8
                if w not in matched_terms:
                    matched_terms.append(w)

        if match_score > 0:
            ranked.append({
                "asset": asset,
                "relevance_score": min(100, match_score),
                "matched_terms": matched_terms
            })

    ranked.sort(key=lambda x: x["relevance_score"], reverse=True)
    return ranked[:max_suggestions]

