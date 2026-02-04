from flask import Flask, render_template, request, jsonify, session
import random
import time
import os
import uuid
# Import game logic from the existing file
from inspection_game import (
    InspectorAI, TeachingAdvisor,
    ROUNDS_PER_GAME, EARLY_GAME_END, MID_GAME_END,
    ACT_SMUGGLE, ACT_LAY_LOW, ACT_BRIBE, ACT_SIGNAL_TRUCE,
    ACT_INSPECT, ACT_DONT_INSPECT, ACT_ACCEPT_BRIBE, ACT_SET_TRAP,
    PAYOFF_SMUGGLE_INSPECT, PAYOFF_SMUGGLE_DONT, 
    PAYOFF_LAYLOW_INSPECT, PAYOFF_LAYLOW_DONT,
    BRIBE_COST, ACTION_NAMES, LLMDialogueGenerator
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# In-memory storage for active games (simplistic for this demo)
# In production, use Redis or a database
games = {}

class WebGameSession:
    def __init__(self, seed=None):
        self.id = str(uuid.uuid4())
        self.seed = seed if seed is not None else int(time.time() * 1000) % 1000000
        self.rng = random.Random(self.seed)
        
        # Initialize AI
        # LLM Disabled for production
        # api_key = os.getenv("OPENAI_API_KEY")
        # llm_gen = None
        # if api_key:
        #     llm_gen = LLMDialogueGenerator("openai", api_key, {})
        
        self.inspector = InspectorAI(self.seed, llm_generator=None)
        self.advisor = TeachingAdvisor(self.rng)
        # Import GameTheoryTutor inside WebSession if not available globally, or assume it's imported
        from inspection_game import GameTheoryTutor
        self.tutor = GameTheoryTutor()
        
        self.round_num = 0
        self.score = 0
        self.history = []
        self.last_player_action = None
        
    def to_dict(self):
        data = {
            'id': self.id,
            'round': self.round_num,
            'max_rounds': ROUNDS_PER_GAME,
            'score': self.score,
            'trust_level': self.inspector.trust_level,
            'inspector_mood': self.inspector.personality.mood,
            'history': self.history[-5:], # Send last 5 for efficiency
            'game_over': self.round_num >= ROUNDS_PER_GAME
        }
        
        if data['game_over']:
            # Generate insights
            # Convert web history format back to expected format if needed, or just pass as is
            # The tutor expects simple dicts, our history is similar enough
            data['tutor_report'] = self.tutor.generate_report(self.history, self.score, self.inspector.trust_level)
            
        return data

    def play_round(self, player_action, amount=1):
        if self.round_num >= ROUNDS_PER_GAME:
            return {'error': 'Game Over'}
            
        self.round_num += 1
        
        # 1. Pre-round Analysis (for pre-round flavor text in frontend?)
        # For simplicity, we process everything in one go here.
        
        # 2. Handle Special Actions
        bribe_accepted = False
        was_trap = False
        
        flavor_text = {}
        
        if player_action == ACT_BRIBE:
            bribe_accepted, response = self.inspector.handle_bribe(self.round_num, self.score)
            flavor_text['bribe_response'] = response
        elif player_action == ACT_SIGNAL_TRUCE:
            response = self.inspector.handle_truce_signal()
            flavor_text['truce_response'] = response
            
        # 3. Inspector Decision
        inspector_action, is_bait, announced = self.inspector.decide(
            self.round_num, self.score, self.last_player_action
        )
        
        # Override logic from CLI main loop
        if bribe_accepted and self.inspector.pending_deal != "trap":
            inspector_action = ACT_DONT_INSPECT
        elif self.inspector.pending_deal == "trap":
            inspector_action = ACT_INSPECT
            was_trap = True
            self.inspector.pending_deal = None
            
        if is_bait and player_action == ACT_SMUGGLE:
            was_trap = True
            
        # 4. Payoff
        # Calculate base cost (bribe)
        payoff = 0
        if player_action == ACT_BRIBE:
            payoff -= BRIBE_COST
            
        effective_player = ACT_LAY_LOW if player_action in [ACT_BRIBE, ACT_SIGNAL_TRUCE] else player_action
        
        if effective_player == ACT_SMUGGLE:
            if inspector_action == ACT_INSPECT:
                payoff += (PAYOFF_SMUGGLE_INSPECT * amount)
            else:
                payoff += (PAYOFF_SMUGGLE_DONT * amount)
        else:
            if inspector_action == ACT_INSPECT:
                payoff += PAYOFF_LAYLOW_INSPECT
            else:
                payoff += PAYOFF_LAYLOW_DONT
                
        self.score += payoff
        
        # 5. Insight & Flavor
        reaction = self.inspector.personality.get_outcome_comment(
            player_action, inspector_action, was_trap
        )
        flavor_text['reaction'] = reaction
        
        context = {
            'round_num': self.round_num,
            'smuggle_freq': self.inspector.get_smuggle_frequency(),
            'trust_level': self.inspector.trust_level,
            'was_trap': was_trap,
            'bribed': player_action == ACT_BRIBE,
            'signaled_truce': player_action == ACT_SIGNAL_TRUCE,
        }
        insight = self.advisor.get_insight(player_action, inspector_action, payoff, context)
        
        # Record
        self.inspector.record_round(player_action, inspector_action, was_trap)
        self.last_player_action = player_action
        
        round_result = {
            'round': self.round_num,
            'player_action': player_action,
            'player_action_name': ACTION_NAMES.get(player_action, "Unknown"),
            'inspector_action': inspector_action,
            'inspector_action_name': ACTION_NAMES.get(inspector_action, "Unknown"),
            'payoff': payoff,
            'amount': amount,
            'total_score': self.score,
            'insight': insight,
            'flavor': flavor_text,
            'was_trap': was_trap,
            'bribe_accepted': bribe_accepted,
            'game_over': self.round_num >= ROUNDS_PER_GAME
        }
        
        self.history.append(round_result)
        return round_result

@app.route('/theory')
def theory():
    return render_template('theory.html')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_game():
    game = WebGameSession()
    games[game.id] = game
    session['game_id'] = game.id
    return jsonify(game.to_dict())

@app.route('/api/move', methods=['POST'])
def move():
    game_id = session.get('game_id')
    if not game_id or game_id not in games:
        return jsonify({'error': 'No active game'}), 400
        
    game = games[game_id]
    data = request.json
    try:
        action = int(data.get('action'))
        amount = int(data.get('amount', 1))
        # Cap amount to prevent abuse
        amount = max(1, min(amount, 5)) 
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid inputs'}), 400
        
    result = game.play_round(action, amount)
    return jsonify(result)

@app.route('/api/state', methods=['GET'])
def get_state():
    game_id = session.get('game_id')
    if not game_id or game_id not in games:
        return jsonify({'error': 'No active game'}), 400
    
    return jsonify(games[game_id].to_dict())

if __name__ == '__main__':
    app.run(debug=True, port=5000)
