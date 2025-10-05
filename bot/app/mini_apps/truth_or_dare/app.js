// Улучшенный JavaScript файл для Mini-App "Правда или Действие 2.0"

// Инициализация Telegram Web App API
let tg;
try {
 tg = window.Telegram.WebApp;
  tg.expand();
  tg.enableClosingConfirmation();
} catch (e) {
  console.log("Telegram Web App API не доступен");
}

// Глобальные переменные
let currentTheme = 'light';
let gameState = {
 screen: 'welcome',
  lobbyCode: '',
  playerName: '',
  players: [],
  currentPlayerIndex: 0,
  gameMode: 'clockwise', // clockwise или anyone
  rulesMode: 'with', // with или without
  difficultySetting: 'all', // all, safe, spicy, risky
  currentTask: null,
 taskType: null,
  targetPlayerId: null,
  passesUsed: {}, // Счетчик пасов для каждого игрока
  maxPasses: 1, // Максимальное количество пасов при включенных правилах
  gameActive: false
};

// DOM Elements
const screens = {
  welcome: document.getElementById('welcome-screen'),
  createLobby: document.getElementById('create-lobby-screen'),
  joinLobby: document.getElementById('join-lobby-screen'),
  lobby: document.getElementById('lobby-screen'),
  game: document.getElementById('game-screen'),
  taskSelection: document.getElementById('task-selection-screen')
};

// Инициализация приложения
document.addEventListener('DOMContentLoaded', function() {
  // Проверяем тему системы
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    setTheme('dark');
  }
  
  // Показываем начальный экран
  showScreen('welcome');
  
  // Инициализируем Telegram Web App
  initializeTelegramWebApp();
  
  // Анимация прогресса на главном экране
  animateWelcomeProgress();
});

// Функции навигации между экранами
function showScreen(screenName) {
  // Скрываем все экраны
  Object.values(screens).forEach(screen => {
    screen.classList.remove('active');
 });
  
  // Показываем нужный экран
  if (screens[screenName]) {
    screens[screenName].classList.add('active');
    gameState.screen = screenName;
  }
}

function showWelcome() {
  showScreen('welcome');
}

function showCreateLobby() {
  showScreen('createLobby');
}

function showJoinLobby() {
  showScreen('joinLobby');
}

function showLobby() {
  showScreen('lobby');
  updateLobbyInfo();
  animateLobbyProgress();
}

function showGame() {
  showScreen('game');
  updateGameInfo();
  animateGameProgress();
}

function showTaskSelection() {
  showScreen('taskSelection');
  updateTaskSelectionScreen();
}

function showQuickGame() {
  // Быстрая игра - создает лобби с настройками по умолчанию
  gameState.playerName = "Игрок";
  gameState.gameMode = 'clockwise';
  gameState.rulesMode = 'with';
  gameState.difficultySetting = 'all';
  gameState.lobbyCode = generateLobbyCode();
  gameState.players = [{
    id: generatePlayerId(),
    name: gameState.playerName,
    isHost: true
  }];
  
  showNotification(`Быстрая игра создана! Код: ${gameState.lobbyCode}`);
  showLobby();
}

// Функции работы с темой
function toggleTheme() {
 currentTheme = currentTheme === 'light' ? 'dark' : 'light';
  setTheme(currentTheme);
}

function setTheme(theme) {
 currentTheme = theme;
  document.documentElement.setAttribute('data-theme', theme);
  
  // Обновляем иконку темы
  const themeIcon = document.getElementById('theme-icon');
  if (themeIcon) {
    themeIcon.textContent = theme === 'light' ? '🌙' : '☀️';
  }
  
  // Сохраняем выбор темы
  localStorage.setItem('theme', theme);
}

