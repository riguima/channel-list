import asyncio
import os
from datetime import datetime, time
from random import sample
from time import sleep
from threading import Thread

from dotenv import load_dotenv
import pyromod
from pyrogram.client import Client
from pyrogram.raw.functions.messages import GetAllChats
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
            data = callback_query.data.split('_')
            query = select(CategoryModel).where(CategoryModel.name == data[0])
            model = session.scalars(query).first()
            if len(data) == 2:
                await add_channel(
                    callback_query.message, model.name, int(data[1])
                )
            else:
                await channels_by_category(callback_query.message, model.name)
    else:
        await actions[callback_query.data](client, callback_query.message)


@app.on_chat_member_updated()
async def member_updated(_, update):
    with Session() as session:
        query = select(CategoryModel)
        options = []
        for model in session.scalars(query).all():
            options.append(
                [
                    InlineKeyboardButton(
                        model.name,
                        callback_data=f'{model.name}_{update.chat.id}',
                    )
                ]
            )
        await app.send_message(
            update.from_user.id,
            'Escolha a categoria do seu canal:',
            reply_markup=InlineKeyboardMarkup(options),
        )


async def add_channel(message, category, chat_id):
    with Session() as session:
        query = select(CategoryModel).where(CategoryModel.name == category)
        chat = await app.get_chat(chat_id)
        category = session.scalars(query).first()
        channel = ChannelModel(
            url=f'http://t.me/{chat.username}',
            chat_id=int(chat_id),
            title=chat.title,
            category=category,
        )
        session.add(channel)
        session.commit()
        await message.reply('Canal adicionado')
        await start(None, message)


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
            options.append([InlineKeyboardButton(model.title, url=model.url)])
        options.append(
            [InlineKeyboardButton('Voltar', callback_data='return')]
        )
    await message.reply(
        'Canais participantes:',
        reply_markup=InlineKeyboardMarkup(options),
    )


async def alert_channels():
    with Session() as session:
        query = select(ChannelModel)
        models = session.scalars(query).all()
        for model in models:
            while True:
                channels = sample(models, k=min(30, len(models) - 1))
                if model not in channels:
                    break
            options = [
                [InlineKeyboardButton(c.title, url=c.url)]
                for c in channels
            ]
            await app.send_message(
                model.chat_id,
                (
                    '👏 Lista de canais parceiros divulgada para mais de '
                    f'{len(models)} canais:\n\n👥 Lista para grupos: @divulgap'
                    'utaria'
                ),
                reply_markup=InlineKeyboardMarkup(options),
            )


def alert_channels_callback():
    times = [time(hour=0), time(hour=18), time(hour=9)]
    while True:
        for t in times:
            now = datetime.now().time()
            if now.hour == t.hour and now.minute == t.minute:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(alert_channels())
                loop.close()
        sleep(60)


if __name__ == '__main__':
    with Session() as session:
        query = select(CategoryModel)
        if not session.scalars(query).all():
            create_categories()
    Thread(target=alert_channels_callback).start()
    app.run()
