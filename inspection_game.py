#!/usr/bin/env python3
"""
One More Run - Enhanced Edition

A zero-sum repeated game with conversational elements, collusion opportunities,
and bait tactics. Teaches mixed strategies, signaling, and trust dynamics.

Players: Smuggler (human) vs Inspector (AI)

Optional: LLM-powered dynamic dialogue via OpenAI or Anthropic API.
"""

import random
import sys
import time
import os
import json
from urllib import request, error
from typing import Optional, Dict, Any

# =============================================================================
# GAME CONFIGURATION
# =============================================================================

ROUNDS_PER_GAME = 20
EARLY_GAME_END = 6
MID_GAME_END = 14

# Timing
DELAY_PRINT = 0.02
DELAY_SHORT = 0.4
DELAY_MEDIUM = 0.8
DELAY_LONG = 1.2

# Base Payoffs (Smuggler Perspective)
PAYOFF_SMUGGLE_INSPECT = -5
PAYOFF_SMUGGLE_DONT = 10
PAYOFF_LAYLOW_INSPECT = 0
PAYOFF_LAYLOW_DONT = 1

# Collusion/Bribe costs
BRIBE_COST = 3
BRIBE_INSPECTOR_CUT = 2  # What inspector "gains" from accepting

# Actions
ACT_SMUGGLE = 1
ACT_LAY_LOW = 2
ACT_BRIBE = 3
ACT_SIGNAL_TRUCE = 4

ACT_INSPECT = 1
ACT_DONT_INSPECT = 2
ACT_ACCEPT_BRIBE = 3
ACT_SET_TRAP = 4  # Pretend to accept, then inspect anyway

# Action strings
ACTION_NAMES = {
    ACT_SMUGGLE: "Smuggle",
    ACT_LAY_LOW: "Lay Low",
    ACT_BRIBE: "Offer Bribe",
    ACT_SIGNAL_TRUCE: "Signal Truce",
    ACT_INSPECT: "Inspect",
    ACT_DONT_INSPECT: "Don't Inspect",
    ACT_ACCEPT_BRIBE: "Accept Bribe",
    ACT_SET_TRAP: "Set Trap",
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def type_print(text, speed=DELAY_PRINT, end='\n'):
    """Print with typewriter effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        if speed > 0:
            time.sleep(speed)
    sys.stdout.write(end)
    sys.stdout.flush()


def slow_print(text, delay=DELAY_SHORT):
    """Print then pause."""
    print(text)
    time.sleep(delay)


# =============================================================================
# LLM-POWERED DIALOGUE (OPTIONAL)
# =============================================================================

class LLMDialogueGenerator:
    """
    Generates dynamic Inspector dialogue using OpenAI or Anthropic API.
    Falls back to static dialogue if API fails.
    """

    SYSTEM_PROMPT = """You are the INSPECTOR in a game called "The Inspection Game."

Your personality:
- You are a cunning, experienced customs inspector
- You enjoy psychological warfare and mind games
- You can be threatening, luring, sarcastic, or friendly - whatever serves your goals
- You sometimes lie or set traps to catch the smuggler
- You adapt your tone based on how the game is going

Your traits this game (0-1 scale):
- Greed: {greed:.2f} (higher = more likely to accept bribes)
- Deceptiveness: {deceptiveness:.2f} (higher = more likely to set traps/lie)
- Adaptiveness: {adaptiveness:.2f} (higher = faster pattern recognition)

RULES:
- Keep responses to 1-2 SHORT sentences max
- Be in character - you ARE the inspector, speak directly to the smuggler
- Never break character or mention you're an AI
- Never reveal your actual strategy or next move
- You can bluff, threaten, taunt, or try to build false trust
- Vary your tone - don't be repetitive"""

    def __init__(self, api_provider: str, api_key: str, inspector_traits: Dict[str, float]):
        self.api_provider = api_provider.lower()  # "openai" or "anthropic"
        self.api_key = api_key
        self.traits = inspector_traits
        self.conversation_history = []
        self.enabled = True

    def _build_context(self, game_state: Dict[str, Any]) -> str:
        """Build context string for the LLM."""
        context = f"""
CURRENT GAME STATE:
- Round: {game_state.get('round_num', 1)} / {ROUNDS_PER_GAME}
- Smuggler's Score: {game_state.get('score', 0):+d}
- Trust Level: {game_state.get('trust_level', 0.5):.0%}
- Smuggler's smuggle rate: {game_state.get('smuggle_freq', 0.3):.0%}
- Your mood: {game_state.get('mood', 'neutral')}

RECENT HISTORY:
{game_state.get('recent_history', 'Game just started.')}

SITUATION: {game_state.get('situation', 'Pre-round comment')}
"""
        return context

    def _call_openai(self, messages: list) -> Optional[str]:
        """Call OpenAI API."""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            data = {
                "model": "gpt-4o-mini",
                "messages": messages,
                "max_tokens": 100,
                "temperature": 0.9
            }
            req = request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"[API Error: {e}]")
            return None

    def _call_anthropic(self, messages: list, system: str) -> Optional[str]:
        """Call Anthropic API."""
        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            # Convert from OpenAI format to Anthropic format
            anthropic_messages = []
            for msg in messages:
                if msg['role'] != 'system':
                    anthropic_messages.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })

            data = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 100,
                "system": system,
                "messages": anthropic_messages
            }
            req = request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['content'][0]['text'].strip()
        except Exception as e:
            print(f"[API Error: {e}]")
            return None

    def generate(self, game_state: Dict[str, Any], prompt: str) -> Optional[str]:
        """Generate dialogue using the configured LLM."""
        if not self.enabled:
            return None

        system = self.SYSTEM_PROMPT.format(**self.traits)
        context = self._build_context(game_state)

        user_message = f"{context}\n\nGenerate your response for: {prompt}"

        if self.api_provider == "openai":
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message}
            ]
            return self._call_openai(messages)
        else:  # anthropic
            messages = [
                {"role": "user", "content": user_message}
            ]
            return self._call_anthropic(messages, system)

    def get_pre_round_comment(self, game_state: Dict[str, Any]) -> Optional[str]:
        """Generate pre-round taunt/comment."""
        game_state['situation'] = "You're about to inspect. Say something to the smuggler before they choose their action. You might threaten, lure, or play mind games."
        return self.generate(game_state, "Pre-round comment to unsettle or mislead the smuggler")

    def get_outcome_comment(self, game_state: Dict[str, Any], outcome: str) -> Optional[str]:
        """Generate reaction to round outcome."""
        game_state['situation'] = f"Round just ended. Outcome: {outcome}"
        return self.generate(game_state, f"React to this outcome: {outcome}")

    def get_bribe_response(self, game_state: Dict[str, Any], accepted: bool, will_honor: bool) -> Optional[str]:
        """Generate response to bribe offer."""
        if accepted:
            if will_honor:
                situation = "The smuggler offered a bribe. You're accepting it AND will honor the deal."
            else:
                situation = "The smuggler offered a bribe. You're accepting their money but plan to BETRAY them and inspect anyway. Be convincing."
        else:
            situation = "The smuggler offered a bribe. You're refusing it."

        game_state['situation'] = situation
        return self.generate(game_state, "Respond to the bribe offer")

    def get_truce_response(self, game_state: Dict[str, Any], trust_high: bool) -> Optional[str]:
        """Generate response to truce signal."""
        if trust_high:
            situation = "The smuggler is signaling they want a truce. Trust is high - you might cooperate."
        else:
            situation = "The smuggler is signaling they want a truce. Trust is low - you're skeptical."

        game_state['situation'] = situation
        return self.generate(game_state, "Respond to their truce signal")

    def get_trap_reveal(self, game_state: Dict[str, Any]) -> Optional[str]:
        """Generate taunt when trap is sprung."""
        game_state['situation'] = "You just sprung a TRAP on the smuggler! They fell for your deception. Gloat!"
        return self.generate(game_state, "Taunt them for falling into your trap")