// Функции работы с лобби
function createLobby() {
  const playerNameInput = document.getElementById('player-name');
  const playerName = playerNameInput.value.trim();
  
  if (!playerName) {
    showNotification('Пожалуйста, введите ваше имя');
    return;
  }
  
  if (playerName.length > 30) {
    showNotification('Имя должно быть не длиннее 30 символов');
    return;
  }
  
  // Получаем выбранные режимы
  const gameMode = document.querySelector('input[name="game-mode"]:checked').value;
  const rulesMode = document.querySelector('input[name="rules-mode"]:checked').value;
  const difficultySetting = document.getElementById('difficulty-setting').value;
  
  // Создаем лобби (в реальной реализации будет API вызов)
  gameState.playerName = playerName;
  gameState.gameMode = gameMode;
  gameState.rulesMode = rulesMode;
 gameState.difficultySetting = difficultySetting;
  gameState.lobbyCode = generateLobbyCode();
  gameState.players = [{
    id: generatePlayerId(),
    name: playerName,
    isHost: true
  }];
  
  // Устанавливаем максимальное количество пасов в зависимости от режима
  gameState.maxPasses = rulesMode === 'with' ? 1 : Infinity;
  
  showNotification(`Лобби создано! Код: ${gameState.lobbyCode}`);
  showLobby();
}

function joinLobby() {
 const playerNameInput = document.getElementById('join-player-name');
  const lobbyCodeInput = document.getElementById('lobby-code');
  
  const playerName = playerNameInput.value.trim();
  const lobbyCode = lobbyCodeInput.value.trim().toUpperCase();
  
  if (!playerName) {
    showNotification('Пожалуйста, введите ваше имя');
    return;
  }
  
  if (playerName.length > 30) {
    showNotification('Имя должно быть не длиннее 30 символов');
    return;
  }
  
  if (!lobbyCode || lobbyCode.length !== 6) {
    showNotification('Пожалуйста, введите корректный 6-значный код лобби');
    return;
  }
  
  // В реальной реализации здесь будет API вызов для присоединения к лобби
 // Пока симулируем успешное присоединение
  gameState.playerName = playerName;
  gameState.lobbyCode = lobbyCode;
 gameState.players = [
    {
      id: generatePlayerId(),
      name: playerName,
      isHost: false
    },
    {
      id: generatePlayerId(),
      name: "Игрок 2",
      isHost: true
    }
  ];
  
  showNotification('Вы успешно присоединились к лобби!');
  showLobby();
}

function startGame() {
  if (gameState.players.length < 2) {
    showNotification('Нужно минимум 2 игрока для начала игры');
    return;
  }
  
  gameState.gameActive = true;
  gameState.passesUsed = {}; // Сбросить счетчик пасов
 gameState.players.forEach(player => {
    gameState.passesUsed[player.id] = 0;
  });
  
  showNotification('Игра началась!');
  showGame();
}

function endGame() {
  if (confirm('Вы уверены, что хотите завершить игру?')) {
    gameState.gameActive = false;
    showLobby();
    showNotification('Игра завершена');
  }
}

function leaveLobby() {
  if (confirm('Вы уверены, что хотите покинуть лобби?')) {
    gameState.players = [];
    gameState.lobbyCode = '';
    gameState.gameActive = false;
    showWelcome();
    showNotification('Вы покинули лобби');
  }
}

function copyLobbyCode() {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(gameState.lobbyCode).then(() => {
      showNotification('Код лобби скопирован в буфер обмена');
    }).catch(err => {
      console.error('Ошибка при копировании: ', err);
      showNotification('Не удалось скопировать код');
    });
  } else {
    // Альтернативный метод для старых браузеров
    const textArea = document.createElement("textarea");
    textArea.value = gameState.lobbyCode;
    document.body.appendChild(textArea);
    textArea.select();
    try {
      document.execCommand('copy');
      showNotification('Код лобби скопирован в буфер обмена');
    } catch (err) {
      showNotification('Не удалось скопировать код');
    }
    document.body.removeChild(textArea);
  }
}

