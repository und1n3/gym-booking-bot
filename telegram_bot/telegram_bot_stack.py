from aws_cdk import (
    Stack,
    aws_lambda,
    aws_apigateway,
    aws_ssm,
    aws_lambda_python_alpha,
    aws_iam,
    Duration,
)
from constructs import Construct
import os

class TelegramBotStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        telegram_token = aws_ssm.StringParameter.from_string_parameter_name(
            self, "TelegramApiToken", "fitness_bot_telegram_token"
        )
        booking_lambda = aws_lambda_python_alpha.PythonFunction(
            self,
            "GymBookingLambda",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            entry="lambda/booking_lambda",
            retry_attempts=0,
            timeout=Duration.seconds(20),
        )

        booking_lambda.add_to_role_policy(
            statement=aws_iam.PolicyStatement(
                actions=["ssm:GetParameter"], resources=["*"]
            )
        )
        booking_lambda.grant_invoke_composite_principal(
            composite_principal=aws_iam.CompositePrincipal(
                aws_iam.ServicePrincipal("events.amazonaws.com"),
            )
        )

        # Define the Lambda function
        telegram_bot_lambda = aws_lambda_python_alpha.PythonFunction(
            self,
            "TelegramBotHandler",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            entry="lambda/bot_lambda",
            retry_attempts=0,
            environment={"BOOKING_LAMBDA_ARN": booking_lambda.function_arn,
                         'WHITELIST':os.environ['WHITELIST']},
        )
        telegram_bot_lambda.add_to_role_policy(
            statement=aws_iam.PolicyStatement(
                actions=["ssm:PutParameter"], resources=["*"]
            )
        )
        telegram_bot_lambda.add_to_role_policy(
            statement=aws_iam.PolicyStatement(
                actions=[
                    "events:PutRule",
                    "events:PutTargets",
                    "events:ListRules",
                    "events:DeleteRule",
                    "events:RemoveTargets",
                ],
                resources=["*"],
            )
        )
        telegram_token.grant_read(telegram_bot_lambda)
        # Define the API Gateway
        api = aws_apigateway.LambdaRestApi(
            self, "TelegramBotApi", handler=telegram_bot_lambda, proxy=False
        )
        items = api.root.add_resource("webhook")
        items.add_method("POST")
