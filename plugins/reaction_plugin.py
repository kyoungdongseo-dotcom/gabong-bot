from telegram.ext import MessageReactionHandler
from handlers.reaction_handler import handle_reaction


def register(app, config):
    app.add_handler(MessageReactionHandler(handle_reaction))
