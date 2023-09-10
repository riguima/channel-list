import asyncio
import os
from datetime import date, datetime, time
from random import sample
from threading import Thread
from time import sleep

import pyromod
from dotenv import load_dotenv
from pyrogram import filters
from pyrogram.client import Client
from pyrogram.types import CallbackQuery, Chat, Message
from sqlalchemy import select

from channel_list.config import config
from channel_list.database import Session
from channel_list.models import Category, Channel
from channel_list.utils import create_reply_markup

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
        config['messages']['START_MENU'].replace(
            '{minimum_members_count}', config['MINIMUM_MEMBERS_COUNT']
        ),
        reply_markup=create_reply_markup(
            {'Participar': {'callback_data': 'participate'}},
            {'Canais Participantes': {'callback_data': 'choose_category'}},
        ),
    )


@app.on_callback_query()
async def answer(client: Client, callback_query: CallbackQuery) -> None:
    actions = {
        'participate': participate,
        'choose_category': choose_category,
        'return': start,
    }
    await actions[callback_query.data](client, callback_query.message)


@app.on_callback_query(filters.regex('admin_code:.+'))
async def admin_code(client: Client, callback_query: CallbackQuery) -> None:
    chat_id, from_user_id, flag = callback_query.data.split(':').split('_')
    answer_message = await callback_query.message.chat.ask(
        'Digite o código de verificação de admin:'
    )
    if answer_message.text == config['ADMIN_VERIFICATION_CODE']:
        chat = await app.get_chat(int(chat_id))
        await send_confirmation_message(chat)
        await choose_category(int(chat_id), int(from_user_id), flag)
    else:
        await answer_message.reply(
            'Código inválido',
            reply_markup=create_reply_markup(
                {
                    'Digitar novamente': {
                        'callback_data': 'admin_code_{"_".join(data)}'
                    },
                    'Voltar': {'callback_data': 'return'},
                },
            ),
        )


@app.on_callback_query(filters.regex('add_channel:.+'))
async def add_channel(client: Client, callback_query: CallbackQuery) -> None:
    with Session() as session:
        category_id, chat_id = callback_query.data.split(':').split('_')
        category = session.get(Category, category_id)
        chat = await app.get_chat(chat_id)
        try:
            confirmation_message = await app.send_message(
                chat_id, 'Mensagem de confirmação'
            )
            await confirmation_message.delete()
            await callback_query.message.reply(
                (
                    f'🌐Seu Canal: {chat.title}\n\n• Link: {chat.invite_link}\n• D'
                    f'ata Adic.: {date.today().strftime("%d/%m/%Y")}\n• Categoria:'
                    f' {category.name}\n• Divulgando: ✅ Sim'
                ),
                reply_markup=create_reply_markup(
                    {
                        '🗣 Divulgando Canal: ✅ Sim': {
                            'url': f'http://t.me/{config["BOT_NAME"]}'
                        },
                        '#⃣ Categoria do Canal': {
                            'callback_data': f'change_category:{category_id}_{chat_id}'
                        },
                        'Voltar': {'callback_data': 'return'},
                    },
                ),
            )
            channel = Channel(
                url=chat.invite_link,
                chat_id=int(chat_id),
                title=chat.title,
                category=category,
            )
            session.add(channel)
            session.commit()
        except:
            await app.leave_chat(int(chat_id))
            await callback_query.message.reply(
                (
                    'Você não definiu todas as permissões necessárias para o b'
                    f'ot funcionar no canal {chat.title}, veja aqui as permiss'
                    'ões que o bot precisa para funcionar'
                ),
            )
            await callback_query.message.reply_photo(
                'permissions.jpg',
                reply_markup=create_reply_markup(
                    {'Voltar': {'callback_data': 'return'}}
                ),
            )


@app.on_callback_query(filters.regex('change_category:.+'))
async def change_category(
    client: Client, callback_query: CallbackQuery
) -> None:
    with Session() as session:
        category_id, chat_id = callback_query.data.split(':').split('_')
        query = select(Channel).where(Channel.chat_id == int(chat_id))
        model = session.scalars(query).first()
        category = session.get(Category, int(category_id))
        model.category = category
        session.commit()
        callback_query.message.reply(
            f'Seu canal agora é da categoria {category}'
        )
        await start(client, callback_query.message)


