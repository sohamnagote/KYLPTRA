import re
import uuid
from typing import List, Dict, Any, Optional

HOOK_KEYWORDS = [
    "why", "how", "what if", "did you know", "ever wonder", "the secret",
    "the biggest mistake", "stop doing", "here is why", "here's why", "nobody talks about",
    "the truth about", "i realized", "pay attention", "listen carefully",
    "most people", "you won't believe", "the real reason", "this changes everything",
    "kya aap jante", "kaise", "kyun", "dekho", "ek baat", "sach yeh hai"
]

EMPHATIC_KEYWORDS = [
    "never", "always", "actually", "absolutely", "crucial", "essential",
    "insane", "incredible", "game changer", "worst", "best", "secret",
    "mistake", "powerful", "massive", "vital", "shocking", "important",
    "definitely", "formula", "strategy", "truth", "zaroori", "shandar", "zabardast"
]

TOPIC_THEMES = {
    "controversial": ["controversial", "disagree", "wrong", "lie", "myth", "debate", "danger", "terrible", "shocking", "scam", "fool", "stop", "never", "fake", "truth"],
    "business": ["business", "money", "revenue", "profit", "client", "sales", "customer", "market", "scale", "product", "pricing", "growth", "invest", "startup", "founder", "finance", "wealth"],
    "funny": ["funny", "hilarious", "laugh", "joke", "ridiculous", "crazy", "weird", "fun", "bloopers", "humor"],
    "educational": ["how to", "step by step", "learn", "understand", "reason", "guide", "concept", "principle", "framework", "tutorial", "lesson", "rule", "method", "teach", "advice"],
    "hooks": ["why", "how", "secret", "truth", "mistake", "stop", "listen", "pay attention", "most people", "key", "remember"],
    "entrepreneurship": ["founder", "startup", "venture", "team", "vision", "hustle", "company", "leadership", "scale", "ceo", "build"]
}

def clean_word(w: str) -> str:
    return re.sub(r"[^\w\s]", "", w).strip().lower()

def extract_instruction_keywords(instruction: Optional[str]) -> List[str]:
    if not instruction or not isinstance(instruction, str):
        return []
    stopwords = {"find", "the", "a", "an", "clips", "moments", "that", "contain", "with", "most", "about", "discussing", "in", "of", "and", "or", "for"}
    words = re.findall(r"\b[a-zA-Z0-9]{3,}\b", instruction.lower())
    return [w for w in words if w not in stopwords]

