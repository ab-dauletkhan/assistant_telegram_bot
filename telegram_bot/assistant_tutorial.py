from openai import OpenAI
import shelve
from dotenv import dotenv_values, find_dotenv
import os
import time
import logging
from telegram import Update, User
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes

env_path = find_dotenv()
config = dotenv_values(env_path)

client = OpenAI(api_key=config['OPENAI_API_KEY'])


# --------------------------------------------------------------
# Upload file
# --------------------------------------------------------------
# def upload_file(path):
#     # Upload a file with an "assistants" purpose
#     file = client.files.create(file=open(path, "rb"), purpose="assistants")
#     return file


# file = upload_file("")


# --------------------------------------------------------------
# Create assistant
# --------------------------------------------------------------
# def create_assistant(file):
#     """
#     You currently cannot set the temperature for Assistant via the API.
#     """
#     assistant = client.beta.assistants.create(
#         name="",
#         instructions="",
#         tools=[{"type": "retrieval"}],
#         model="gpt-4-1106-preview",
#     )
#     return assistant


# assistant = create_assistant(file)


# --------------------------------------------------------------
# Thread management
# --------------------------------------------------------------
def check_if_thread_exists(tg_id):
    with shelve.open("threads_db") as threads_shelf:
        return threads_shelf.get(tg_id, None)


def store_thread(tg_id, thread_id):
    with shelve.open("threads_db", writeback=True) as threads_shelf:
        threads_shelf[tg_id] = thread_id


# --------------------------------------------------------------
# Generate response
# --------------------------------------------------------------
def generate_response(message_body, tg_id_int, name):
    # Convert int to str to encode
    tg_id = str(tg_id_int)
    # Check if there is already a thread_id for the tg_id
    thread_id = check_if_thread_exists(tg_id)

    # If a thread doesn't exist, create one and store it
    if thread_id is None:
        logging.info(f"Creating new thread for {name} with tg_id {tg_id}")
        thread = client.beta.threads.create()
        store_thread(tg_id, thread.id)
        thread_id = thread.id

    # Otherwise, retrieve the existing thread
    else:
        logging.info(f"Retrieving existing thread for {name} with tg_id {tg_id}")
        thread = client.beta.threads.retrieve(thread_id)

    # Add message to thread
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message_body,
    )

    # Run the assistant and get the new message
    new_message = run_assistant(thread)
    logging.info(f"To {name}:", new_message)
    return new_message


# --------------------------------------------------------------
# Run assistant
# --------------------------------------------------------------
def run_assistant(thread):
    # Retrieve the Assistant
    assistant = client.beta.assistants.retrieve(config['ASSISTANT_ID'])

    # Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )

    # Wait for completion
    while run.status != "completed":
        # Be nice to the API
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

    # Retrieve the Messages
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    new_message = messages.data[0].content[0].text.value
    logging.info(f"Generated message: {new_message}")
    return new_message


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me! Write any concerns")

async def assistant_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    # print(user['username'], user['id'])
    request = update.message.text
    response = generate_response(request, user['id'], user['username'])
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)


if __name__ == '__main__':
    application = ApplicationBuilder().token(config['TOKEN']).build()
    
    start_handler = CommandHandler('start', start)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), assistant_answer)
    
    application.add_handler(start_handler)
    application.add_handler(message_handler)

    application.run_polling()


# --------------------------------------------------------------
# Test assistant
# --------------------------------------------------------------

# new_message = generate_response("What's the check in time?", "123", "John")

# new_message = generate_response("What's the pin for the lockbox?", "456", "Sarah")

# new_message = generate_response("What was my previous question?", "123", "John")

# new_message = generate_response("What was my previous question?", "456", "Sarah")