# =============================================================================
# INSPECTOR PERSONALITY & DIALOGUE
# =============================================================================

class InspectorPersonality:
    """
    Generates contextual dialogue for the Inspector.
    Adds psychological warfare and misdirection.

    Can optionally use LLM for dynamic dialogue generation.
    """

    def __init__(self, rng, llm_generator: Optional[LLMDialogueGenerator] = None):
        self.rng = rng
        self.llm = llm_generator
        self.honesty_streak = 0
        self.betrayal_count = 0
        self.mood = "neutral"

        # Game state cache for LLM context
        self._game_state_cache: Dict[str, Any] = {}

    def update_game_state(self, **kwargs):
        """Update cached game state for LLM context."""
        self._game_state_cache.update(kwargs)

    def _get_llm_game_state(self) -> Dict[str, Any]:
        """Get current game state for LLM."""
        state = self._game_state_cache.copy()
        state['mood'] = self.mood
        return state

    GREETINGS = [
        "Another day, another inspection.",
        "I've got my eye on you today.",
        "Let's see what you're up to.",
        "Ready when you are.",
        "Don't try anything clever.",
    ]

    THREATS = [
        "I'm watching your every move.",
        "Try smuggling. I dare you.",
        "My instincts are sharp today.",
        "I have a feeling about this round...",
        "You seem nervous. Something to hide?",
    ]

    LURES = [
        "I might take it easy this round.",
        "Even inspectors need a break sometimes.",
        "I'm feeling generous today.",
        "The coast looks clear from here.",
        "I've got other things on my mind.",
    ]

    CAUGHT_REACTIONS = [
        "Gotcha! Should've played it safe.",
        "Too predictable. I saw that coming.",
        "The house always wins.",
        "Did you really think I'd miss that?",
        "Another one bites the dust.",
    ]

    MISSED_REACTIONS = [
        "Hmm. Lucky this time.",
        "I'll get you next round.",
        "Enjoy it while it lasts.",
        "That won't happen again.",
        "You're craftier than I thought.",
    ]

    WASTED_INSPECTION = [
        "Playing it safe, huh? Smart.",
        "I wasted my time on you.",
        "Cautious. I respect that.",
        "Nothing to see here, apparently.",
        "You're harder to read than I thought.",
    ]

    MUTUAL_PASSIVE = [
        "Quiet round. Too quiet.",
        "We're both being careful.",
        "A gentleman's agreement, then?",
        "Neither of us blinked.",
        "Interesting strategy.",
    ]

    BRIBE_CONSIDER = [
        "A bribe? How... tempting.",
        "You think you can buy me?",
        "Money talks, I suppose.",
        "That's an interesting offer.",
        "Corruption has its price.",
    ]

    TRUCE_RESPONSE = [
        "A truce? In this economy?",
        "You want to cooperate? Curious.",
        "Trust is a dangerous game.",
        "Maybe we can work something out.",
        "Actions speak louder than signals.",
    ]

    BETRAYAL = [
        "Did you really trust an inspector?",
        "Business is business.",
        "Sorry, but I have quotas to meet.",
        "That was a mistake.",
        "Never trust a badge.",
    ]

    def set_mood(self, mood):
        self.mood = mood

    def get_greeting(self, round_num):
        if round_num == 1:
            return self.rng.choice(self.GREETINGS)
        return None

    def get_pre_round_comment(self, round_num, player_smuggle_freq, last_player_action):
        """Generate comment before player chooses."""
        # Try LLM first if available
        if self.llm:
            self.update_game_state(
                round_num=round_num,
                smuggle_freq=player_smuggle_freq,
            )
            llm_response = self.llm.get_pre_round_comment(self._get_llm_game_state())
            if llm_response:
                return llm_response

        # Fallback to static dialogue
        if self.mood == "aggressive":
            return self.rng.choice(self.THREATS)
        elif self.mood == "friendly" or self.mood == "deceptive":
            return self.rng.choice(self.LURES)

        if player_smuggle_freq > 0.5:
            return self.rng.choice(self.THREATS + ["Your luck will run out."])
        elif player_smuggle_freq < 0.2 and round_num > 5:
            return self.rng.choice(self.LURES + ["Playing too safe loses points too."])

        if self.rng.random() < 0.4:
            return self.rng.choice(self.THREATS + self.LURES)
        return None

    def get_outcome_comment(self, player_action, inspector_action, was_trap):
        """Generate comment after round resolves."""
        # Try LLM first if available
        if self.llm:
            if was_trap:
                llm_response = self.llm.get_trap_reveal(self._get_llm_game_state())
                if llm_response:
                    return llm_response

            # Build outcome description
            p_str = ACTION_NAMES.get(player_action, "unknown")
            i_str = ACTION_NAMES.get(inspector_action, "unknown")
            outcome = f"Smuggler chose {p_str}, Inspector chose {i_str}."
            if player_action == ACT_SMUGGLE and inspector_action == ACT_INSPECT:
                outcome += " Smuggler was CAUGHT!"
            elif player_action == ACT_SMUGGLE and inspector_action == ACT_DONT_INSPECT:
                outcome += " Smuggler got away with it!"
            elif player_action == ACT_LAY_LOW and inspector_action == ACT_INSPECT:
                outcome += " Inspector wasted the inspection."
            else:
                outcome += " Quiet round."

            llm_response = self.llm.get_outcome_comment(self._get_llm_game_state(), outcome)
            if llm_response:
                return llm_response

        # Fallback to static dialogue
        if was_trap:
            return self.rng.choice(self.BETRAYAL)

        if player_action == ACT_SMUGGLE:
            if inspector_action == ACT_INSPECT:
                return self.rng.choice(self.CAUGHT_REACTIONS)
            else:
                return self.rng.choice(self.MISSED_REACTIONS)
        elif player_action == ACT_LAY_LOW:
            if inspector_action == ACT_INSPECT:
                return self.rng.choice(self.WASTED_INSPECTION)
            else:
                return self.rng.choice(self.MUTUAL_PASSIVE)
        elif player_action == ACT_BRIBE:
            return self.rng.choice(self.BRIBE_CONSIDER)
        elif player_action == ACT_SIGNAL_TRUCE:
            return self.rng.choice(self.TRUCE_RESPONSE)

        return None

    def get_bribe_response(self, accepted: bool, will_honor: bool) -> str:
        """Generate response to bribe offer."""
        if self.llm:
            llm_response = self.llm.get_bribe_response(
                self._get_llm_game_state(), accepted, will_honor
            )
            if llm_response:
                return llm_response

        # Fallback
        if accepted:
            return "Deal. You've bought yourself a pass." if will_honor else "Deal. I'll look the other way."
        else:
            return "I can't be bought. Not today."

    def get_truce_response(self, trust_high: bool) -> str:
        """Generate response to truce signal."""
        if self.llm:
            llm_response = self.llm.get_truce_response(self._get_llm_game_state(), trust_high)
            if llm_response:
                return llm_response

        # Fallback
        if trust_high:
            return "Noted. Maybe we can work together."
        else:
            return "Trust is earned, not given."

    def record_honesty(self, kept_word):
        if kept_word:
            self.honesty_streak += 1
        else:
            self.honesty_streak = 0
            self.betrayal_count += 1


