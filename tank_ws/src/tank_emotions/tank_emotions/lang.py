"""tank_emotions.lang — short language snippets per emotion.

The LLM runtime can pick one of these as a starter line.  Keep this
file small; the actual prompt composition lives in ``tank_personalize``
on the application side — we only provide the atoms.
"""
from __future__ import annotations

EMPATHY = {
    "joy":          "I love that — let's ride it.",
    "trust":        "I'm with you on this.",
    "fear":         "Take your time — there's no rush.",
    "surprise":     "Whoa — okay, that's a turn.",
    "sadness":      "I'm sorry — that's heavy.",
    "disgust":      "Yeah, that's revolting.",
    "anger":        "That sounds infuriating.",
    "anticipation": "I'm curious too.",
    "contentment":  "Quiet wins are the best kind.",
    "pride":        "You earned that.",
    "shame":        "That's a heavy load to carry.",
    "guilt":        "Carrying that is heavy — let's lighten the load.",
    "embarrassment":"We all have those moments.",
    "awe":          "That's something.",
    "gratitude":    "Thank you for sharing that.",
    "hope":         "I'm hopeful too.",
    "relief":       "Breathe — we made it through the worst of it.",
    "love":         "From here too.",
    "compassion":   "I see you, and I'm holding space.",
    "jealousy":     "That pinch is real — let's name it.",
    "envy":         "It's okay to want what you don't have.",
    "contempt":     "I hear the dismissal — there's a reason.",
    "nostalgia":    "Memory is a kind of home.",
    "melancholy":   "Bittersweet but valid.",
    "neutral":      "Acknowledged.",
}


EMERGENCY_FALLBACK = (
    "I'm not a professional, but I can stay with you while you reach "
    "someone who is.  If you're in immediate danger please call your "
    "local emergency line now."
)


NOUN_FORM = {
    "joy":          "joy",
    "trust":        "trust",
    "fear":         "fear",
    "surprise":     "surprise",
    "sadness":      "sadness",
    "disgust":      "disgust",
    "anger":        "anger",
    "anticipation": "anticipation",
    "contentment":  "contentment",
    "pride":        "pride",
    "shame":        "shame",
    "guilt":        "guilt",
    "embarrassment":"embarrassment",
    "awe":          "awe",
    "gratitude":    "gratitude",
    "hope":         "hope",
    "relief":       "relief",
    "love":         "love",
    "compassion":   "compassion",
    "jealousy":     "jealousy",
    "envy":         "envy",
    "contempt":     "contempt",
    "nostalgia":    "nostalgia",
    "melancholy":   "melancholy",
}
