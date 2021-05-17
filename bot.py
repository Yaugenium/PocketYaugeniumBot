import aiohttp
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor, markdown
import os

from yarl import URL
import json

api_key = os.environ['API_KEY']

bot = Bot(token=os.environ['TOKEN'])
dp = Dispatcher(bot)

tmdb_url = URL('https://www.themoviedb.org')

search_url = URL(
    f'https://api.themoviedb.org/3/search/multi?'
    f'api_key={api_key}'
    f'&language=ru'
    f'&include_adult=true'
)

find_url = URL('https://api.themoviedb.org')


@dp.message_handler(commands=['start'])
async def send_start(message: types.Message) -> None:
    await message.reply('Привет, к сожалению Евгений не может быть с тобой весь день, но может я смогу помочь?\n'
                        'Нажми /help чтобы познакомиться с функциональностью Карманного Евгениума!')


@dp.message_handler(commands=['help'])
async def send_help(message: types.Message) -> None:
    await message.reply('У меня есть для тебя пару команд: \n'
                        '/start - если захочешь услышать приветствие\n'
                        '/help - если потерял дар речи\n'
                        '/search - если хочешь послушать о фильме\n'
                        '/secret - очень секретно, мне нельзя об этом рассказывать\n')


@dp.message_handler(commands=['secret'])
async def send_secret(message: types.Message) -> None:
    await message.reply(markdown.hlink('Этого сообщения никогда не было!',
                                       'https://www.youtube.com/watch?v=dQw4w9WgXcQ'),
                        disable_web_page_preview=True, parse_mode='HTML')


@dp.message_handler(commands=['search'])
async def send_search(message: types.Message) -> None:
    if not len(message.text) > 8:
        await message.reply("Без названия я мало что расскажу...\n"
                            "Введи /search <название_фильма> и поболтаем")
        return

    async with aiohttp.ClientSession() as session:
        async with session.get(search_url.update_query({'query': message.text[8:]})) as resp:
            response = json.loads(await resp.text())

            if not response['total_results']:
                await message.reply('Упс, о таком не слышал...')
                return

            inline_keyboard = types.InlineKeyboardMarkup()
            results = sorted(filter(lambda x: x['media_type'] in ['movie', 'tv'], response['results']),
                             key=lambda x: -x['vote_average'])[:5]

            for index, movie in enumerate(results):
                title = movie['original_title'] if movie['media_type'] == 'movie' else movie['original_name'] + ' (TV)'
                date = movie['release_date'][:4] if movie['media_type'] == 'movie' else movie['first_air_date'][:4]
                button = types.InlineKeyboardButton(f"{title} ({date})",
                                                    callback_data=f"{movie['media_type']} {movie['id']}")

                inline_keyboard.add(button)

            await message.reply('О каком желаешь услышать?', reply_markup=inline_keyboard)


@dp.callback_query_handler()
async def process_callback_button(callback_query: types.CallbackQuery) -> None:
    await bot.answer_callback_query(callback_query.id)

    pos = callback_query.data.find(' ')
    media_type = callback_query.data[:pos]
    media_id = callback_query.data[pos + 1:]

    async with aiohttp.ClientSession() as session:
        async with session.get(find_url.with_path(f'/3/{media_type}/{media_id}').with_query(
                {'api_key': api_key, 'language': 'ru'})) as resp:
            result = json.loads(await resp.text())

            rating = result['vote_average'] if result['vote_count'] else 'неизвестен'
            overview = result['overview'] if result['overview'] else 'отсутствует'

            await bot.send_photo(callback_query.from_user.id, tmdb_url.with_path(
                '/t/p/w600_and_h900_bestv2' + result['poster_path']).human_repr(),
                                 f"Рейтинг: {rating}\n"
                                 f"Описание: {overview}")

            link = markdown.hlink('прошу', tmdb_url.with_path(
                f"/{media_type}"
                f"/{result['id']}"
                f"/watch").with_query({'locale': 'RU'}).human_repr())

            await bot.send_message(callback_query.from_user.id, 'Если захочешь посмотреть, то ' + link,
                                   disable_web_page_preview=True, parse_mode='HTML')


@dp.message_handler()
async def send_hint(message: types.Message) -> None:
    await message.reply('Прости, я не знаю такой команды,\n'
                        '/help расскажет что я умею')


if __name__ == '__main__':
    executor.start_polling(dp)