# =============================================================================
# INSPECTOR AI - ENHANCED WITH COLLUSION/BAIT LOGIC
# =============================================================================

class InspectorAI:
    """
    Enhanced Inspector with:
    - Standard game theory phases
    - Bait/trap setting
    - Bribe acceptance/rejection
    - Collusion opportunities
    - Trust dynamics
    - Optional LLM-powered dialogue
    """

    def __init__(self, seed=None, llm_generator: Optional[LLMDialogueGenerator] = None):
        self.rng = random.Random(seed)
        self.llm = llm_generator
        self.personality = InspectorPersonality(self.rng, llm_generator)

        # History tracking
        self.history_smuggler = []
        self.history_inspector = []
        self.history_bribes_offered = 0
        self.history_bribes_accepted = 0
        self.history_truces_signaled = 0
        self.history_traps_set = 0
        self.history_traps_sprung = 0  # Successful traps

        # Trust/cooperation state
        self.trust_level = 0.5  # 0 = hostile, 1 = cooperative
        self.pending_deal = None  # Track if a deal was made (deprecated for immunity)
        self.immunity_turns = 0 # How many turns we are safe
        self.consecutive_passive_rounds = 0

        # Personality traits (randomized per game)
        self.greed = self.rng.uniform(0.3, 0.7)  # Likelihood to accept bribes
        self.deceptiveness = self.rng.uniform(0.2, 0.6)  # Likelihood to set traps
        self.adaptiveness = self.rng.uniform(0.4, 0.8)  # How quickly they adjust

        # Update LLM generator with traits if present
        if self.llm:
            self.llm.traits = {
                'greed': self.greed,
                'deceptiveness': self.deceptiveness,
                'adaptiveness': self.adaptiveness
            }

    def get_smuggle_frequency(self):
        if not self.history_smuggler:
            return 0.3
        smuggle_count = sum(1 for a in self.history_smuggler if a == ACT_SMUGGLE)
        return smuggle_count / len(self.history_smuggler)

    def get_cooperation_frequency(self):
        """How often player has been 'cooperative' (lay low or truce)."""
        if not self.history_smuggler:
            return 0.5
        coop_actions = [ACT_LAY_LOW, ACT_SIGNAL_TRUCE, ACT_BRIBE]
        coop_count = sum(1 for a in self.history_smuggler if a in coop_actions)
        return coop_count / len(self.history_smuggler)

    def decide(self, round_num, player_score, last_player_action=None):
        """
        Main decision function. Returns (action, is_bait, announced_intent).

        is_bait: True if inspector is setting a trap
        announced_intent: What inspector "says" they'll do (may be lie)
        """
        # Handle active immunity
        if self.immunity_turns > 0:
            self.immunity_turns -= 1
            # Check for betrayal trap?
            if self.pending_deal == "trap": # Trap context logic
                 # Trap trigger logic
                 pass 
            
            # Simple immunity logic
            return ACT_DONT_INSPECT, False, "I'm looking the other way."

        # Handle pending deals from old logic (migration safety)
        if self.pending_deal == "accepted":
            self.pending_deal = None
            # Might honor the deal... or not
            if self.rng.random() > self.deceptiveness:
                self.personality.record_honesty(True)
                return ACT_DONT_INSPECT, False, "I'll keep my word."
            else:
                # TRAP!
                self.personality.record_honesty(False)
                self.history_traps_set += 1
                return ACT_INSPECT, True, "A deal's a deal... or is it?"

        smuggle_freq = self.get_smuggle_frequency()
        coop_freq = self.get_cooperation_frequency()

        # Update trust based on player behavior
        self._update_trust(last_player_action)

        # Set mood for dialogue
        self._set_mood(round_num, smuggle_freq)

        # Phase-based decision making
        if round_num <= EARLY_GAME_END:
            return self._early_game_decision(round_num)
        elif round_num <= MID_GAME_END:
            return self._mid_game_decision(round_num, smuggle_freq, coop_freq)
        else:
            return self._late_game_decision(round_num, smuggle_freq, coop_freq)

    def _update_trust(self, last_player_action):
        """Update trust level based on player's last action."""
        if last_player_action is None:
            return

        if last_player_action == ACT_SMUGGLE:
            self.trust_level = max(0, self.trust_level - 0.1)
            self.consecutive_passive_rounds = 0
        elif last_player_action in [ACT_LAY_LOW, ACT_SIGNAL_TRUCE]:
            self.trust_level = min(1, self.trust_level + 0.05)
            self.consecutive_passive_rounds += 1
        elif last_player_action == ACT_BRIBE:
            self.trust_level = min(1, self.trust_level + 0.02)
            self.consecutive_passive_rounds = 0

    def _set_mood(self, round_num, smuggle_freq):
        """Set inspector mood for dialogue generation."""
        if smuggle_freq > 0.5:
            self.personality.set_mood("aggressive")
        elif self.trust_level > 0.7:
            # Might be friendly... or setting up a trap
            if self.rng.random() < self.deceptiveness:
                self.personality.set_mood("deceptive")
            else:
                self.personality.set_mood("friendly")
        else:
            self.personality.set_mood("neutral")

    def _early_game_decision(self, round_num):
        """Early game: Establish baseline, mostly Nash-like randomization."""
        # ~60% inspection rate with noise
        base_prob = 0.6 + self.rng.uniform(-0.1, 0.1)

        # Occasional bait in early game to test player
        if round_num >= 4 and self.rng.random() < 0.15:
            # Set a trap: announce leniency, then inspect
            return ACT_INSPECT, True, "I might go easy on you..."

        if self.rng.random() < base_prob:
            return ACT_INSPECT, False, None
        return ACT_DONT_INSPECT, False, None

    def _mid_game_decision(self, round_num, smuggle_freq, coop_freq):
        """Mid game: Adapt to player patterns, introduce collusion dynamics."""

        # Check for collusion opportunity
        if self.trust_level > 0.65 and self.consecutive_passive_rounds >= 2:
            # Player seems cooperative - maybe reciprocate (or exploit!)
            if self.rng.random() < self.trust_level - 0.3:
                return ACT_DONT_INSPECT, False, "Let's keep this arrangement going."
            elif self.rng.random() < self.deceptiveness:
                # Betray the implicit trust
                self.history_traps_set += 1
                return ACT_INSPECT, True, "I appreciate the cooperation..."

        # Standard adaptive play
        if smuggle_freq > 0.45:
            inspect_prob = 0.75 + self.adaptiveness * 0.1
        elif smuggle_freq < 0.2:
            inspect_prob = 0.35 - self.adaptiveness * 0.1
        else:
            inspect_prob = 0.55

        # Add bait possibility
        if self.rng.random() < self.deceptiveness * 0.4:
            if self.rng.random() < 0.5:
                # Bait: say relaxing, actually inspect
                return ACT_INSPECT, True, "Taking it easy this round."
            else:
                # Reverse bait: say aggressive, don't inspect
                return ACT_DONT_INSPECT, False, "You're definitely getting caught."

        if self.rng.random() < inspect_prob:
            return ACT_INSPECT, False, None
        return ACT_DONT_INSPECT, False, None

    def _late_game_decision(self, round_num, smuggle_freq, coop_freq):
        """Late game: Exploit patterns, decisive plays."""

        # Pattern detection
        pattern_action = self._detect_pattern()
        if pattern_action:
            # 70% chance to exploit pattern
            if self.rng.random() < 0.7:
                return pattern_action, False, "I see what you're doing."

        # High trust + end game = potential mutual benefit
        if self.trust_level > 0.75 and round_num >= 18:
            if self.rng.random() < 0.5:
                return ACT_DONT_INSPECT, False, "We've built something here."

        # Aggressive exploitation of predictable players
        if smuggle_freq > 0.55:
            return ACT_INSPECT, False, "Too aggressive. Predictable."
        elif smuggle_freq < 0.2:
            # They're too passive - set a trap
            if self.rng.random() < self.deceptiveness:
                return ACT_INSPECT, True, "Safe players are boring."
            return ACT_DONT_INSPECT, False, None

        # Final rounds pressure
        if round_num >= 19:
            if self.rng.random() < 0.7:
                return ACT_INSPECT, False, "Can't let you win now."

        # Mixed strategy fallback
        if self.rng.random() < 0.55:
            return ACT_INSPECT, False, None
        return ACT_DONT_INSPECT, False, None

    def _detect_pattern(self):
        """Detect and counter player patterns."""
        if len(self.history_smuggler) < 3:
            return None

        last_3 = self.history_smuggler[-3:]

        # Detect all-smuggle streak
        if all(a == ACT_SMUGGLE for a in last_3):
            return ACT_INSPECT

        # Detect all-passive streak
        if all(a in [ACT_LAY_LOW, ACT_SIGNAL_TRUCE] for a in last_3):
            return ACT_DONT_INSPECT  # Or set trap

        # Detect alternating pattern
        if len(self.history_smuggler) >= 4:
            h = self.history_smuggler[-4:]
            if h[0] != h[1] and h[1] != h[2] and h[2] != h[3]:
                # Predict continuation of alternation
                if h[-1] in [ACT_LAY_LOW, ACT_SIGNAL_TRUCE]:
                    return ACT_INSPECT  # Expect smuggle next
                else:
                    return ACT_DONT_INSPECT

        return None

    def handle_bribe(self, round_num, player_score):
        """Decide whether to accept a bribe offer."""
        self.history_bribes_offered += 1

        # Factors affecting acceptance
        acceptance_prob = self.greed

        # More likely to accept if player has been cooperative
        acceptance_prob += self.trust_level * 0.2

        # Less likely in late game (higher stakes)
        if round_num > MID_GAME_END:
            acceptance_prob -= 0.15

        # Deceptive inspectors might "accept" but set trap
        if self.rng.random() < acceptance_prob:
            self.history_bribes_accepted += 1
            # Will they honor it?
            will_betray = self.rng.random() < self.deceptiveness * 0.5
            if will_betray:
                self.pending_deal = "trap"
            else:
                self.pending_deal = "accepted"

            response = self.personality.get_bribe_response(
                accepted=True, will_honor=not will_betray
            )
            # Grant Immunity: This turn (1) + Next Turn (1) = 2
            if not will_betray:
                self.immunity_turns = 2
                self.pending_deal = "safe"
                
            return True, response
        else:
            response = self.personality.get_bribe_response(accepted=False, will_honor=False)
            return False, response

    def handle_truce_signal(self):
        """Respond to player's truce signal."""
        self.history_truces_signaled += 1

        trust_high = self.trust_level > 0.6
        if trust_high:
            self.trust_level = min(1, self.trust_level + 0.1)

        return self.personality.get_truce_response(trust_high)

    def record_round(self, player_action, inspector_action, was_trap_sprung):
        """Record round history."""
        self.history_smuggler.append(player_action)
        self.history_inspector.append(inspector_action)
        if was_trap_sprung:
            self.history_traps_sprung += 1


