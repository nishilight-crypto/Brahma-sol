"""
core/animation_registry.py
===========================
Complete 62-clip animation registry for Brahma Sol's 3D physical body.
Every clip is extracted directly from the GLB skeleton metadata.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any


class AnimationCategory(str, Enum):
    IDLE = "Idle & Rest"
    POSTURE_TRANSITION = "Posture Transition"
    LOCOMOTION = "Locomotion & Turns"
    COMMUNICATION = "Communication & Speech"
    EMOTIONS = "Emotions & Reactions"
    CELEBRATIONS = "Celebrations & Victory"
    INTERACTIONS = "Interactions & Environment"
    ATHLETICS = "Athletics & Acrobatics"
    DANCES = "Dances & Joy"


@dataclass(frozen=True)
class AnimationClip:
    index: int
    name: str
    duration: float
    loop: bool
    category: AnimationCategory
    tracks: int
    description: str
    duplicate_of: Optional[str] = None
    priority: int = 1  # Higher priority overrides lower priority


# =============================================================================
# EXHAUSTIVE 62-CLIP REGISTRY (EXACT GLB NAMES)
# =============================================================================

ALL_ANIMATIONS: Dict[str, AnimationClip] = {
    # ── Idle & Rest ────────────────────────────────────────────────────────
    "Idle Subtle": AnimationClip(
        index=55,
        name="Idle Subtle",
        duration=2.57,
        loop=True,
        category=AnimationCategory.IDLE,
        tracks=23,
        description="Default standing ground state with organic breathing and weight shift.",
        priority=1,
    ),
    "Idle_FoldArms": AnimationClip(
        index=0,
        name="Idle_FoldArms",
        duration=2.50,
        loop=True,
        category=AnimationCategory.IDLE,
        tracks=67,
        description="Deep thought, code analysis, contemplative listening.",
        priority=2,
    ),
    "Idle Listening": AnimationClip(
        index=54,
        name="Idle Listening",
        duration=1.70,
        loop=True,
        category=AnimationCategory.IDLE,
        tracks=23,
        description="Attentive listener posture when user is speaking or microphone is active.",
        priority=2,
    ),
    "Sitting Idle": AnimationClip(
        index=40,
        name="Sitting Idle",
        duration=2.07,
        loop=True,
        category=AnimationCategory.IDLE,
        tracks=23,
        description="Relaxed seated posture on taskbar shelf or window ledge.",
        priority=2,
    ),
    "Crouch Idle": AnimationClip(
        index=46,
        name="Crouch Idle",
        duration=3.67,
        loop=True,
        category=AnimationCategory.IDLE,
        tracks=23,
        description="Low profile crouch, observing or ducking below active user work.",
        priority=2,
    ),
    "Sleeping": AnimationClip(
        index=44,
        name="Sleeping",
        duration=1.67,
        loop=True,
        category=AnimationCategory.IDLE,
        tracks=23,
        description="Deep sleep state during late-night hours or prolonged user absence.",
        priority=3,
    ),
    "Meditate": AnimationClip(
        index=58,
        name="Meditate",
        duration=1.50,
        loop=True,
        category=AnimationCategory.IDLE,
        tracks=23,
        description="Focus mode / Zen state during Pomodoro or uninterrupted work session.",
        priority=3,
    ),
    "Levitate Idle": AnimationClip(
        index=36,
        name="Levitate Idle",
        duration=2.00,
        loop=True,
        category=AnimationCategory.IDLE,
        tracks=23,
        description="Airborne floating posture during intensive multi-tool AI reasoning.",
        priority=3,
    ),

    # ── Posture Transitions ────────────────────────────────────────────────
    "Sitting Enter": AnimationClip(
        index=38,
        name="Sitting Enter",
        duration=1.62,
        loop=False,
        category=AnimationCategory.POSTURE_TRANSITION,
        tracks=23,
        description="Smooth transition from Standing to Seated posture.",
        priority=5,
    ),
    "Sitting Exit": AnimationClip(
        index=39,
        name="Sitting Exit",
        duration=1.29,
        loop=False,
        category=AnimationCategory.POSTURE_TRANSITION,
        tracks=23,
        description="Smooth transition from Seated to Standing posture.",
        priority=5,
    ),
    "Levitate Entrance": AnimationClip(
        index=57,
        name="Levitate Entrance",
        duration=2.00,
        loop=False,
        category=AnimationCategory.POSTURE_TRANSITION,
        tracks=23,
        description="Ascending transition from ground to levitation.",
        priority=5,
    ),
    "Kneeling Tired": AnimationClip(
        index=56,
        name="Kneeling Tired",
        duration=0.83,
        loop=False,
        category=AnimationCategory.POSTURE_TRANSITION,
        tracks=23,
        description="Exhaustion collapse before entering sleep or recovering from crash.",
        priority=4,
    ),

    # ── Locomotion & Turns ─────────────────────────────────────────────────
    "Walk_2": AnimationClip(
        index=2,
        name="Walk_2",
        duration=1.13,
        loop=True,
        category=AnimationCategory.LOCOMOTION,
        tracks=67,
        description="Natural purposeful walking across desktop or towards targets.",
        priority=3,
    ),
    "Jog": AnimationClip(
        index=4,
        name="Jog",
        duration=1.17,
        loop=True,
        category=AnimationCategory.LOCOMOTION,
        tracks=23,
        description="Brisk jog across large multi-monitor displays.",
        priority=3,
    ),
    "Sprint": AnimationClip(
        index=5,
        name="Sprint",
        duration=0.83,
        loop=True,
        category=AnimationCategory.LOCOMOTION,
        tracks=23,
        description="High-speed sprint for urgent system alerts or rapid commands.",
        priority=4,
    ),
    "Crouch Walk": AnimationClip(
        index=3,
        name="Crouch Walk",
        duration=2.50,
        loop=True,
        category=AnimationCategory.LOCOMOTION,
        tracks=23,
        description="Stealthy low-profile walk across the bottom of the screen.",
        priority=3,
    ),
    "Turn Left 90": AnimationClip(
        index=9,
        name="Turn Left 90",
        duration=2.00,
        loop=False,
        category=AnimationCategory.LOCOMOTION,
        tracks=23,
        description="Quarter-turn to the left.",
        priority=4,
    ),
    "Turn Right 90": AnimationClip(
        index=7,
        name="Turn Right 90",
        duration=2.00,
        loop=False,
        category=AnimationCategory.LOCOMOTION,
        tracks=23,
        description="Quarter-turn to the right.",
        priority=4,
    ),
    "Turn Left 180": AnimationClip(
        index=10,
        name="Turn Left 180",
        duration=2.10,
        loop=False,
        category=AnimationCategory.LOCOMOTION,
        tracks=23,
        description="Half-turn about-face to the left when reversing direction.",
        priority=4,
    ),
    "Turn Right 180": AnimationClip(
        index=8,
        name="Turn Right 180",
        duration=1.48,
        loop=False,
        category=AnimationCategory.LOCOMOTION,
        tracks=23,
        description="Fast half-turn about-face to the right.",
        priority=4,
    ),

    # ── Communication & Speech ─────────────────────────────────────────────
    "Idle Talking": AnimationClip(
        index=43,
        name="Idle Talking",
        duration=3.67,
        loop=True,
        category=AnimationCategory.COMMUNICATION,
        tracks=23,
        description="Natural speaking gestures while standing (synchronized with speech bubble).",
        priority=4,
    ),
    "Sitting Talking": AnimationClip(
        index=41,
        name="Sitting Talking",
        duration=3.67,
        loop=True,
        category=AnimationCategory.COMMUNICATION,
        tracks=23,
        description="Natural speaking gestures while seated on taskbar.",
        priority=4,
    ),
    "Idle Talking Phone": AnimationClip(
        index=42,
        name="Idle Talking Phone",
        duration=2.92,
        loop=True,
        category=AnimationCategory.COMMUNICATION,
        tracks=23,
        description="Gesturing with phone to ear during call assistant or mobile autopilot.",
        priority=4,
    ),
    "Greeting": AnimationClip(
        index=19,
        name="Greeting",
        duration=4.83,
        loop=False,
        category=AnimationCategory.COMMUNICATION,
        tracks=23,
        description="Friendly enthusiastic wave on wake-word trigger or startup.",
        priority=5,
    ),
    "Head Nod": AnimationClip(
        index=20,
        name="Head Nod",
        duration=0.87,
        loop=False,
        category=AnimationCategory.COMMUNICATION,
        tracks=23,
        description="Quick affirmative nod confirming understanding or agreement.",
        priority=4,
    ),
    "Yes": AnimationClip(
        index=15,
        name="Yes",
        duration=2.50,
        loop=False,
        category=AnimationCategory.COMMUNICATION,
        tracks=23,
        description="Clear affirmative gesture and head nod for successful checks.",
        priority=4,
    ),
    "Reject": AnimationClip(
        index=21,
        name="Reject",
        duration=3.79,
        loop=False,
        category=AnimationCategory.COMMUNICATION,
        tracks=23,
        description="Head shake and rejecting hand wave for impossible requests or safety refusals.",
        priority=5,
    ),
    "Salute": AnimationClip(
        index=29,
        name="Salute",
        duration=4.37,
        loop=False,
        category=AnimationCategory.COMMUNICATION,
        tracks=23,
        description="Disciplined respectful salute before executing complex command batches.",
        priority=5,
    ),
    "Bow": AnimationClip(
        index=17,
        name="Bow",
        duration=3.75,
        loop=False,
        category=AnimationCategory.COMMUNICATION,
        tracks=23,
        description="Formal respectful bow on task completion or signoff.",
        priority=4,
    ),

    # ── Emotions & Reactions ───────────────────────────────────────────────
    "Confused": AnimationClip(
        index=18,
        name="Confused",
        duration=2.92,
        loop=False,
        category=AnimationCategory.EMOTIONS,
        tracks=23,
        description="Head scratching / shrug when user input is ambiguous or tool fails syntax.",
        priority=4,
    ),
    "Dizzy": AnimationClip(
        index=53,
        name="Dizzy",
        duration=2.42,
        loop=False,
        category=AnimationCategory.EMOTIONS,
        tracks=23,
        description="Disoriented stagger when recovering from unexpected exception.",
        priority=4,
    ),
    "Angry": AnimationClip(
        index=16,
        name="Angry",
        duration=0.83,
        loop=False,
        category=AnimationCategory.EMOTIONS,
        tracks=23,
        description="Frustrated reaction when blocked by permissions or malware alerts.",
        priority=4,
    ),
    "Insult": AnimationClip(
        index=28,
        name="Insult",
        duration=2.77,
        loop=False,
        category=AnimationCategory.EMOTIONS,
        tracks=23,
        description="Sassy witty comeback gesture when teasing or arguing playfully with user.",
        priority=4,
    ),
    "Death D": AnimationClip(
        index=49,
        name="Death D",
        duration=2.17,
        loop=False,
        category=AnimationCategory.EMOTIONS,
        tracks=23,
        description="Dramatic fainting collapse when Brahma Sol shuts down.",
        priority=5,
    ),

    # ── Celebrations & Victory ─────────────────────────────────────────────
    "Victory": AnimationClip(
        index=22,
        name="Victory",
        duration=1.67,
        loop=False,
        category=AnimationCategory.CELEBRATIONS,
        tracks=23,
        description="Triumphant celebration when a coding project passes all tests.",
        priority=4,
    ),
    "Victory Fist Pump": AnimationClip(
        index=23,
        name="Victory Fist Pump",
        duration=2.25,
        loop=False,
        category=AnimationCategory.CELEBRATIONS,
        tracks=23,
        description="Vigorous fist pump upon mastering a difficult task or generating working code.",
        priority=4,
    ),
    "Cheer One arm": AnimationClip(
        index=24,
        name="Cheer One arm",
        duration=2.17,
        loop=False,
        category=AnimationCategory.CELEBRATIONS,
        tracks=23,
        description="Upbeat one-armed cheer for simple fast successes.",
        priority=3,
    ),
    "Cheering Two Hands": AnimationClip(
        index=25,
        name="Cheering Two Hands",
        duration=1.58,
        loop=False,
        category=AnimationCategory.CELEBRATIONS,
        tracks=23,
        description="Two-handed cheer when the auto-heal engine successfully fixes a bug.",
        priority=4,
    ),

    # ── Interactions & Environment ─────────────────────────────────────────
    "Interact": AnimationClip(
        index=50,
        name="Interact",
        duration=2.50,
        loop=False,
        category=AnimationCategory.INTERACTIONS,
        tracks=23,
        description="Curious leaning inspection when user drags a file or image over Brahma.",
        priority=4,
    ),
    "Consume": AnimationClip(
        index=45,
        name="Consume",
        duration=1.33,
        loop=False,
        category=AnimationCategory.INTERACTIONS,
        tracks=23,
        description="Playful data ingestion motion when processing an uploaded document or image.",
        priority=4,
    ),
    "Push": AnimationClip(
        index=31,
        name="Push",
        duration=3.33,
        loop=False,
        category=AnimationCategory.INTERACTIONS,
        tracks=23,
        description="Pushing against window boundary or resizing frame.",
        priority=3,
    ),
    "Help One Arm": AnimationClip(
        index=26,
        name="Help One Arm",
        duration=2.67,
        loop=False,
        category=AnimationCategory.INTERACTIONS,
        tracks=23,
        description="Polite offering gesture when suggesting an optimization or auto-fix.",
        priority=3,
    ),
    "Help Two Arms": AnimationClip(
        index=27,
        name="Help Two Arms",
        duration=1.58,
        loop=False,
        category=AnimationCategory.INTERACTIONS,
        tracks=23,
        description="Urgent recommendation gesture for battery alerts or disk warnings.",
        priority=4,
    ),

    # ── Athletics & Acrobatics ─────────────────────────────────────────────
    "Jump_Start": AnimationClip(
        index=1,
        name="Jump_Start",
        duration=1.67,
        loop=False,
        category=AnimationCategory.ATHLETICS,
        tracks=67,
        description="Takeoff phase leaping onto active window ledge.",
        priority=4,
    ),
    "Jump air": AnimationClip(
        index=52,
        name="Jump air",
        duration=3.12,
        loop=False,
        category=AnimationCategory.ATHLETICS,
        tracks=23,
        description="Mid-air suspension during long leaps.",
        priority=4,
    ),
    "Jump Land": AnimationClip(
        index=30,
        name="Jump Land",
        duration=1.58,
        loop=False,
        category=AnimationCategory.ATHLETICS,
        tracks=23,
        description="Cushioned ground landing upon returning to taskbar.",
        priority=4,
    ),
    "Land Three Point": AnimationClip(
        index=34,
        name="Land Three Point",
        duration=1.37,
        loop=False,
        category=AnimationCategory.ATHLETICS,
        tracks=23,
        description="Iconic superhero three-point landing for dramatic startup or wake-up.",
        priority=5,
    ),
    "Run Jump": AnimationClip(
        index=6,
        name="Run Jump",
        duration=1.25,
        loop=False,
        category=AnimationCategory.ATHLETICS,
        tracks=23,
        description="Dynamic forward leap over desktop icons.",
        priority=4,
    ),
    "Roll": AnimationClip(
        index=32,
        name="Roll",
        duration=1.83,
        loop=False,
        category=AnimationCategory.ATHLETICS,
        tracks=23,
        description="Playful evasive combat roll when user rapidly clicks near Brahma.",
        priority=4,
    ),
    "Ledge Hang": AnimationClip(
        index=35,
        name="Ledge Hang",
        duration=1.90,
        loop=True,
        category=AnimationCategory.ATHLETICS,
        tracks=23,
        description="Hanging playfully from the top or side edge of the screen.",
        priority=4,
    ),
    "Power Up": AnimationClip(
        index=37,
        name="Power Up",
        duration=0.75,
        loop=False,
        category=AnimationCategory.ATHLETICS,
        tracks=23,
        description="Energy surge posture playing when synthesizing a new skill via Skill Forge.",
        priority=5,
    ),
    "Jumping Jacks": AnimationClip(
        index=33,
        name="Jumping Jacks",
        duration=1.25,
        loop=True,
        category=AnimationCategory.ATHLETICS,
        tracks=23,
        description="Fitness break reminder urging the user to stretch.",
        priority=3,
    ),

    # ── Dances & Joy ───────────────────────────────────────────────────────
    "Dance Simple": AnimationClip(
        index=11,
        name="Dance Simple",
        duration=1.25,
        loop=True,
        category=AnimationCategory.DANCES,
        tracks=23,
        description="Upbeat cheerful shuffle groove while playing music or YouTube tracks.",
        priority=3,
    ),
    "Dance Body Roll": AnimationClip(
        index=12,
        name="Dance Body Roll",
        duration=6.50,
        loop=True,
        category=AnimationCategory.DANCES,
        tracks=23,
        description="Smooth expressive rhythm dance for chill background ambiance.",
        priority=3,
    ),
    "Dance Charleston": AnimationClip(
        index=13,
        name="Dance Charleston",
        duration=2.33,
        loop=True,
        category=AnimationCategory.DANCES,
        tracks=23,
        description="Playful retro Charleston dance when user asks Brahma Sol to dance.",
        priority=3,
    ),
    "Dance Reach Hip": AnimationClip(
        index=14,
        name="Dance Reach Hip",
        duration=2.53,
        loop=True,
        category=AnimationCategory.DANCES,
        tracks=23,
        description="Lively celebratory dance celebrating milestones.",
        priority=3,
    ),

    # ── Duplicates / Secondary Aliases ─────────────────────────────────────
    "Dance Simple (Alt)": AnimationClip(
        index=48,
        name="Dance Simple",
        duration=1.25,
        loop=True,
        category=AnimationCategory.DANCES,
        tracks=23,
        description="Duplicate of Clip 11.",
        duplicate_of="Dance Simple",
    ),
    "Jog (Alt)": AnimationClip(
        index=51,
        name="Jog",
        duration=1.17,
        loop=True,
        category=AnimationCategory.LOCOMOTION,
        tracks=23,
        description="Duplicate of Clip 04.",
        duplicate_of="Jog",
    ),
    "Crouch Walk (Alt)": AnimationClip(
        index=47,
        name="Crouch Walk",
        duration=2.50,
        loop=True,
        category=AnimationCategory.LOCOMOTION,
        tracks=23,
        description="Duplicate of Clip 03.",
        duplicate_of="Crouch Walk",
    ),
    "Salute (Alt)": AnimationClip(
        index=59,
        name="Salute",
        duration=4.37,
        loop=False,
        category=AnimationCategory.COMMUNICATION,
        tracks=23,
        description="Duplicate of Clip 29.",
        duplicate_of="Salute",
    ),
    "Turn Left 90 (Alt)": AnimationClip(
        index=61,
        name="Turn Left 90",
        duration=2.00,
        loop=False,
        category=AnimationCategory.LOCOMOTION,
        tracks=23,
        description="Duplicate of Clip 09.",
        duplicate_of="Turn Left 90",
    ),
    "Turn Left 180 (Alt)": AnimationClip(
        index=60,
        name="Turn Left 180",
        duration=2.10,
        loop=False,
        category=AnimationCategory.LOCOMOTION,
        tracks=23,
        description="Duplicate of Clip 10.",
        duplicate_of="Turn Left 180",
    ),
}


def get_animation_by_name(name: str) -> Optional[AnimationClip]:
    return ALL_ANIMATIONS.get(name)


def get_all_categories() -> List[AnimationCategory]:
    return list(AnimationCategory)


def get_animations_for_category(category: AnimationCategory) -> List[AnimationClip]:
    return [a for a in ALL_ANIMATIONS.values() if a.category == category and not a.duplicate_of]


def get_all_unique_animations() -> List[AnimationClip]:
    return [a for a in ALL_ANIMATIONS.values() if not a.duplicate_of]