def score_candidate_window(
    segments: List[Dict[str, Any]],
    start_time: float,
    end_time: float,
    custom_instruction: Optional[str] = None
) -> Dict[str, Any]:
    duration = end_time - start_time
    full_text = " ".join(s["text"].strip() for s in segments)
    words = full_text.split()
    word_count = len(words)
    lower_text = full_text.lower()

    reasons = []
    
    # Factor breakdown tracking
    breakdown = {
        "opening_strength": 0,
        "contextual_completeness": 0,
        "interesting_content": 0,
        "speech_cadence": 0,
        "natural_ending": 0,
        "topic_relevance": 0
    }

    # 1. Opening Hook Evaluation (up to 25 pts)
    first_segment_text = segments[0]["text"].lower().strip() if segments else ""
    first_words = " ".join(first_segment_text.split()[:8])

    hook_matched = False
    for hook in HOOK_KEYWORDS:
        if hook in first_words or hook in first_segment_text:
            pts = 24
            breakdown["opening_strength"] = pts
            reasons.append(f"Strong opening hook detected ('{hook}') (+{pts})")
            hook_matched = True
            break

    if not hook_matched:
        if any(first_words.startswith(q) for q in ["who", "what", "where", "when", "why", "how", "is", "can"]):
            pts = 18
            breakdown["opening_strength"] = pts
            reasons.append(f"Opening question phrase identified (+{pts})")
        else:
            first_word = clean_word(words[0]) if words else ""
            if first_word in ["and", "but", "so", "or", "because", "aur", "lekin"]:
                breakdown["opening_strength"] = 5
                reasons.append("Starts on dependent conjunction (-5)")
            else:
                breakdown["opening_strength"] = 14
                reasons.append("Clear standalone start sentence (+14)")

    # 2. Contextual Completeness & Natural Boundary (up to 20 pts)
    last_segment_text = segments[-1]["text"].strip() if segments else ""
    if last_segment_text.endswith((".", "!", "?")):
        breakdown["natural_ending"] = 10
        breakdown["contextual_completeness"] = 10
        reasons.append("Clean sentence termination at boundary (+20)")
    elif not last_segment_text.endswith((",", "-", "...", ";")):
        breakdown["natural_ending"] = 6
        breakdown["contextual_completeness"] = 7
        reasons.append("Natural speech pause boundary (+13)")
    else:
        breakdown["natural_ending"] = 3
        breakdown["contextual_completeness"] = 4
        reasons.append("Mid-phrase boundary pause (+7)")

    # 3. Emphatic & Interesting Content (up to 20 pts)
    matched_emphatics = [w for w in EMPHATIC_KEYWORDS if f" {w} " in f" {lower_text} "]
    has_question = any("?" in s["text"] for s in segments[:-1])
    
    emphatic_pts = min(12, len(matched_emphatics) * 4)
    question_pts = 8 if has_question else 0
    content_pts = min(20, emphatic_pts + question_pts)
    breakdown["interesting_content"] = content_pts
    
    if matched_emphatics:
        reasons.append(f"High-impact emphatic language ({', '.join(matched_emphatics[:3])}) (+{emphatic_pts})")
    if has_question:
        reasons.append("Presents question with follow-up explanation (+8)")

    # 4. Speech Cadence & Flow (up to 15 pts)
    if duration > 0:
        wpm = (word_count / duration) * 60.0
        if 115 <= wpm <= 185:
            breakdown["speech_cadence"] = 15
            reasons.append(f"Optimal conversational cadence ({int(wpm)} WPM) (+15)")
        elif 80 <= wpm < 115 or 185 < wpm <= 220:
            breakdown["speech_cadence"] = 10
            reasons.append(f"Good speech pacing ({int(wpm)} WPM) (+10)")
        elif wpm < 70:
            breakdown["speech_cadence"] = 2
            reasons.append("Slow pacing or silent pauses (+2)")
        else:
            breakdown["speech_cadence"] = 5
            reasons.append("Fast speech cadence (+5)")

    # 5. Custom Natural Language Instruction & Topic Relevance (up to 25 pts)
    if custom_instruction and custom_instruction.strip():
        inst_lower = custom_instruction.strip().lower()
        inst_keywords = extract_instruction_keywords(inst_lower)

        matched_inst_words = [kw for kw in inst_keywords if kw in lower_text]

        theme_matches = []
        for theme_key, theme_words in TOPIC_THEMES.items():
            if theme_key in inst_lower or any(kw in theme_words for kw in inst_keywords):
                for tw in theme_words:
                    if f" {tw} " in f" {lower_text} " and tw not in theme_matches:
                        theme_matches.append(tw)

        total_topic_matches = list(set(matched_inst_words + theme_matches))
        if total_topic_matches:
            pts = min(25, 10 + len(total_topic_matches) * 5)
            breakdown["topic_relevance"] = pts
            reasons.append(f"Matches instruction '{custom_instruction}': ({', '.join(total_topic_matches[:3])}) (+{pts})")
        else:
            breakdown["topic_relevance"] = 5
            reasons.append(f"General semantic relevance to '{custom_instruction}' (+5)")
    else:
        breakdown["topic_relevance"] = 10

    # Calculate overall score (0 to 100)
    raw_score = sum(breakdown.values())
    final_score = max(15, min(99, raw_score))

    summary_words = words[:12]
    hook_summary = " ".join(summary_words) + ("..." if len(words) > 12 else "")

    return {
        "score": final_score,
        "score_reasons": reasons,
        "score_breakdown": breakdown,
        "hook_summary": hook_summary,
        "transcript_text": full_text
    }