@app.on_chat_member_updated()
async def member_updated(_, update):
    minimum_members_count = int(config['MINIMUM_MEMBERS_COUNT'])
    try:
        members_count = await app.get_chat_members_count(update.chat.id)
    except:
        await app.send_message(
            update.old_chat_member.invited_by.id,
            (
                'Seu canal foi removido dos canais participantes, pois voc'
                'ê removeu o bot do seu canal '
            ),
            reply_markup=create_reply_markup(
                {'Voltar': {'callback_data': 'return'}}
            ),
        )
        with Session() as session:
            query = select(Channel).where(Channel.chat_id == update.chat.id)
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
                reply_markup=create_reply_markup(
                    {
                        'Digitar código': {
                            'callback_data': (
                                f'admin_code_{update.chat.id}_{update.from_user.id}'
                            ),
                        },
                        'Voltar': {'callback_data': 'return'},
                    },
                ),
            )
        else:
            with Session() as session:
                query = select(Channel).where(
                    Channel.chat_id == update.chat.id
                )
                model = session.scalars(query).first()
                if model is None:
                    await send_confirmation_message(update.chat)
                    await choose_category(
                        update.chat.id,
                        update.from_user.id,
                        'add',
                    )


async def send_confirmation_message(chat: Chat) -> None:
    await app.send_message(
        chat.id,
        (
            '👏 O bot é um administrador do canal e tem as permissões corretas'
            f'.\n\n👏 Parabéns, canal {chat.title} adicionado na lista.\n\nPre'
            'zamos pelo crescimento mútuo, enquanto você cresce também ajuda o'
            'utros canais a crescerem.'
        ),
        reply_markup=create_reply_markup(
            {
                'Configurar Meus Canais': {
                    'url': f'http://t.me/{config["BOT_NAME"]}'
                },
            },
        ),
    )


async def choose_category(chat_id: int, from_user_id: int, flag: str) -> None:
    with Session() as session:
        options = {}
        for model in session.scalars(select(Category)).all():
            options[model.name] = {
                'callback_data': f'{flag}:{model.id}_{chat_id}'
            }
        await app.send_message(
            from_user_id,
            'Escolha a categoria do seu canal:',
            reply_markup=create_reply_markup(options),
        )


async def participate(_, message: Message) -> None:
    minimum_members_count = int(config['MINIMUM_MEMBERS_COUNT'])
    await message.reply(
        f'Seu canal precisa ter pelo menos {minimum_members_count} membros:',
        reply_markup=create_reply_markup(
            {
                'Escolha um canal': {
                    'url': (
                        f'http://t.me/{config["BOT_NAME"]}?startchannel&'
                        'admin=post_messages+edit_messages+delete_message'
                        's+invite_users+pin_messages+manager_chat'
                    ),
                },
                'Voltar': {'callback_data': 'return'},
            }
        ),
    )


async def category_menu(_, message: Message) -> None:
    with Session() as session:
        options = {}
        for model in session.scalars(select(Category)).all():
            options[model.name] = {'callback_data': model.name}
        options['Voltar'] = {'callback_data': 'return'}
    await message.reply(
        'Escolha uma categoria:',
        reply_markup=create_reply_markup(options),
    )


async def channels_by_category(message: Message, category_id: int) -> None:
    with Session() as session:
        query = select(Channel).where(Channel.category_id == category_id)
        options = {}
        models = session.scalars(query).all()
        for model in sample(models, k=min(10, len(models))):
            options[model.title] = {'url': model.url}
        options['Voltar'] = {'callback_data': 'return'}
        await message.reply(
            'Canais participantes:',
            reply_markup=create_reply_markup(options),
        )


async def alert_channels():
    with Session() as session:
        query = select(Channel)
        models = session.scalars(query).all()
        for model in models:
            query = select(Channel).where(Channel.category == model.category)
            same_category = session.scalars(query).all()
            while True:
                channels = sample(
                    same_category,
                    k=min(30, len(same_category) - 1),
                )
                if model not in channels:
                    break
            options = {c.title: {'url': c.url} for c in channels}
            await app.send_message(
                model.chat_id,
                (
                    '👏 Lista de canais parceiros divulgada para mais de '
                    f'{len(models)} canais:\n\n👥 Lista para grupos: @divulgap'
                    'utaria_bot'
                ),
                reply_markup=create_reply_markup(options),
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
    Thread(target=alert_channels_callback).start()
    app.run()
