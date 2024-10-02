import aws_cdk as core
import aws_cdk.assertions as assertions

from telegram_bot.telegram_bot_stack import TelegramBotStack


# example tests. To run these tests, uncomment this file along with the example
# resource in telegram_bot/telegram_bot_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = TelegramBotStack(app, "telegram-bot")
    assertions.Template.from_stack(stack)


#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
