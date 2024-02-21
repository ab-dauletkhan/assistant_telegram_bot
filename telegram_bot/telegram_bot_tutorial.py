import os

from openai import OpenAI
import shelve
import time

env_path = find_dotenv()
config = dotenv_values(env_path)
#print(config)

import logging
from telegram import Update, User
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes

import time
from openai import OpenAI


client = OpenAI(api_key=config['OPENAI_API_KEY'])

# assistant = client.beta.assistants.create(
#     name="Chat bot assistant",
#     instructions="You are a personal assistant. You have to provide specific answers according to users problem. For now, you can just answer random answers for any question, later I will supply with database.",
#     tools=[{"type": "code_interpreter"}],
#     model="gpt-4-turbo-preview"
# )

def generate_response(message_body):
    thread = client.beta.threads.create()
    thread_id = thread.id

    message = client.beta.threads.messages.create(
        thread_id = thread_id,
        role = 'user',
        content = message_body
    )

def run_assistant():
    assistant = client.beta.assistants.retrieve(config['ASSISTANT_ID'])
    thread = client.beta.threads.retrieve()

    run = client.beta.threads.runs.create(
        thread_id = thread.id,
        assistant_id = assistant.id,
    )

    while run.status != "completed":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        print(f"Run status: {run.status}")
        time.sleep(1)
    else:
        print("Run completed!")

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    latest_message = messages.data[0].content[0].text.value
    logging.info(f'Generated message: {latest_message}')
    return latest_message


# response = run_assistant()


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me! Write any concerns")

# async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

async def assistant_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    # print(user['username'], user['id'])
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)
    # thread = client.beta.threads.create()


if __name__ == '__main__':
    application = ApplicationBuilder().token(config['TOKEN']).build()
    
    start_handler = CommandHandler('start', start)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), assistant_answer)
    
    application.add_handler(start_handler)
    application.add_handler(message_handler)

    application.run_polling()