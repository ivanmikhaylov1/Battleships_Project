import asyncpg
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import random
from aiogram.dispatcher.router import Router

API_TOKEN = '7600619339:AAHpolJFlzen68FaS6_5OipUmzZH8RRkyRM'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

DB_CONFIG = {
    "user": "user",
    "password": "password",
    "database": "database",
    "host": "localhost",
    "port": 5432
}

async def create_db_connection():
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        return None

async def get_user_statistics(user_id):
    conn = await create_db_connection()
    if not conn:
        return None
    try:
        user_stats = await conn.fetchrow('SELECT * FROM user_statistics WHERE user_id = $1', user_id)
        return user_stats
    finally:
        await conn.close()

async def update_user_statistics(user_id, moves_count, wins_count, board_size):
    conn = await create_db_connection()
    if not conn:
        raise ConnectionError("Не удалось подключиться к базе данных.")
    try:
        await conn.execute('''
            INSERT INTO user_statistics (user_id, moves_count, wins_count, board_size)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                moves_count = EXCLUDED.moves_count, 
                wins_count = EXCLUDED.wins_count,
                board_size = EXCLUDED.board_size
        ''', user_id, moves_count, wins_count, board_size)
    finally:
        await conn.close()

async def increment_win_count(user_id):
    stats = await get_user_statistics(user_id)
    if stats:
        wins_count = stats['wins_count'] + 1
        moves_count = stats['moves_count']
        board_size = stats['board_size']
    else:
        wins_count = 1
        moves_count = 0
        board_size = 5
    await update_user_statistics(user_id, moves_count, wins_count, board_size)

async def increment_move_count(user_id):
    stats = await get_user_statistics(user_id)
    if stats:
        moves_count = stats['moves_count'] + 1
        wins_count = stats['wins_count']
        board_size = stats['board_size']
    else:
        moves_count = 1
        wins_count = 0
        board_size = 5
    await update_user_statistics(user_id, moves_count, wins_count, board_size)

async def generate_statistics_menu(user_id):
    stats = await get_user_statistics(user_id)
    if stats:
        text = f"Статистика пользователя {user_id}:\n" \
               f"Количество побед: {stats['wins_count']}\n" \
               f"Количество ходов: {stats['moves_count']}\n" \
               f"Размер доски: {stats['board_size']}x{stats['board_size']}"
    else:
        text = "Нет данных о статистике для этого пользователя."
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Показать статистику", callback_data="show_stats")]
    ])
    return text, keyboard

async def show_statistics(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    stats_text, keyboard = await generate_statistics_menu(user_id)
    if callback_query.message.text != stats_text:
      await callback_query.message.edit_text(stats_text, reply_markup=keyboard)

user_settings = {}
user_game_data = {}
shot_cells = set()
shots_bot1 = set()
shots_bot2 = set()
VISUAL_MODES = {
  "default": "Стандартный режим",
  "cats": "Режим с котиками"
}

def generate_visual_mode_menu():
  keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
      InlineKeyboardButton(text="Стандартный режим", callback_data="set_visual:default"),
      InlineKeyboardButton(text="Режим с котами", callback_data="set_visual:cats")
    ]
  ])
  return keyboard

def generate_mode_menu():
    button1 = InlineKeyboardButton(text="Игрок против бота", callback_data="mode_1")
    button2 = InlineKeyboardButton(text="Бот против Бота", callback_data="mode_2")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button1, button2]])
    return keyboard

def generate_settings_menu():
  keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
      InlineKeyboardButton(text="Размер поля 5x5", callback_data="set_size:5"),
      InlineKeyboardButton(text="Размер поля 7x7", callback_data="set_size:7")
    ],
    [
      InlineKeyboardButton(text="5 кораблей", callback_data="set_ships:5"),
      InlineKeyboardButton(text="7 кораблей", callback_data="set_ships:7"),
      InlineKeyboardButton(text="9 кораблей", callback_data="set_ships:9"),
      InlineKeyboardButton(text="11 кораблей", callback_data="set_ships:11")
    ],
    [
      InlineKeyboardButton(text="Выбрать визуальный режим", callback_data="choose_visual_mode"),
      InlineKeyboardButton(text="Выбрать режим игры", callback_data="choose_mode"),
      InlineKeyboardButton(text="Топ игроков", callback_data="show_leaderboard")
    ]
  ])
  return keyboard

async def get_leaderboard():
  conn = await create_db_connection()
  if conn:
    leaderboard = await conn.fetch(
      'SELECT user_id, wins_count FROM user_statistics ORDER BY wins_count DESC LIMIT 10'
    )
    await conn.close()
    return leaderboard
  else:
    raise ConnectionError("Failed to connect to the database.")

