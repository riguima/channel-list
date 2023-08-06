import os
from datetime import datetime, time
from time import sleep

from dotenv import load_dotenv
from pyrogram.client import Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import filters
from sqlalchemy import select

from channel_list.models import ChannelModel, CategoryModel
from channel_list.database import Session
from channel_list.utils import create_categories

load_dotenv()


app = Client(
    os.environ['BOT_NAME'],
    api_id=os.environ['API_ID'],
    api_hash=os.environ['API_HASH'],
    bot_token=os.environ['BOT_TOKEN'],
)


@app.on_message(filters.command('start'))
async def start(_, message):
    await message.reply(
        (
            '😃 Partícipe da nossa lista de divulgação de grupos de putaria e '
            'ganhe membros para o seu grupo!\n👑Esse bot pertence ao @grupospo'
            'rnoputariaacelerada\n☝️ Somos a única plataforma de divulgações/pa'
            'rceria adultas 100% automatizada do Telegram.'
        ),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        'Participar',
                        callback_data='participate',
                    ),
                ],
                [
                    InlineKeyboardButton(
                        'Canais Participantes',
                        callback_data='channels',
                    ),
                ],
            ],
        ),
    )


@app.on_callback_query()
async def answer(client, callback_query):
    actions = {
        'participate': participate,
        'channels': channels,
        'return': start,
    }
    if callback_query.data not in actions:
        with Session() as session:
            query = select(CategoryModel).where(
                CategoryModel.name == callback_query.data
            )
            model = session.scalars(query).first()
            await channels_by_category(callback_query.message, model.name)
    else:
        await actions[callback_query.data](client, callback_query.message)


async def participate(_, message):
    await message.reply(
        'Seu canal precisa ter pelo menos 100 membros:',
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        'Escolha um canal',
                        url=(
                            'http://t.me/riguima_channel_list_bot?startchannel'
                            '&admin=post_messages+edit_messages+delete_message'
                            's+invite_users+pin_messages+manager_chat'
                        ),
                    )
                ],
            ],
        ),
    )


async def channels(_, message):
    with Session() as session:
        query = select(CategoryModel)
        options = []
        for model in session.scalars(query).all():
            options.append(
                [InlineKeyboardButton(model.name, callback_data=model.name)]
            )
        options.append(
            [InlineKeyboardButton('Voltar', callback_data='return')]
        )
    await message.reply(
        'Escolha uma categoria:',
        reply_markup=InlineKeyboardMarkup(options),
    )


async def channels_by_category(message, category):
    with Session() as session:
        query = select(ChannelModel).join(CategoryModel).where(
            CategoryModel.name == category
        )
        options = []
        for model in session.scalars(query).all():
            options.append([InlineKeyboardButton(model.name, url=model.url)])
        options.append(
            [InlineKeyboardButton('Voltar', callback_data='return')]
        )
    await message.reply(
        'Canais participantes:',
        reply_markup=InlineKeyboardMarkup(options),
    )


async def alert_channels():
    await app.send_message('riguima', 'Oi')


async def main():
    await app.start()
    times = [time(hour=0), time(hour=18), time(hour=9)]
    while True:
        for t in times:
            now = datetime.now().time()
            if now.hour == t.hour and now.minute == t.minute:
                await alert_channels()
        sleep(60)
    await app.stop()


if __name__ == '__main__':
    with Session() as session:
        query = select(CategoryModel)
        if not session.scalars(query).all():
            create_categories()
    app.run(main())