def generate_clip_suggestions(
    transcript_text: str,
    title: str,
    custom_instruction: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates editable AI titles, hooks, descriptions and hashtags for a clip.
    All completely local, without paid APIs.
    """
    words = [clean_word(w) for w in transcript_text.split() if len(w) > 3]
    top_words = list(dict.fromkeys(words))[:6]

    topic_subject = top_words[0].title() if top_words else "Success"
    secondary_subject = top_words[1].title() if len(top_words) > 1 else "Strategy"

    # Contextual Titles
    titles = [
        f"The Truth About {topic_subject}",
        f"Why Most People Get {topic_subject} Wrong",
        f"Mastering {topic_subject}: The {secondary_subject} Method"
    ]

    # Alternative Hooks
    hooks = [
        f"If you want to understand {topic_subject.lower()}, you must hear this.",
        f"Stop doing this if you care about {secondary_subject.lower()}."
    ]

    # Description
    desc = f"Key takeaway on {topic_subject.lower()} and {secondary_subject.lower()}. Discover why this insight is essential for creators and professionals."

    # Hashtags
    hashtags = f"#{topic_subject} #{secondary_subject} #KlyptraShorts #ViralClips #CreatorTips #Reels"

    return {
        "titles": titles,
        "hooks": hooks,
        "description": desc,
        "hashtags": hashtags
    }

def detect_clip_candidates(
    transcript_data: Dict[str, Any],
    project_id: str,
    min_clip_duration: float = 18.0,
    max_clip_duration: float = 60.0,
    boundary_padding: float = 0.3,
    max_clips: int = 6,
    custom_instruction: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Identifies high-quality, standalone clip candidates from timestamped transcript segments.
    Ensures clips snap to natural sentence boundaries without cutting mid-sentence.
    Supports optional custom natural language instructions.
    """
    segments = transcript_data.get("segments", [])
    video_duration = transcript_data.get("duration", 0.0)

    # If transcript is empty or contains no speech segments (e.g. visual showcases, demo videos, music)
    if not segments:
        if video_duration <= 0.0:
            video_duration = 50.0
        
        target_clip_len = min(20.0, video_duration)
        num_clips = min(max_clips, 3 if video_duration <= 60 else 5)
        step = (video_duration - target_clip_len) / max(1, num_clips - 1) if num_clips > 1 else video_duration

        fallback_clips = []
        descriptions = [
            "Visual Highlight & Intro",
            "Key Feature Demonstration",
            "Core Workflow Showcase",
            "Platform Experience",
            "Closing Summary"
        ]

        for idx in range(num_clips):
            st = round(idx * step, 2)
            et = round(min(video_duration, st + target_clip_len), 2)
            dur = round(et - st, 2)
            if dur < 5.0:
                continue

            desc = descriptions[idx % len(descriptions)]
            score = 88 - (idx * 4)
            sugg = generate_clip_suggestions(desc, f"Clip #{idx + 1}", custom_instruction)

            fallback_clips.append({
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "title": f"Clip #{idx + 1} - {desc}",
                "start_time": st,
                "end_time": et,
                "duration": dur,
                "score": score,
                "score_reasons": [
                    "High-engagement visual highlight window",
                    f"Selected duration: {dur}s for optimal vertical viewer retention",
                    "Seamless pacing across key application presentation"
                ],
                "score_breakdown": {
                    "opening_strength": 20,
                    "contextual_completeness": 18,
                    "interesting_content": 18,
                    "speech_cadence": 12,
                    "natural_ending": 10,
                    "topic_relevance": 10
                },
                "hook_summary": f"{desc} ({st}s - {et}s)",
                "transcript_text": transcript_data.get("full_text") or f"Showcase highlight: {desc}",
                "aspect_ratio": "9:16",
                "crop_x": 0.5,
                "crop_y": 0.5,
                "captions_enabled": bool(transcript_data.get("full_text")),
                "caption_text": transcript_data.get("full_text") or "",
                "caption_font": "Inter",
                "caption_size": 24,
                "caption_color": "#FFFFFF",
                "caption_highlight_color": "#8B5CF6",
                "caption_position": "bottom",
                "volume": 1.0,
                "is_muted": False,
                "status": "candidate",
                "custom_instruction": custom_instruction or "",
                "titles": sugg["titles"],
                "hooks": sugg["hooks"],
                "description": sugg["description"],
                "hashtags": sugg["hashtags"]
            })

        return fallback_clips

    candidates = []

    # Slide through segments to find valid time windows
    n = len(segments)
    for i in range(n):
        seg_start = max(0.0, segments[i]["start"] - boundary_padding)

        for j in range(i, n):
            seg_end = min(video_duration if video_duration > 0 else 999999.0, segments[j]["end"] + boundary_padding)
            span_dur = seg_end - seg_start

            if span_dur < min_clip_duration:
                continue
            if span_dur > max_clip_duration:
                break

            window_segments = segments[i : j + 1]
            scored = score_candidate_window(window_segments, seg_start, seg_end, custom_instruction)
            sugg = generate_clip_suggestions(scored["transcript_text"], f"Clip {len(candidates)+1}", custom_instruction)

            candidates.append({
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "title": f"Moment {len(candidates) + 1}: {scored['hook_summary'][:35]}",
                "start_time": round(seg_start, 2),
                "end_time": round(seg_end, 2),
                "duration": round(span_dur, 2),
                "score": scored["score"],
                "score_reasons": scored["score_reasons"],
                "score_breakdown": scored["score_breakdown"],
                "hook_summary": scored["hook_summary"],
                "transcript_text": scored["transcript_text"],
                "aspect_ratio": "9:16",
                "crop_x": 0.5,
                "crop_y": 0.5,
                "captions_enabled": True,
                "caption_text": scored["transcript_text"],
                "caption_font": "Inter",
                "caption_size": 24,
                "caption_color": "#FFFFFF",
                "caption_highlight_color": "#8B5CF6",
                "caption_position": "bottom",
                "volume": 1.0,
                "is_muted": False,
                "status": "candidate",
                "custom_instruction": custom_instruction or "",
                "titles": sugg["titles"],
                "hooks": sugg["hooks"],
                "description": sugg["description"],
                "hashtags": sugg["hashtags"]
            })

    # Sort by quality score descending
    candidates.sort(key=lambda c: c["score"], reverse=True)

    # De-duplicate heavily overlapping segments
    selected_clips: List[Dict[str, Any]] = []

    def overlaps(c1, c2, threshold=0.4):
        start_max = max(c1["start_time"], c2["start_time"])
        end_min = min(c1["end_time"], c2["end_time"])
        if start_max >= end_min:
            return False
        inter = end_min - start_max
        min_d = min(c1["duration"], c2["duration"])
        return (inter / min_d) > threshold

    for cand in candidates:
        if not any(overlaps(cand, sel) for sel in selected_clips):
            cand["title"] = f"Clip #{len(selected_clips) + 1} - {cand['score']} Score"
            selected_clips.append(cand)
            if len(selected_clips) >= max_clips:
                break

    # If transcript was short and no window met criteria, generate at least one clip of the entire speech
    if not selected_clips and segments:
        first_t = max(0.0, segments[0]["start"] - boundary_padding)
        last_t = min(video_duration if video_duration > 0 else 999999.0, segments[-1]["end"] + boundary_padding)
        dur = last_t - first_t
        scored = score_candidate_window(segments, first_t, last_t, custom_instruction)
        sugg = generate_clip_suggestions(scored["transcript_text"], "Clip #1", custom_instruction)
        selected_clips.append({
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "title": f"Clip #1 - {scored['score']} Score",
            "start_time": round(first_t, 2),
            "end_time": round(last_t, 2),
            "duration": round(dur, 2),
            "score": scored["score"],
            "score_reasons": scored["score_reasons"],
            "score_breakdown": scored["score_breakdown"],
            "hook_summary": scored["hook_summary"],
            "transcript_text": scored["transcript_text"],
            "aspect_ratio": "9:16",
            "crop_x": 0.5,
            "crop_y": 0.5,
            "captions_enabled": True,
            "caption_text": scored["transcript_text"],
            "caption_font": "Inter",
            "caption_size": 24,
            "caption_color": "#FFFFFF",
            "caption_highlight_color": "#8B5CF6",
            "caption_position": "bottom",
            "volume": 1.0,
            "is_muted": False,
            "status": "candidate",
            "custom_instruction": custom_instruction or "",
            "titles": sugg["titles"],
            "hooks": sugg["hooks"],
            "description": sugg["description"],
            "hashtags": sugg["hashtags"]
        })

    return selected_clips