// Функции обновления UI
function updateLobbyInfo() {
  // Обновляем информацию о лобби
  const lobbyCodeDisplay = document.getElementById('lobby-code-display');
  const playerCountDisplay = document.getElementById('player-count');
  const startGameBtn = document.getElementById('start-game-btn');
  const playersList = document.getElementById('players-list');
  
  if (lobbyCodeDisplay) {
    lobbyCodeDisplay.textContent = `Код: ${gameState.lobbyCode}`;
  }
  
  if (playerCountDisplay) {
    playerCountDisplay.textContent = `Игроков: ${gameState.players.length}/8`;
  }
  
  // Обновляем кнопку начала игры
  if (startGameBtn) {
    startGameBtn.disabled = gameState.players.length < 2;
  }
  
  // Обновляем список игроков
  if (playersList) {
    playersList.innerHTML = '';
    gameState.players.forEach((player, index) => {
      const playerElement = document.createElement('div');
      playerElement.className = `player-item ${player.isHost ? 'host' : ''}`;
      playerElement.innerHTML = `
        <span class="player-name">${player.name} ${player.isHost ? '(Вы)' : ''}</span>
        ${player.isHost ? '<span class="host-badge">👑</span>' : ''}
      `;
      playersList.appendChild(playerElement);
    });
  }
}

function updateGameInfo() {
  const currentPlayerDisplay = document.getElementById('current-player');
  const gameModeDisplay = document.getElementById('game-mode');
  
  if (currentPlayerDisplay) {
    const currentPlayer = gameState.players[gameState.currentPlayerIndex];
    currentPlayerDisplay.textContent = `Ход: ${currentPlayer.name}`;
  }
  
  if (gameModeDisplay) {
    const modeText = gameState.gameMode === 'clockwise' ? 'По часовой' : 'Кому угодно';
    gameModeDisplay.textContent = `Режим: ${modeText}`;
  }
  
  updatePlayersGrid();
}

function updatePlayersGrid() {
  const playersGrid = document.getElementById('players-grid');
  if (!playersGrid) return;
  
  playersGrid.innerHTML = '';
  
  gameState.players.forEach((player, index) => {
    const playerCard = document.createElement('div');
    playerCard.className = `player-card ${index === gameState.currentPlayerIndex ? 'active' : ''}`;
    playerCard.innerHTML = `
      <div class="player-avatar">👤</div>
      <div class="player-name">${player.name}</div>
      ${index === gameState.currentPlayerIndex ? '<div class="player-status">Ход</div>' : ''}
    `;
    playersGrid.appendChild(playerCard);
  });
}

function updateTaskSelectionScreen() {
  const targetPlayer = gameState.players[gameState.currentPlayerIndex];
  const targetPlayerName = document.getElementById('target-player-name');
  const taskTypeLabel = document.getElementById('task-type-label');
  
  if (targetPlayerName) {
    targetPlayerName.textContent = targetPlayer.name;
  }
  
  if (taskTypeLabel) {
    taskTypeLabel.textContent = gameState.taskType === 'truth' ? 
      'Введите вопрос для "Правды":' : 
      'Введите задание для "Действия":';
  }
}