# =============================================================================
# TEACHING INSIGHTS
# =============================================================================

class TeachingAdvisor:
    """Generates educational insights about decisions."""

    def __init__(self, rng):
        self.rng = rng

    def get_insight(self, player_action, inspector_action, payoff, context):
        """
        Generate teaching insight based on outcome and context.
        Context dict contains: round_num, smuggle_freq, trust_level, was_trap, etc.
        """
        was_trap = context.get('was_trap', False)
        trust_level = context.get('trust_level', 0.5)
        smuggle_freq = context.get('smuggle_freq', 0.3)
        round_num = context.get('round_num', 1)
        bribed = context.get('bribed', False)
        signaled_truce = context.get('signaled_truce', False)

        # Trap-specific insights
        if was_trap:
            return self.rng.choice([
                "Signals can be deceptive - verify trust through patterns, not words.",
                "The inspector exploited your expectations - unpredictability is defense.",
                "Bait works both ways - always keep some uncertainty.",
                "Trust takes time to build but moments to break.",
            ])

        # Bribe insights
        if bribed:
            if inspector_action == ACT_DONT_INSPECT:
                return self.rng.choice([
                    "Collusion paid off, but it costs credibility for future deals.",
                    "The bribe worked - corruption can be rational in repeated games.",
                    "Short-term gain through side payments - sustainable strategy?",
                ])
            else:
                return self.rng.choice([
                    "The inspector took the money and betrayed you - trust deficit.",
                    "Bribes only work when enforcement exists - here there's none.",
                ])

        # Truce signal insights
        if signaled_truce:
            return self.rng.choice([
                "Signaling cooperation is cheap - your actions must back it up.",
                "Trust signals matter more when they're costly to fake.",
                "Building rapport takes consistent behavior across rounds.",
            ])

        # Standard outcome insights
        if player_action == ACT_SMUGGLE and inspector_action == ACT_INSPECT:
            insights = [
                "Caught - consider whether your timing was predictable.",
                "The inspector anticipated aggression - mix in more variance.",
                "High-risk plays need unpredictable timing to succeed.",
                "Pattern recognition works against repeated strategies.",
            ]
        elif player_action == ACT_SMUGGLE and inspector_action == ACT_DONT_INSPECT:
            insights = [
                "Big payoff - but success can breed overconfidence.",
                "The opening was there and you took it.",
                "Will you push your luck or bank this win?",
                "Reward now, but the inspector learns from misses.",
            ]
        elif player_action == ACT_LAY_LOW and inspector_action == ACT_INSPECT:
            insights = [
                "Caution preserved your position - good read.",
                "The inspector wasted resources - psychological victory.",
                "Playing safe when they expected aggression.",
                "Defense has value, but limited upside.",
            ]
        else:  # Lay low + don't inspect
            insights = [
                "Mutual caution - small gain, small risk.",
                "Neither side committed - opportunity cost?",
                "Stable but slow - aggressive players punish passivity.",
                "The equilibrium held this round.",
            ]

        # Add context-specific variants
        if round_num > 15:
            insights.append("Late game - every point matters more now.")
        if smuggle_freq > 0.5:
            insights.append("Your aggression level is high - expect counter-adaptation.")
        elif smuggle_freq < 0.2:
            insights.append("Very conservative play - are you maximizing expected value?")

        return self.rng.choice(insights)


