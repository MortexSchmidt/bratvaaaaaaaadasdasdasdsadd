from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import uuid
import json
from datetime import datetime, timedelta
import random

app = Flask(__name__)
CORS(app)

# Хранилище данных (в реальном приложении использовать базу данных)
lobbies = {}
games = {}
players = {}

# Загрузка контента для игры
CONTENT_FILE = os.path.join(os.path.dirname(__file__), '../../../truth_or_dare_content.json')
try:
    with open(CONTENT_FILE, 'r', encoding='utf-8') as f:
        GAME_CONTENT = json.load(f)
except FileNotFoundError:
    GAME_CONTENT = {"truths": {"safe": [], "spicy": [], "risky": []}, "dares": {"safe": [], "spicy": [], "risky": []}}

# Конфигурация
STATIC_FOLDER = os.path.join(os.path.dirname(__file__), 'static')
TEMPLATES_FOLDER = os.path.join(os.path.dirname(__file__), 'templates')

# Убедимся, что папки существуют
os.makedirs(STATIC_FOLDER, exist_ok=True)
os.makedirs(TEMPLATES_FOLDER, exist_ok=True)

@app.route('/')
def index():
    """Главная страница Mini-App"""
    return render_template('index.html')

@app.route('/api/health')
def health_check():
    """Проверка состояния API"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/lobby', methods=['POST'])
def create_lobby():
    """Создание нового лобби"""
    data = request.get_json()
    
    # Проверка обязательных полей
    required_fields = ['player_name', 'game_mode', 'rules_mode', 'difficulty_setting']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Проверка валидности значений
    if data['game_mode'] not in ['clockwise', 'anyone']:
        return jsonify({'error': 'Invalid game_mode. Use "clockwise" or "anyone"'}), 400
    
    if data['rules_mode'] not in ['with', 'without']:
        return jsonify({'error': 'Invalid rules_mode. Use "with" or "without"'}), 400
    
    if data['difficulty_setting'] not in ['all', 'safe', 'spicy', 'risky']:
        return jsonify({'error': 'Invalid difficulty_setting. Use "all", "safe", "spicy", or "risky"'}), 400
    
    # Генерация уникального кода лобби
    lobby_code = generate_unique_code()
    
    # Создание лобби
    lobby_id = str(uuid.uuid4())
    lobbies[lobby_id] = {
        'id': lobby_id,
        'code': lobby_code,
        'game_mode': data['game_mode'],
        'rules_mode': data['rules_mode'],
        'difficulty_setting': data['difficulty_setting'],
        'created_at': datetime.now(),
        'players': [{
            'id': str(uuid.uuid4()),
            'name': data['player_name'],
            'is_host': True,
            'joined_at': datetime.now()
        }],
        'max_players': 8
    }
    
    # Сохранение игрока
    player_id = lobbies[lobby_id]['players'][0]['id']
    players[player_id] = {
        'id': player_id,
        'name': data['player_name'],
        'lobby_id': lobby_id
    }
    
    return jsonify({
        'lobby_id': lobby_id,
        'lobby_code': lobby_code,
        'player_id': player_id
    }), 201

@app.route('/api/lobby/<lobby_code>/join', methods=['POST'])
def join_lobby(lobby_code):
    """Присоединение к лобби по коду"""
    data = request.get_json()
    
    # Поиск лобби по коду
    lobby = find_lobby_by_code(lobby_code)
    if not lobby:
        return jsonify({'error': 'Lobby not found'}), 404
    
    # Проверка максимального количества игроков
    if len(lobby['players']) >= lobby['max_players']:
        return jsonify({'error': 'Lobby is full'}), 400
    
    # Проверка наличия имени игрока
    if 'player_name' not in data:
        return jsonify({'error': 'Missing player name'}), 400
    
    # Проверка длины имени
    if len(data['player_name']) > 30:
        return jsonify({'error': 'Player name too long (max 30 characters)'}), 400
    
    # Добавление игрока в лобби
    player_id = str(uuid.uuid4())
    lobby['players'].append({
        'id': player_id,
        'name': data['player_name'],
        'is_host': False,
        'joined_at': datetime.now()
    })
    
    # Сохранение игрока
    players[player_id] = {
        'id': player_id,
        'name': data['player_name'],
        'lobby_id': lobby['id']
    }
    
    return jsonify({
        'player_id': player_id,
        'lobby_id': lobby['id']
    }), 200

@app.route('/api/lobby/<lobby_id>')
def get_lobby(lobby_id):
    """Получение информации о лобби"""
    if lobby_id not in lobbies:
        return jsonify({'error': 'Lobby not found'}), 404
    
    lobby = lobbies[lobby_id]
    
    # Форматирование данных для ответа
    response = {
        'id': lobby['id'],
        'code': lobby['code'],
        'game_mode': lobby['game_mode'],
        'rules_mode': lobby['rules_mode'],
        'difficulty_setting': lobby['difficulty_setting'],
        'created_at': lobby['created_at'].isoformat(),
        'players': [{
            'id': player['id'],
            'name': player['name'],
            'is_host': player['is_host'],
            'joined_at': player['joined_at'].isoformat()
        } for player in lobby['players']],
        'player_count': len(lobby['players']),
        'max_players': lobby['max_players']
    }
    
    return jsonify(response), 200

@app.route('/api/lobby/<lobby_id>/start', methods=['POST'])
def start_game(lobby_id):
    """Начало игры из лобби"""
    if lobby_id not in lobbies:
        return jsonify({'error': 'Lobby not found'}), 404
    
    lobby = lobbies[lobby_id]
    
    # Проверка минимального количества игроков
    if len(lobby['players']) < 2:
        return jsonify({'error': 'Minimum 2 players required'}), 400
    
    # Создание игры
    game_id = str(uuid.uuid4())
    games[game_id] = {
        'id': game_id,
        'lobby_id': lobby_id,
        'game_mode': lobby['game_mode'],
        'rules_mode': lobby['rules_mode'],
        'difficulty_setting': lobby['difficulty_setting'],
        'players': lobby['players'].copy(),
        'current_player_index': 0,
        'passes_used': {player['id']: 0 for player in lobby['players']},
        'started_at': datetime.now(),
        'status': 'active',
        'history': []  # История заданий
    }
    
    # Удаление лобби
    del lobbies[lobby_id]
    
    return jsonify({
        'game_id': game_id,
        'message': 'Game started successfully'
    }), 200

@app.route('/api/game/<game_id>')
def get_game(game_id):
    """Получение информации об игре"""
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = games[game_id]
    
    # Форматирование данных для ответа
    response = {
        'id': game['id'],
        'game_mode': game['game_mode'],
        'rules_mode': game['rules_mode'],
        'difficulty_setting': game['difficulty_setting'],
        'players': [{
            'id': player['id'],
            'name': player['name'],
            'is_host': player['is_host']
        } for player in game['players']],
        'current_player': game['players'][game['current_player_index']]['name'],
        'current_player_id': game['players'][game['current_player_index']]['id'],
        'started_at': game['started_at'].isoformat(),
        'status': game['status'],
        'history': game['history']
    }
    
    return jsonify(response), 200

@app.route('/api/game/<game_id>/next-turn', methods=['POST'])
def next_turn(game_id):
    """Передача хода следующему игроку"""
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = games[game_id]
    
    # Обновление индекса текущего игрока
    game['current_player_index'] = (game['current_player_index'] + 1) % len(game['players'])
    
    return jsonify({
        'message': 'Turn passed successfully',
        'current_player': game['players'][game['current_player_index']]['name'],
        'current_player_id': game['players'][game['current_player_index']]['id']
    }), 200

@app.route('/api/game/<game_id>/make-choice', methods=['POST'])
def make_choice(game_id):
    """Сделать выбор (правда, действие, пас и т.д.)"""
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = games[game_id]
    data = request.get_json()
    
    if 'choice_type' not in data:
        return jsonify({'error': 'Missing choice_type'}), 400
    
    choice_type = data['choice_type']
    
    if choice_type == 'pass':
        # Проверка, можно ли использовать пас
        current_player_id = game['players'][game['current_player_index']]['id']
        max_passes = 1 if game['rules_mode'] == 'with' else float('inf')
        
        if game['passes_used'][current_player_id] >= max_passes:
            return jsonify({'error': 'Maximum passes used'}), 400
        
        # Использовать пас
        game['passes_used'][current_player_id] += 1
        game['current_player_index'] = (game['current_player_index'] + 1) % len(game['players'])
        
        return jsonify({
            'message': 'Pass used, turn passed to next player',
            'current_player': game['players'][game['current_player_index']]['name'],
            'current_player_id': game['players'][game['current_player_index']]['id']
        }), 200
    
    elif choice_type in ['truth', 'dare', 'random']:
        # Генерация задания
        if choice_type == 'random':
            choice_type = random.choice(['truth', 'dare'])
        
        # Определение целевого игрока в зависимости от режима
        if game['game_mode'] == 'clockwise':
            target_player_index = (game['current_player_index'] + 1) % len(game['players'])
        else:  # anyone
            if 'target_player_id' not in data:
                return jsonify({'error': 'Target player required in "anyone" mode'}), 400
            target_player_id = data['target_player_id']
            target_player_index = next((i for i, p in enumerate(game['players']) if p['id'] == target_player_id), -1)
            if target_player_index == -1:
                return jsonify({'error': 'Target player not found in game'}), 400
        
        # Получение контента
        content = get_random_content(choice_type, game['difficulty_setting'])
        
        # Добавление в историю
        game['history'].append({
            'from_player_id': game['players'][game['current_player_index']]['id'],
            'to_player_id': game['players'][target_player_index]['id'],
            'type': choice_type,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'message': f'{choice_type.capitalize()} selected',
            'content': content,
            'from_player': game['players'][game['current_player_index']]['name'],
            'to_player': game['players'][target_player_index]['name'],
            'type': choice_type
        }), 200
    
    else:
        return jsonify({'error': 'Invalid choice_type. Use "truth", "dare", "random", or "pass"'}), 400

def get_random_content(content_type, difficulty_setting):
    """Получить случайный контент для задания"""
    if content_type not in ['truth', 'dare']:
        return "Неверный тип контента"
    
    key = "truths" if content_type == "truth" else "dares"
    
    if difficulty_setting == "all":
        # Объединяем все уровни сложности
        options = []
        for diff in GAME_CONTENT[key].values():
            options.extend(diff)
    elif difficulty_setting in GAME_CONTENT[key]:
        # Используем только указанный уровень сложности
        options = GAME_CONTENT[key][difficulty_setting]
    else:
        # Если указан неверный уровень, используем все
        options = []
        for diff in GAME_CONTENT[key].values():
            options.extend(diff)
    
    if not options:
        return "Контент не найден"
    
    return random.choice(options)

# Вспомогательные функции
def generate_unique_code():
    """Генерация уникального 6-значного кода лобби"""
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    while True:
        code = ''.join([random.choice(chars) for _ in range(6)])
        if not find_lobby_by_code(code):
            return code

def find_lobby_by_code(code):
    """Поиск лобби по коду"""
    for lobby in lobbies.values():
        if lobby['code'] == code:
            return lobby
    return None

# Обработка ошибок
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)