async def show_leaderboard(callback_query: types.CallbackQuery):
  leaderboard = await get_leaderboard()
  if leaderboard:
    leaderboard_text = "🏆 Топ-10 игроков:\n\n"
    for rank, record in enumerate(leaderboard, start=1):
      leaderboard_text += f"{rank}. Игрок {record['user_id']} - {record['wins_count']} побед\n"
  else:
    leaderboard_text = "Таблица лидеров пуста."
  await callback_query.message.edit_text(
    leaderboard_text
  )

async def choose_visual_mode(callback_query: types.CallbackQuery):
  await callback_query.message.edit_text(
    "Выберите визуальный режим:",
    reply_markup=generate_visual_mode_menu()
  )

async def set_visual_mode(callback_query: types.CallbackQuery):
  user_id = callback_query.from_user.id
  visual_mode = callback_query.data.split(":")[1]
  user_settings[user_id] = user_settings.get(user_id, {})
  user_settings[user_id]["visual_mode"] = visual_mode
  await callback_query.answer(f"Визуальный режим установлен: {VISUAL_MODES[visual_mode]}")

def generate_board(size, visual_mode="default"):
  if visual_mode == "cats":
    return [['📦' for _ in range(size)] for _ in range(size)]
  else:
    return [['⬜️' for _ in range(size)] for _ in range(size)]

def place_ships(board_size, ship_count):
  ships = set()
  while len(ships) < ship_count:
    x, y = random.randint(0, board_size - 1), random.randint(0, board_size - 1)
    ships.add((x, y))
  return ships

def generate_keyboard(board):
  buttons = []
  for i, row in enumerate(board):
    row_buttons = []
    for j, cell in enumerate(row):
      button = InlineKeyboardButton(text=str(cell), callback_data=f'cell_{i}_{j}')
      row_buttons.append(button)
    buttons.append(row_buttons)

  keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
  return keyboard


async def send_welcome(message: types.Message):
  await message.reply(
    "Это игра Морской бой.\n"
    "Ты можешь выбрать режим игры: Игрок против Бота или Бот против Бота.\n"
    "Также доступны настройки поля и количества кораблей.",
    reply_markup=generate_settings_menu()
  )


async def choose_mode(callback_query: types.CallbackQuery):
  await callback_query.message.edit_text(
    "Выберите режим игры:",
    reply_markup=generate_mode_menu()
  )

async def set_game_mode(callback_query: types.CallbackQuery):
  user_id = callback_query.from_user.id
  visual_mode = user_settings.get(user_id, {}).get("visual_mode", "default")
  if ":" in callback_query.data:
    mode = callback_query.data.split(":")[1]
  else:
    mode = callback_query.data
  user_settings[callback_query.from_user.id] = user_settings.get(callback_query.from_user.id, {})
  user_settings[callback_query.from_user.id]["mode"] = mode
  if mode == "mode_1":
    await callback_query.answer("Выбран режим 'Игрок против Бота'")
    await start_game(callback_query)
  elif mode == "mode_2":
    await callback_query.answer("Выбран режим 'Бот против Бота'")
    await start_bot_vs_bot(callback_query, visual_mode)

async def set_board_size(callback_query: types.CallbackQuery):
  size = int(callback_query.data.split(":")[1])
  user_settings[callback_query.from_user.id] = user_settings.get(callback_query.from_user.id, {})
  user_settings[callback_query.from_user.id]["board_size"] = size
  await callback_query.answer(f"Размер поля установлен на {size}x{size}")

async def set_ship_count(callback_query: types.CallbackQuery):
  ships = int(callback_query.data.split(":")[1])
  user_settings[callback_query.from_user.id] = user_settings.get(callback_query.from_user.id, {})
  user_settings[callback_query.from_user.id]["ship_count"] = ships
  await callback_query.answer(f"Количество кораблей установлено на {ships}")

async def start_game(callback_query: types.CallbackQuery):
  user_id = callback_query.from_user.id
  settings = user_settings.get(user_id, {})
  board_size = settings.get("board_size", 5)
  ship_count = settings.get("ship_count", 5)
  visual_mode = settings.get("visual_mode", "default")
  board = generate_board(board_size, visual_mode)
  ships = place_ships(board_size, ship_count)
  user_game_data[user_id] = {
    "board": board,
    "ships": ships,
    "remaining_ships": len(ships)
  }
  await callback_query.message.edit_reply_markup(
    reply_markup=generate_keyboard(board)
  )