// Функции выбора заданий
function selectChoice(choiceType) {
  const choices = {
    truth: { icon: '💡', label: 'Правда', color: '#4361ee' },
    dare: { icon: '🎭', label: 'Действие', color: '#f72585' },
    random: { icon: '🎲', label: 'Случайное', color: '#4cc9f0' },
    pass: { icon: '⏭️', label: 'Пас', color: '#7209b7' }
  };
  
  const choice = choices[choiceType];
  if (!choice) return;
  
  if (choiceType === 'pass') {
    // Проверяем, можно ли использовать пас
    const currentPlayer = gameState.players[gameState.currentPlayerIndex];
    if (gameState.passesUsed[currentPlayer.id] >= gameState.maxPasses) {
      showNotification('Вы уже использовали максимальное количество пасов!');
      return;
    }
    
    gameState.passesUsed[currentPlayer.id] += 1;
    showNotification(`Вы использовали пас!`);
    
    // Переходим к следующему игроку
    nextPlayer();
  } else if (choiceType === 'random') {
    // Генерируем случайное задание
    const randomType = Math.random() > 0.5 ? 'truth' : 'dare';
    const randomContent = getRandomContent(randomType);
    
    showNotification(`Случайное задание: ${randomContent}`);
    
    // Показываем карточку задания
    showTaskCard(randomType, randomContent);
    
    // Переходим к следующему игроку
    nextPlayer();
  } else {
    // Для "Правды" или "Действия" переходим к экрану создания задания
    gameState.taskType = choiceType;
    
    // Определяем следующего игрока в зависимости от режима
    if (gameState.gameMode === 'clockwise') {
      gameState.targetPlayerId = (gameState.currentPlayerIndex + 1) % gameState.players.length;
    } else {
      // В режиме "кому угодно" нужно выбрать игрока
      // Пока упрощаем и выбираем следующего
      gameState.targetPlayerId = (gameState.currentPlayerIndex + 1) % gameState.players.length;
    }
    
    showTaskSelection();
  }
}

function getRandomContent(type) {
  // В реальной реализации здесь будет API вызов для получения случайного контента
  // Пока возвращаем заглушку
 if (type === 'truth') {
    const truths = [
      "Какой твой любимый мем в TikTok?",
      "Какая песня всегда поднимает тебе настроение?",
      "Если бы ты мог путешествовать куда угодно прямо сейчас, куда бы поехал?",
      "Какой у тебя самый смешной навык?",
      "Если бы ты выиграл миллион, что бы купил первым делом?"
    ];
    return truths[Math.floor(Math.random() * truths.length)];
  } else {
    const dares = [
      "Спой куплет своей любимой песни голосом робота",
      "Сделай 10 танцевальных движений под воображаемую музыку",
      "Напиши комплимент каждому участнику игры в голосовом сообщении",
      "Изобрази позу йоги 'дерево' и удерживай 10 секунд",
      "Сделай селфи с самой глупой гримасой"
    ];
    return dares[Math.floor(Math.random() * dares.length)];
  }
}

function showTaskCard(type, content) {
  const container = document.getElementById('task-card-container');
  const card = document.getElementById('task-card');
  const taskContent = document.getElementById('task-content');
  
  if (container && taskContent) {
    container.style.display = 'block';
    taskContent.textContent = content;
    
    // Анимация переворота карточки
    setTimeout(() => {
      if (card) {
        card.classList.add('flipped');
      }
    }, 500);
  }
}

function sendTask() {
  const taskInput = document.getElementById('task-input');
  const taskContent = taskInput.value.trim();
  
  if (!taskContent) {
    showNotification('Пожалуйста, введите задание');
    return;
  }
  
  if (taskContent.length > 200) {
    showNotification('Задание должно быть не длиннее 200 символов');
    return;
  }
  
  // Отправляем задание (в реальной реализации будет API вызов)
  showNotification(`Задание отправлено игроку!`);
  
  // Показываем карточку задания
  showTaskCard(gameState.taskType, taskContent);
  
  // Переходим к следующему игроку
  nextPlayer();
  
  // Возвращаемся в игру
 showGame();
}

function setDifficulty(difficulty) {
  // Устанавливаем уровень сложности
  gameState.difficultySetting = difficulty;
  showNotification(`Уровень сложности установлен: ${getDifficultyName(difficulty)}`);
}

function getDifficultyName(difficulty) {
  const names = {
    'safe': 'Безопасно',
    'spicy': 'Остро',
    'risky': 'Рискованно',
    'all': 'Все уровни'
  };
 return names[difficulty] || 'Неизвестно';
}