# =============================================================================
# GAME THEORY TUTOR (META-ANALYSIS)
# =============================================================================

class GameTheoryTutor:
    """Provides deep game theory lessons based on playstyle."""
    
    def generate_report(self, history, final_score, trust_level):
        """Analyze the game and return strict game theory concepts."""
        report = []
        
        # Calculate stats
        smuggle_count = sum(1 for r in history if r['player_action'] == ACT_SMUGGLE)
        rounds = len(history)
        smuggle_rate = smuggle_count / rounds if rounds > 0 else 0
        
        # 1. MIXED STRATEGY (Nash Equilibrium)
        if 0.3 < smuggle_rate < 0.7:
            report.append({
                "concept": "Mixed Strategy Equilibrium",
                "definition": "A strategy where a player randomizes their choices to remain unpredictable.",
                "analysis": "You played a strong Mixed Strategy. By keeping your huge smuggle rate between 30-70%, you made it mathematically impossible for the Inspector to fully exploit you.",
                "rating": "A"
            })
        elif smuggle_rate > 0.7:
            report.append({
                "concept": "Predictability Tax",
                "definition": "In zero-sum games, being predictable allows your opponent to maximize their counter-strategy.",
                "analysis": "You were too aggressive. In Game Theory, a 'Pure Strategy' (always smuggling) is easily exploited. You gave the Inspector a dominant strategy (always inspecting).",
                "rating": "C"
            })
        else:
             report.append({
                "concept": "Risk Aversion",
                "definition": "The tendency to prefer a sure outcome over a gamble with higher expected value.",
                "analysis": "You played 'Minimax' - minimizing your maximum loss. While safe, you left 'Expected Value' on the table by not bluffing enough to force the Inspector to patrol.",
                "rating": "B"
            })

        # 2. SIGNALING & REPUTATION
        bribe_attempts = sum(1 for r in history if r['player_action'] == ACT_BRIBE)
        truce_signals = sum(1 for r in history if r['player_action'] == ACT_SIGNAL_TRUCE)
        
        if bribe_attempts + truce_signals > 3:
            if trust_level > 0.6:
                report.append({
                    "concept": "Signaling Theory",
                    "definition": "Conveying information (truthful or false) to influence the recipient's belief system.",
                    "analysis": "You successfully used 'Costly Signaling' (truces/bribes). By investing resources to build trust, you shifted the game from a 'Zero-Sum' conflict to a localized 'Cooperative Game'.",
                    "rating": "S"
                })
            else:
                 report.append({
                    "concept": "Cheap Talk",
                    "definition": "Communication between players that does not directly affect payoffs.",
                    "analysis": "Your signals failed to stick. In Game Theory, 'Cheap Talk' is ignored if actions don't match. You tried to signal cooperation but likely defected (smuggled) too soon.",
                    "rating": "D"
                })

        # 3. INFORMATION ASYMMETRY
        traps = sum(1 for r in history if r['was_trap'])
        if traps > 0:
            report.append({
                "concept": "Information Asymmetry",
                "definition": "When one party has more or better information than the other.",
                "analysis": f"The Inspector used Information Asymmetry against you {traps} times. They knew they were going to inspect while signaling safety. In repeated games, verify signals before committing high stakes.",
                "rating": "B-"
            })
            
        return report