async def start_player_vs_bot(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    settings = user_settings.get(user_id, {})
    board_size = settings.get("board_size", 5)
    ship_count = settings.get("ship_count", 3)

    board = generate_board(board_size)
    ships = place_ships(board_size, ship_count)

    user_game_data[user_id] = {
        "board": board,
        "ships": ships,
        "remaining_ships": ship_count
    }

    await callback_query.message.edit_text(
        f"Ты начал игру против бота! Корабли на поле: {ship_count}\n\n{generate_board_text(board)}",
        reply_markup=generate_keyboard(board)
    )

async def start_bot_vs_bot(callback_query: types.CallbackQuery, visual_mode="default"):
  smile = '🐈' if visual_mode == "cats" else '🔥'
  user_id = callback_query.from_user.id
  settings = user_settings.get(user_id, {})
  board_size = settings.get("board_size", 5)
  ship_count = settings.get("ship_count", 3)
  visual_mode = settings.get("visual_mode", "default")

  bot1_board = generate_board(board_size, visual_mode)
  bot2_board = generate_board(board_size, visual_mode)

  bot1_ships = place_ships(board_size, ship_count)
  bot2_ships = place_ships(board_size, ship_count)
  k = 0
  while bot1_ships and bot2_ships:
    k += 1
    x, y = random.randint(0, board_size - 1), random.randint(0, board_size - 1)
    while (x, y) in shots_bot1:
      x, y = random.randint(0, board_size - 1), random.randint(0, board_size - 1)
    if (x, y) in bot2_ships:
      bot2_ships.remove((x, y))
      bot2_board[x][y] = smile
    else:
      bot2_board[x][y] = '❌'
    shots_bot1.add((x, y))
    x, y = random.randint(0, board_size - 1), random.randint(0, board_size - 1)
    while (x, y) in shots_bot2:
      x, y = random.randint(0, board_size - 1), random.randint(0, board_size - 1)
    if (x, y) in bot1_ships:
      bot1_ships.remove((x, y))
      bot1_board[x][y] = smile
    else:
      bot1_board[x][y] = '❌'
    shots_bot2.add((x, y))
    await callback_query.message.edit_text(
      f"Бот 1 стреляет:\n{generate_board_text(bot2_board)}\n\n"
      f"Бот 2 стреляет:\n{generate_board_text(bot1_board)}"
    )
    await asyncio.sleep(0.3)
  winner = "Бот 1" if bot2_ships == 0 else "Бот 2"
  await callback_query.message.edit_text(f"Игра окончена! Победил {winner}! 🎉 за {k} ходов")

def generate_board_text(board):
  return "\n".join(" ".join(row) for row in board)

async def update_shot_button(callback_query: types.CallbackQuery, x: int, y: int, new_text: str):
  buttons = callback_query.message.reply_markup.inline_keyboard
  buttons[x][y].text = new_text
  updated_keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
  await callback_query.message.edit_reply_markup(reply_markup=updated_keyboard)

async def handle_shoot(callback_query: types.CallbackQuery):
  user_id = callback_query.from_user.id
  visual_mode = user_settings.get(user_id, {}).get("visual_mode", "default")
  smile = '🐈' if visual_mode == "cats" else '🔥'
  if user_id not in user_game_data:
    await callback_query.answer("Начни новую игру с /start!")
    return
  _, x, y = callback_query.data.split('_')
  x, y = int(x), int(y)
  game = user_game_data[user_id]
  board = game["board"]
  ships = game["ships"]
  await increment_move_count(user_id)
  if (x, y) in shot_cells:
    await callback_query.answer("Выстрел уже был!")
    return
  shot_cells.add((x, y))
  if (x, y) in ships:
    board[x][y] = smile
    ships.remove((x, y))
    game["remaining_ships"] -= 1
    await callback_query.answer("Попал")
    await update_shot_button(callback_query, x, y, smile)
  else:
    board[x][y] = '❌'
    await callback_query.answer("Мимо")
    await update_shot_button(callback_query, x, y, '❌')
  updated_message = f"Осталось кораблей: {game['remaining_ships']}"
  if game["remaining_ships"] == 0:
    await increment_win_count(user_id)
    shot_cells.clear()
    final_message = (
      "Ты потопил все корабли! 🎉\n\n"
      f"{generate_board_text(board)}\n\n"
      "Начни новую игру с /start."
    )
    await callback_query.message.edit_text(
      final_message,
      reply_markup=callback_query.message.reply_markup
    )
    del user_game_data[user_id]
  else:
    await callback_query.message.edit_text(
      updated_message,
      reply_markup=generate_keyboard(board)
    )

async def main():
  router = Router()
  router.message.register(send_welcome, F.text == "/start")
  router.callback_query.register(choose_mode, F.data == "choose_mode")
  router.callback_query.register(set_game_mode, F.data.startswith("mode"))
  router.callback_query.register(set_board_size, F.data.startswith("set_size"))
  router.callback_query.register(set_ship_count, F.data.startswith("set_ships"))
  router.callback_query.register(start_player_vs_bot, F.data == "player_vs_bot")
  router.callback_query.register(handle_shoot, F.data.startswith("cell"))
  router.callback_query.register(choose_visual_mode, F.data == "choose_visual_mode")
  router.callback_query.register(set_visual_mode, F.data.startswith("set_visual"))
  router.callback_query.register(show_leaderboard, F.data == "show_leaderboard")
  dp.include_router(router)
  await dp.start_polling(bot)

if __name__ == '__main__':
  asyncio.run(main())
