# Gym Class Scheduler Bot 🤖💪

This project is a Telegram bot that helps you book your gym classes in advance. You simply send a message to the bot to schedule your class, and the bot takes care of booking it for you automatically 24 hours before it starts. All powered by AWS Lambda and EventBridge (cron jobs). 🏋️‍♂️
## How It Works

1. **Telegram Bot:** You chat with the bot to schedule your gym classes.
2. **AWS Lambda (Webhook Handler):** This handles incoming messages from Telegram and sets up the schedule as EventBridge rules.
3. **AWS EventBridge (Cron Jobs):** EventBridge rules are created to trigger the booking exactly 24 hours before your class starts.
4. **AWS Lambda (Booking Handler):** Once the scheduled time hits, this Lambda function automatically books your class. 


## Getting Started 🚀
What You Need

- AWS account 
- AWS CLI set up and ready
- Telegram Bot Token (create one using BotFather)
- Node.js installed

## Structure

 **Two Lambda functions:**
- **TelegramWebhookHandler**: Handles incoming messages and sets up EventBridge rules.
- **GymBookingHandler**: Books the gym classes 24 hours before the scheduled time.

**EventBridge (Cron Jobs):**
    - EventBridge is what schedules the booking. The first Lambda (TelegramWebhookHandler) creates the cron job when you schedule a class, which then triggers the booking Lambda 24 hours before the class.

```mermaid
---
title: Bot Architecture
---
graph LR
    A(User) --> B(telegram Bot)
    C(Bot - AWS Lambda)--->B
    B -->C
    C --> D(CloudWatch Events)
    D -->E(Booking - AWS Lamda)
    E -->F(Gym Web)
````

## Using the Bot 💬

- Start a conversation: Just message the bot to get started.
- Schedule a class: Type /info and follow the bot’s instructions to set up your class.
- Automatic Booking: 24 hours before your scheduled class, the bot will automatically book it for you.

Telegram Commands

    /start – Start interacting with the bot.
    /info - Get the available commands for the bot.
    /usuari - Set up the user for the gym application.
    /contrasenya - Set up the pasword for the user.
    /reserva – Schedule a gym class.
    /horari - List all the scheduled bookings.
    /elimina – Cancel a scheduled class schedule.

## License

This project is licensed under the GNU General Public License v3.0. See the LICENSE file for more details.