#!/usr/bin/env python3
import os

import aws_cdk as cdk

from telegram_bot.telegram_bot_stack import TelegramBotStack


app = cdk.App()
TelegramBotStack(
    app,
    "TelegramBotStack",
)

app.synth()
