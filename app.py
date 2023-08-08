import asyncio
import os
from datetime import datetime, time, date
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
            'Antes de tudo...\n\n• O seu canal deve ter uma quantidade mínima '
            f'de {os.environ["MINIMUM_MEMBERS_COUNT"]} membros para participar'
            ' da lista.\n• Somente o CRIADOR do canal poderá adicionar e admin'
            'istrar o canal usando esse bot.\n• O canal precisa ser ativo, can'
            'ais inativos são removido da lista.\n\nComo participar:\n\n👌 Par'
            'a ter o seu canal divulgado é bem simples, apenas adicione este b'
            'ot como um dos administradores do seu canal e dê as permissões qu'
            'e ele precisa, saiba das permissões nescessárias aqui. https://t.'
            'me/divulgaputariabot'
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
    if 'admin_code' in callback_query.data:
        data = callback_query.data.split('_')[2:]
        answer_message = await callback_query.message.chat.ask(
            'Digite o código de verificação de admin:'
        )
        if answer_message.text == os.environ['ADMIN_VERIFICATION_CODE']:
            await choose_category(int(data[0]), int(data[1]), data[2])
        else:
            await answer_message.reply(
                'Código inválido',
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                'Digitar novamente',
                                callback_data=f'admin_code_{"_".join(data)}',
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                'Voltar',
                                callback_data='return',
                            ),
                        ],
                    ],
                ),
            )
    elif callback_query.data not in actions:
        with Session() as session:
            data = callback_query.data.split('_')
            query = select(CategoryModel).where(CategoryModel.name == data[0])
            model = session.scalars(query).first()
            if data[-1] == 'add':
                await add_channel(
                    callback_query.message, model.name, int(data[1])
                )
            elif data[-1] == 'change':
                await change_category(
                    callback_query.message, model.name, int(data[1])
                )
            else:
                await channels_by_category(callback_query.message, model.name)
    else:
        await actions[callback_query.data](client, callback_query.message)


@app.on_chat_member_updated()
async def member_updated(_, update):
    minimum_members_count = int(os.environ['MINIMUM_MEMBERS_COUNT'])
    try:
        members_count = await app.get_chat_members_count(update.chat.id)
    except:
        await app.send_message(
            update.old_chat_member.invited_by.id,
            (
                'Seu canal foi removido dos canais participantes, pois voc'
                'ê removeu o bot do seu canal '
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton('Voltar', callback_data='return')],
                ],
            ),
        )
        with Session() as session:
            query = select(ChannelModel).where(
                ChannelModel.chat_id == update.chat.id
            )
            model = session.scalars(query).first()
            session.delete(model)
            session.commit()
    else:
        if members_count < minimum_members_count:
            await app.send_message(
                update.from_user.id,
                (
                    'Você não pode adicionar um canal com menos de '
                    f'{minimum_members_count} membros por não ser um admin'
                    ', caso seja um admin coloque o código de admin'
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                'Digitar código',
                                callback_data=(
                                    f'admin_code_{update.chat.id}_'
                                    f'{update.from_user.id}_add'
                                ),
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                'Voltar',
                                callback_data='return',
                            ),
                        ],
                    ],
                )
            )
        else:
            with Session() as session:
                query = select(ChannelModel).where(ChannelModel.chat_id == update.chat.id)
                model = session.scalars(query).first()
                if model is None:
                    await choose_category(update.chat.id, update.from_user.id, 'add')


async def choose_category(chat_id, from_user_id, flag):
    with Session() as session:
        query = select(CategoryModel)
        options = []
        for model in session.scalars(query).all():
            options.append(
                [
                    InlineKeyboardButton(
                        model.name,
                        callback_data=f'{model.name}_{chat_id}_{flag}',
                    )
                ]
            )
        await app.send_message(
            from_user_id,
            'Escolha a categoria do seu canal:',
            reply_markup=InlineKeyboardMarkup(options),
        )


async def add_channel(message, category, chat_id):
    chat = await app.get_chat(chat_id)
    try:
        await app.send_message(
            chat_id,
            (
                '👏 O bot é um administrador do canal e tem as permissões '
                f'corretas.\n\n👏 Parabéns, canal {chat.title} adicionado '
                'na lista.\n\nPrezamos pelo crescimento mútuo, enquanto vo'
                'cê cresce também ajuda outros canais a crescerem.'
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            'Configurar Meus Canais',
                            url=f'http://t.me/{os.environ["BOT_NAME"]}',
                        ),
                    ],
                ],
            ),
        )
        await message.reply(
            (
                f'🌐Seu Canal: {chat.title}\n\n• Link: {chat.invite_link}\n• D'
                f'ata Adic.: {date.today().strftime("%d/%m/%Y")}\n• Categoria:'
                f' {category}\n• Divulgando: ✅ Sim'
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            '🗣 Divulgando Canal: ✅ Sim',
                            url=f'http://t.me/{os.environ["BOT_NAME"]}',
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            '#⃣ Categoria do Canal',
                            callback_data=f'{category}_{chat_id}_change',
                        ),
                    ],
                    [
                        InlineKeyboardButton('Voltar', callback_data='return'),
                    ],
                ],
            ),
        )
        with Session() as session:
            query = select(CategoryModel).where(CategoryModel.name == category)
            category = session.scalars(query).first()
            channel = ChannelModel(
                url=chat.invite_link,
                chat_id=int(chat_id),
                title=chat.title,
                category=category,
            )
            session.add(channel)
            session.commit()
    except:
        await app.leave_chat(int(chat_id))
        await message.reply(
            (
                'Você não definiu todas as permissões necessárias para o b'
                f'ot funcionar no canal {chat.title}, veja aqui as permiss'
                'ões que o bot precisa para funcionar'
            ),
        )
        await message.reply_photo(
            'permissions.jpg',
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            'Voltar',
                            callback_data='return',
                        ),
                    ],
                ],
            ),
        )


async def change_category(message, category, chat_id):
    with Session() as session:
        query = select(ChannelModel).where(ChannelModel.chat_id == chat_id)
        model = session.scalars(query).first()
        model.category = category
        session.commit()
        message.reply(f'Seu canal agora é da categoria {category}')
        await start(None, message)


async def participate(_, message):
    minimum_members_count = int(os.environ['MINIMUM_MEMBERS_COUNT'])
    await message.reply(
        f'Seu canal precisa ter pelo menos {minimum_members_count} membros:',
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        'Escolha um canal',
                        url=(
                            f'http://t.me/{os.environ["BOT_NAME"]}?startchannel'
                            '&admin=post_messages+edit_messages+delete_message'
                            's+invite_users+pin_messages+manager_chat'
                        ),
                    )
                ],
                [InlineKeyboardButton('Voltar', callback_data='return')],
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
        models = session.scalars(query).all()
        for model in sample(models, k=min(10, len(models))):
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
            query = select(ChannelModel).where(
                ChannelModel.category == model.category
            )
            same_category = session.scalars(query).all()
            while True:
                channels = sample(
                    same_category,
                    k=min(30, len(same_category) - 1),
                )
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
                    'utaria_bot'
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