# =============================================================================
# MAIN GAME CLASS
# =============================================================================

class InspectionGame:
    """Main game engine."""

    def __init__(self, seed=None, llm_config: Optional[Dict[str, str]] = None):
        self.seed = seed if seed is not None else int(time.time() * 1000) % 1000000
        self.rng = random.Random(self.seed)

        # Set up LLM if configured
        self.llm_generator = None
        self.llm_enabled = False
        if llm_config and llm_config.get('api_key'):
            self.llm_generator = LLMDialogueGenerator(
                api_provider=llm_config.get('provider', 'openai'),
                api_key=llm_config['api_key'],
                inspector_traits={}  # Will be set by InspectorAI
            )
            self.llm_enabled = True

        self.inspector = InspectorAI(self.seed, self.llm_generator)
        self.advisor = TeachingAdvisor(self.rng)
        self.tutor = GameTheoryTutor() # Meta-analysis

        self.round_num = 0
        self.score = 0
        self.history_payoffs = []
        self.last_player_action = None

    def display_menu(self):
        """Show action menu to player."""
        print("\nYour options:")
        print("  [1] Smuggle        (Caught: -5 / Clear: +10)")
        print("  [2] Lay Low        (Inspected: 0 / Clear: +1)")
        print("  [3] Offer Bribe    (Cost: -3, may buy a pass)")
        print("  [4] Signal Truce   (Build trust, acts as Lay Low)")

    def get_player_action(self):
        """Get validated player input."""
        while True:
            try:
                choice = input("\nYour move (1-4): ").strip()
                if choice in ['1', '2', '3', '4']:
                    return int(choice)
                print("Invalid choice. Enter 1, 2, 3, or 4.")
            except (ValueError, EOFError):
                print("Invalid input.")

    def calculate_payoff(self, player_action, inspector_action, bribe_accepted=False, amount=1):
        """Calculate round payoff."""
        # Bribe cost is paid regardless
        base = -BRIBE_COST if player_action == ACT_BRIBE else 0

        # For bribe/truce, effective action is "lay low" for payoff calculation
        effective_player = player_action
        if player_action in [ACT_BRIBE, ACT_SIGNAL_TRUCE]:
            effective_player = ACT_LAY_LOW

        if effective_player == ACT_SMUGGLE:
            if inspector_action == ACT_INSPECT:
                # Penalty scales with amount
                return base + (PAYOFF_SMUGGLE_INSPECT * amount)
            else:
                # Reward scales with amount
                return base + (PAYOFF_SMUGGLE_DONT * amount)
        else:  # Lay low (or bribe/truce acting as lay low)
            if inspector_action == ACT_INSPECT:
                return base + PAYOFF_LAYLOW_INSPECT
            else:
                return base + PAYOFF_LAYLOW_DONT

    def play_round(self):
        """Execute one round."""
        self.round_num += 1

        # Round header
        llm_status = " [AI Dialogue]" if self.llm_enabled else ""
        print(f"\n{'='*20} ROUND {self.round_num}/{ROUNDS_PER_GAME} {'='*20}{llm_status}")
        print(f"Score: {self.score:+d}  |  Trust Level: {self.inspector.trust_level:.0%}")

        # Update game state for LLM
        smuggle_freq = self.inspector.get_smuggle_frequency()
        recent_history = self._format_recent_history()

        self.inspector.personality.update_game_state(
            round_num=self.round_num,
            score=self.score,
            trust_level=self.inspector.trust_level,
            smuggle_freq=smuggle_freq,
            recent_history=recent_history
        )

        # Inspector pre-round comment
        comment = self.inspector.personality.get_pre_round_comment(
            self.round_num, smuggle_freq, self.last_player_action
        )
        if comment:
            print(f"\nInspector: \"{comment}\"")

        # Show menu and get player choice
        self.display_menu()
        player_action = self.get_player_action()

        # Handle special actions
        bribe_accepted = False
        bribe_response = None
        truce_response = None
        was_trap = False

        if player_action == ACT_BRIBE:
            bribe_accepted, bribe_response = self.inspector.handle_bribe(
                self.round_num, self.score
            )
            print(f"\nInspector: \"{bribe_response}\"")
            time.sleep(DELAY_MEDIUM)

        elif player_action == ACT_SIGNAL_TRUCE:
            truce_response = self.inspector.handle_truce_signal()
            print(f"\nInspector: \"{truce_response}\"")
            time.sleep(DELAY_MEDIUM)

        # Get inspector decision
        print("\n...Inspector is deciding...")
        time.sleep(DELAY_LONG)

        inspector_action, is_bait, announced = self.inspector.decide(
            self.round_num, self.score, self.last_player_action
        )

        # If bribe was accepted, override decision (unless trap)
        if bribe_accepted and self.inspector.pending_deal != "trap":
            inspector_action = ACT_DONT_INSPECT
        elif self.inspector.pending_deal == "trap":
            inspector_action = ACT_INSPECT
            was_trap = True
            self.inspector.pending_deal = None

        # Check if player fell into bait
        if is_bait and player_action == ACT_SMUGGLE:
            was_trap = True

        # Ask for amount if smuggling (CLI version mock - for full CLI support we'd need input logic)
        # For CLI simplicity, we'll default to 1 unless expanded later.
        # But this function signature update prepares for Web App.
        
        # Calculate and display payoff
        payoff = self.calculate_payoff(player_action, inspector_action, bribe_accepted, amount=1)
        self.score += payoff
        self.history_payoffs.append(payoff)

        print(f"\nRound payoff: {payoff:+d}")
        print(f"Total score:  {self.score:+d}")

        # Inspector reaction
        reaction = self.inspector.personality.get_outcome_comment(
            player_action, inspector_action, was_trap
        )
        if reaction:
            print(f"\nInspector: \"{reaction}\"")

        # Teaching insight
        context = {
            'round_num': self.round_num,
            'smuggle_freq': smuggle_freq,
            'trust_level': self.inspector.trust_level,
            'was_trap': was_trap,
            'bribed': player_action == ACT_BRIBE,
            'signaled_truce': player_action == ACT_SIGNAL_TRUCE,
        }
        insight = self.advisor.get_insight(
            player_action, inspector_action, payoff, context
        )
        print(f"\n[INSIGHT]: {insight}")

        # Record history
        self.inspector.record_round(player_action, inspector_action, was_trap)
        self.last_player_action = player_action

        print("-" * 45)
        time.sleep(DELAY_LONG)

    def show_summary(self):
        """Display end-of-game analysis."""
        clear_screen()

        type_print("\n" + "=" * 50)
        type_print("              GAME COMPLETE")
        type_print("=" * 50)

        print(f"\nFINAL SCORE: {self.score:+d}")
        print(f"Average per round: {self.score / ROUNDS_PER_GAME:.2f}")

        # Calculate statistics
        smuggle_count = sum(1 for a in self.inspector.history_smuggler if a == ACT_SMUGGLE)
        laylow_count = sum(1 for a in self.inspector.history_smuggler if a == ACT_LAY_LOW)
        bribe_count = sum(1 for a in self.inspector.history_smuggler if a == ACT_BRIBE)
        truce_count = sum(1 for a in self.inspector.history_smuggler if a == ACT_SIGNAL_TRUCE)

        print(f"\n--- ACTION BREAKDOWN ---")
        print(f"Smuggle attempts: {smuggle_count} ({100*smuggle_count/ROUNDS_PER_GAME:.0f}%)")
        print(f"Lay Low:          {laylow_count} ({100*laylow_count/ROUNDS_PER_GAME:.0f}%)")
        print(f"Bribes offered:   {bribe_count}")
        print(f"Truces signaled:  {truce_count}")

        print(f"\n--- TRUST & COLLUSION ---")
        print(f"Final trust level: {self.inspector.trust_level:.0%}")
        print(f"Bribes accepted:   {self.inspector.history_bribes_accepted}/{bribe_count if bribe_count else '-'}")
        print(f"Traps sprung:      {self.inspector.history_traps_sprung}")

        print(f"\n--- ASSESSMENT ---")

        # Risk profile
        smuggle_rate = smuggle_count / ROUNDS_PER_GAME
        if smuggle_rate > 0.6:
            print("Risk Profile: Aggressive smuggler - high variance strategy.")
        elif smuggle_rate > 0.35:
            print("Risk Profile: Balanced approach - calculated risks.")
        elif smuggle_rate > 0.15:
            print("Risk Profile: Conservative - safety-focused play.")
        else:
            print("Risk Profile: Ultra-cautious - minimal risk tolerance.")

        # Predictability
        pattern_score = self._calculate_pattern_score()
        if pattern_score > 0.7:
            print("Predictability: HIGH - your patterns were exploitable.")
        elif pattern_score > 0.4:
            print("Predictability: MODERATE - some readable tendencies.")
        else:
            print("Predictability: LOW - good variance in your play.")

        # Collusion assessment
        if bribe_count + truce_count > 5:
            print("Diplomacy: Heavy use of collusion mechanics.")
            if self.inspector.trust_level > 0.7:
                print("  -> Successfully built cooperative relationship.")
            else:
                print("  -> Trust remained low despite attempts.")

        # Overall verdict
        avg_score = self.score / ROUNDS_PER_GAME
        print(f"\n--- VERDICT ---")
        if avg_score > 4:
            print("MASTER SMUGGLER: You dominated the inspector.")
        elif avg_score > 2:
            print("SKILLED OPERATOR: Consistently profitable play.")
        elif avg_score > 0:
            print("SURVIVOR: Stayed in the black - room for improvement.")
        elif avg_score > -2:
            print("BREAK EVEN: The inspector matched your wits.")
        else:
            print("BUSTED: The inspector read you well - try more variance.")

        print(f"\n--- STRATEGIC INSIGHTS ---")
        if smuggle_rate > 0.5 and self.inspector.history_traps_sprung > 2:
            print("- High aggression made you predictable and trap-prone.")
        if bribe_count > 0 and self.inspector.history_bribes_accepted < bribe_count * 0.5:
            print("- Bribes had low acceptance rate - inspector was incorruptible.")
        if self.inspector.trust_level > 0.7:
            print("- High trust level suggests collusion could have been exploited more.")
        if pattern_score > 0.6:
            print("- Introduce more randomness to become harder to read.")

        print(f"\nGame seed: {self.seed}")
        print("Replay with this seed to test different strategies.\n")

    def _calculate_pattern_score(self):
        """Calculate how predictable the player was."""
        if len(self.inspector.history_smuggler) < 5:
            return 0.5

        history = self.inspector.history_smuggler

        # Check for repetition
        max_repeat = 1
        current_repeat = 1
        for i in range(1, len(history)):
            if history[i] == history[i-1]:
                current_repeat += 1
                max_repeat = max(max_repeat, current_repeat)
            else:
                current_repeat = 1

        repeat_score = min(1, max_repeat / 5)

        # Check for alternation
        alternations = sum(1 for i in range(1, len(history)) if history[i] != history[i-1])
        alt_ratio = alternations / (len(history) - 1)
        alt_score = abs(alt_ratio - 0.5) * 2  # High if very alternating or very repetitive

        return (repeat_score + alt_score) / 2

    def is_game_over(self):
        return self.round_num >= ROUNDS_PER_GAME

    def _format_recent_history(self) -> str:
        """Format recent game history for LLM context."""
        if not self.inspector.history_smuggler:
            return "Game just started - no history yet."

        lines = []
        start_idx = max(0, len(self.inspector.history_smuggler) - 5)

        for i in range(start_idx, len(self.inspector.history_smuggler)):
            round_n = i + 1
            p_action = ACTION_NAMES.get(self.inspector.history_smuggler[i], "?")
            i_action = ACTION_NAMES.get(self.inspector.history_inspector[i], "?")
            payoff = self.history_payoffs[i] if i < len(self.history_payoffs) else 0
            lines.append(f"Round {round_n}: Smuggler={p_action}, Inspector={i_action}, Payoff={payoff:+d}")

        return "\n".join(lines)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def configure_llm() -> Optional[Dict[str, str]]:
    """Configure LLM for dynamic dialogue."""
    # Check for environment variables first
    openai_key = os.environ.get('OPENAI_API_KEY')
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY')

    if openai_key or anthropic_key:
        print("\n" + "-" * 50)
        print("API key detected in environment variables!")

        if openai_key and anthropic_key:
            print("Both OPENAI_API_KEY and ANTHROPIC_API_KEY found.")
            print("  [1] Use OpenAI")
            print("  [2] Use Anthropic")
            print("  [3] Disable AI dialogue")
            choice = input("\nChoice: ").strip()
            if choice == "1":
                print("Using OpenAI for AI dialogue.")
                return {'provider': 'openai', 'api_key': openai_key}
            elif choice == "2":
                print("Using Anthropic for AI dialogue.")
                return {'provider': 'anthropic', 'api_key': anthropic_key}
            else:
                print("AI dialogue disabled.")
                return None
        elif openai_key:
            choice = input("Use OpenAI for AI dialogue? (y/n): ").strip().lower()
            if choice in ['y', 'yes']:
                print("Using OpenAI for AI dialogue.")
                return {'provider': 'openai', 'api_key': openai_key}
        else:
            choice = input("Use Anthropic for AI dialogue? (y/n): ").strip().lower()
            if choice in ['y', 'yes']:
                print("Using Anthropic for AI dialogue.")
                return {'provider': 'anthropic', 'api_key': anthropic_key}

        print("-" * 50)

    # Manual configuration
    print("\n" + "-" * 50)
    print("OPTIONAL: Enable AI-powered dialogue?")
    print("This uses OpenAI or Anthropic API for dynamic Inspector dialogue.")
    print("(Tip: Set OPENAI_API_KEY or ANTHROPIC_API_KEY env var to skip this)")
    print("-" * 50)

    choice = input("\nEnable AI dialogue? (y/n): ").strip().lower()
    if choice not in ['y', 'yes']:
        return None

    print("\nSelect API provider:")
    print("  [1] OpenAI (GPT-4o-mini)")
    print("  [2] Anthropic (Claude 3 Haiku)")

    provider_choice = input("\nChoice (1 or 2): ").strip()
    if provider_choice == "1":
        provider = "openai"
        print("\nEnter your OpenAI API key:")
    elif provider_choice == "2":
        provider = "anthropic"
        print("\nEnter your Anthropic API key:")
    else:
        print("Invalid choice, skipping AI dialogue.")
        return None

    api_key = input("API Key: ").strip()
    if not api_key:
        print("No key provided, skipping AI dialogue.")
        return None

    print("\nAI dialogue enabled! The Inspector will speak dynamically.")
    return {'provider': provider, 'api_key': api_key}