function nextPlayer() {
  gameState.currentPlayerIndex = (gameState.currentPlayerIndex + 1) % gameState.players.length;
  updateGameInfo();
  showNotification('Ход переходит к следующему игроку');
}

// Вспомогательные функции
function generateLobbyCode() {
  // Генерируем случайный 6-значный код
 const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let result = '';
  for (let i = 0; i < 6; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

function generatePlayerId() {
  // Генерируем уникальный ID для игрока
  return Date.now() + Math.floor(Math.random() * 10000);
}

function showNotification(message) {
  const notification = document.getElementById('notification');
  const notificationText = document.getElementById('notification-text');
  
  if (notification && notificationText) {
    notificationText.textContent = message;
    notification.classList.add('show');
    
    setTimeout(() => {
      notification.classList.remove('show');
    }, 3000);
 }
  
  // Также показываем уведомление через Telegram Web App API
  if (tg) {
    tg.showPopup({
      title: 'Уведомление',
      message: message,
      buttons: [{type: 'ok'}]
    });
 }
}

// Анимации прогресса
function animateWelcomeProgress() {
  const progressBar = document.getElementById('welcome-progress');
  if (progressBar) {
    progressBar.style.width = '0%';
    setTimeout(() => {
      progressBar.style.width = '100%';
    }, 300);
  }
}

function animateLobbyProgress() {
  const progressBar = document.getElementById('lobby-progress');
  if (progressBar) {
    progressBar.style.width = '0%';
    setTimeout(() => {
      progressBar.style.width = '100%';
    }, 300);
  }
}

function animateGameProgress() {
  const progressBar = document.getElementById('game-progress');
  if (progressBar) {
    progressBar.style.width = '0%';
    setTimeout(() => {
      progressBar.style.width = '100%';
    }, 300);
  }
}

// Инициализация Telegram Web App
function initializeTelegramWebApp() {
  if (tg) {
    // Устанавливаем цвета темы
    document.documentElement.style.setProperty('--tg-theme-bg-color', tg.themeParams.bg_color || '#ffffff');
    document.documentElement.style.setProperty('--tg-theme-text-color', tg.themeParams.text_color || '#000000');
    document.documentElement.style.setProperty('--tg-theme-hint-color', tg.themeParams.hint_color || '#999999');
    document.documentElement.style.setProperty('--tg-theme-link-color', tg.themeParams.link_color || '#4361ee');
    document.documentElement.style.setProperty('--tg-theme-button-color', tg.themeParams.button_color || '#4361ee');
    document.documentElement.style.setProperty('--tg-theme-button-text-color', tg.themeParams.button_text_color || '#ffffff');
    
    // Обработчик изменения темы
    tg.onEvent('themeChanged', () => {
      const isDark = tg.colorScheme === 'dark';
      setTheme(isDark ? 'dark' : 'light');
    });
  }
}

// Обработчики событий
document.addEventListener('click', function(e) {
  // Обработка кликов по radio кнопкам
  if (e.target.classList.contains('radio-option')) {
    const input = e.target.querySelector('input');
    if (input) {
      input.checked = true;
    }
  }
});

// Обработка видимости страницы
document.addEventListener('visibilitychange', function() {
  if (!document.hidden && tg) {
    // Страница стала видимой
    tg.ready();
  }
});

// Обработка клавиши "Назад" в Telegram
if (tg) {
  tg.BackButton.onClick(() => {
    // В зависимости от текущего экрана, возвращаемся назад
    switch (gameState.screen) {
      case 'createLobby':
      case 'joinLobby':
        showWelcome();
        break;
      case 'taskSelection':
        showGame();
        break;
      case 'game':
        showLobby();
        break;
      case 'lobby':
        showWelcome();
        break;
      default:
        showWelcome();
    }
 });
  
  // Показываем кнопку "Назад" если не на главном экране
  if (gameState.screen !== 'welcome') {
    tg.BackButton.show();
  }
}