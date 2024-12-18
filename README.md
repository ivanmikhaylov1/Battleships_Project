# Battleships_Project
@Battleships_Project_bot

# Как разворачивать проект у себя на компьютере:
1. 8 сторочка: добавить API своего бота API_TOKEN = 'Ваш API'. Получить можно в боте @BotFather в телеграме.
2. Добавить таблицу запросом SQL:
CREATE TABLE user_statistics (
    user_id BIGINT PRIMARY KEY,
    moves_count INTEGER DEFAULT 0,
    wins_count INTEGER DEFAULT 0,
    board_size INTEGER DEFAULT 5
);
3. Установить библиотеки asyncpg, aiogram, asyncio:
   pip install asyncpg aiogram asyncpg
   pip install asyncpg aiogram aiogram
   pip install asyncpg aiogram asyncio
