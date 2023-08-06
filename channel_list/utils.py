from channel_list.database import Session
from channel_list.models import CategoryModel


def create_categories():
    categories = [
        'Adulto',
        'Filmes e Séries',
        'Notícias',
        'Esportes',
        'Vendas',
        'Entretenimento',
        'Humor, Memes',
        'Outros'
    ]
    with Session() as session:
        for category in categories:
            session.add(CategoryModel(name=category))
        session.commit()