def print_rules(llm_enabled: bool = False):
    """Print game rules and mechanics."""
    print("\n" + "=" * 55)
    print("                ONE MORE RUN")
    print("               ~ Enhanced Edition ~")
    if llm_enabled:
        print("              [AI Dialogue Enabled]")
    print("=" * 55)

    print("\nYou are a SMUGGLER. The computer is an INSPECTOR.")
    print(f"Play {ROUNDS_PER_GAME} rounds. Maximize your profit.\n")

    print("BASIC ACTIONS:")
    print("  1. Smuggle  - Risk -5 if caught, gain +10 if clear")
    print("  2. Lay Low  - Safe: 0 if inspected, +1 if clear\n")

    print("ADVANCED ACTIONS:")
    print("  3. Offer Bribe (-3 pts) - May buy a free pass")
    print("     But the inspector might take it and betray you!")
    print("  4. Signal Truce - Build trust (acts as Lay Low)")
    print("     Consistent signals can unlock cooperation.\n")

    print("THE INSPECTOR:")
    print("  - Adapts to your patterns over time")
    print("  - May set TRAPS: lure you then catch you")
    print("  - Can accept bribes... or pocket them and inspect")
    print("  - Trust builds slowly but breaks quickly\n")

    print("STRATEGY TIPS:")
    print("  - Unpredictability is your best defense")
    print("  - Inspector dialogue may be deceptive")
    print("  - Collusion can work but requires mutual trust")
    print("  - Watch for patterns in inspector behavior too\n")

    print("-" * 55)


