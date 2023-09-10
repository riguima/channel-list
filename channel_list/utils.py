from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def create_reply_markup(options: dict) -> None:
    buttons = []
    keys = list(options.keys())
    for c in range(0, len(keys), step=2):
        try:
            buttons.append(
                [
                    InlineKeyboardButton(keys[c], **options[keys[c]]),
                    InlineKeyboardButton(keys[c + 1], **options[keys[c + 1]]),
                ]
            )
        except IndexError:
            buttons.append([InlineKeyboardButton(keys[c], **options[keys[c]])])
    return InlineKeyboardMarkup(buttons)