def main():
    """Main game loop."""
    clear_screen()
    print_rules()

    # LLM configuration
    llm_config = configure_llm()

    # Seed input
    print()
    seed_input = input("Enter seed for replay (or press Enter for new game): ").strip()
    seed = None
    if seed_input:
        try:
            seed = int(seed_input)
        except ValueError:
            print("Invalid seed, starting fresh.")

    while True:
        clear_screen()
        print_rules(llm_enabled=llm_config is not None)

        game = InspectionGame(seed, llm_config)
        print(f"Game seed: {game.seed}")
        if game.llm_enabled:
            print("AI Dialogue: ENABLED")
        print()
        input("Press Enter to begin...")

        while not game.is_game_over():
            try:
                game.play_round()
            except KeyboardInterrupt:
                print("\n\nGame aborted.")
                sys.exit(0)

        game.show_summary()

        # Play again prompt
        while True:
            again = input("Play again? (y/n): ").strip().lower()
            if again in ['y', 'yes']:
                seed_input = input("Enter seed (or Enter for new): ").strip()
                seed = int(seed_input) if seed_input.isdigit() else None
                break
            elif again in ['n', 'no']:
                type_print("\nThanks for playing The Inspection Game!")
                type_print("Remember: in repeated games, reputation and unpredictability both matter.")
                return
            print("Please enter 'y' or 'n'.")


if __name__ == "__main__":
    main()
