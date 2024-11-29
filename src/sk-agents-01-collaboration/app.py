# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os
import dotenv
import copy
import pyperclip # Install via pip

from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent
from semantic_kernel.agents.strategies.selection.kernel_function_selection_strategy import (
    KernelFunctionSelectionStrategy,
)
from semantic_kernel.agents.strategies.termination.kernel_function_termination_strategy import (
    KernelFunctionTerminationStrategy,
)
from semantic_kernel.connectors.ai.open_ai.services.azure_chat_completion import AzureChatCompletion
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from semantic_kernel.functions.kernel_function_from_prompt import KernelFunctionFromPrompt
from semantic_kernel.kernel import Kernel

###################################################################
# The following sample demonstrates how to create a simple,       #
# agent group chat that utilizes a Reviewer Chat Completion       #
# Agent along with a Writer Chat Completion Agent to              #
# complete a user's task.                                         #
###################################################################

dotenv.load_dotenv()

class ClipboardAccess:
    @kernel_function
    def set_clipboard(content: str):
        if not content.strip():
            return

        pyperclip.copy(content)


REVIEWER_NAME = "Reviewer"
COPYWRITER_NAME = "Writer"

import openai
import httpx

def _create_kernel_with_chat_completion(service_id: str) -> Kernel:
    # it seems codespaces messes with the proxy settings
    if "CODESPACES" in os.environ:
        ahttp_client = httpx.AsyncClient()
        client = openai.AsyncAzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-10-01-preview",
            http_client=ahttp_client,
        )
        chat_completion_service = AzureChatCompletion(
            deployment_name=os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME"),  
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"), # Used to point to your service
            service_id=service_id, # Optional; for targeting specific services within Semantic Kernel
            async_client=client,
        )
    else:
        chat_completion_service = AzureChatCompletion(
            deployment_name=os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME"),  
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"), # Used to point to your service
            service_id=service_id, # Optional; for targeting specific services within Semantic Kernel
        )

    kernel = Kernel()
    kernel.add_service(chat_completion_service)
    return kernel

async def main():
    agent_reviewer = ChatCompletionAgent(
        service_id=REVIEWER_NAME,
        kernel=_create_kernel_with_chat_completion(REVIEWER_NAME),
        name=REVIEWER_NAME,
        instructions="""
            Your responsiblity is to review and identify how to improve user provided content.
            If the user has providing input or direction for content already provided, specify how to 
            address this input.
            Never directly perform the correction or provide example.
            Once the content has been updated in a subsequent response, you will review the content 
            again until satisfactory.
            Always copy satisfactory content to the clipboard using available tools and inform user.

            RULES:
            - Only identify suggestions that are specific and actionable.
            - Verify previous suggestions have been addressed.
            - Never repeat previous suggestions.
            """,
    )

    agent_writer = ChatCompletionAgent(
        service_id=COPYWRITER_NAME,
        kernel=_create_kernel_with_chat_completion(COPYWRITER_NAME),
        name=COPYWRITER_NAME,
        instructions="""
            Your sole responsiblity is to rewrite content according to review suggestions.

            - Always apply all review direction.
            - Always revise the content in its entirety without explanation.
            - Never address the user.
            """,
    )

    selection_function = KernelFunctionFromPrompt(
        function_name="selection",
        prompt=f"""
        Determine which participant takes the next turn in a conversation based on the the most recent participant.
        State only the name of the participant to take the next turn.
        No participant should take more than one turn in a row.

        Choose only from these participants:
        - {REVIEWER_NAME}
        - {COPYWRITER_NAME}

        Always follow these rules when selecting the next participant:
        - After user input, it is {COPYWRITER_NAME}'s turn.
        - After {COPYWRITER_NAME} replies, it is {REVIEWER_NAME}'s turn.
        - After {REVIEWER_NAME} provides feedback, it is {COPYWRITER_NAME}'s turn.

        History:
        {{{{$history}}}}
        """,
    )

    TERMINATION_KEYWORD = "yes"

    termination_function = KernelFunctionFromPrompt(
        function_name="termination",
        prompt=f"""
            Examine the RESPONSE and determine whether the content has been deemed satisfactory.
            If content is satisfactory, respond with a single word without explanation: {TERMINATION_KEYWORD}.
            If specific suggestions are being provided, it is not satisfactory.
            If no correction is suggested, it is satisfactory.

            RESPONSE:
            {{{{$history}}}}
            """,
    )

    chat = AgentGroupChat(
        agents=[agent_writer, agent_reviewer],
        selection_strategy=KernelFunctionSelectionStrategy(
            function=selection_function,
            kernel=_create_kernel_with_chat_completion("selection"),
            result_parser=lambda result: str(result.value[0]) if result.value is not None else COPYWRITER_NAME,
            agent_variable_name="agents",
            history_variable_name="history",
        ),
        termination_strategy=KernelFunctionTerminationStrategy(
            agents=[agent_reviewer],
            function=termination_function,
            kernel=_create_kernel_with_chat_completion("termination"),
            result_parser=lambda result: TERMINATION_KEYWORD in str(result.value[0]).lower(),
            history_variable_name="history",
            maximum_iterations=10,
        ),
    )

    is_complete: bool = False
    while not is_complete:
        user_input = input("User:> ")
        if not user_input:
            continue

        if user_input.lower() == "exit":
            is_complete = True
            break

        if user_input.lower() == "reset":
            await chat.reset()
            print("[Conversation has been reset]")
            continue

        if user_input.startswith("@") and len(input) > 1:
            file_path = input[1:]
            try:
                if not os.path.exists(file_path):
                    print(f"Unable to access file: {file_path}")
                    continue
                with open(file_path) as file:
                    user_input = file.read()
            except Exception:
                print(f"Unable to access file: {file_path}")
                continue

        await chat.add_chat_message(ChatMessageContent(role=AuthorRole.USER, content=user_input))

        async for response in chat.invoke():
            print(f"# {response.role} - {response.name or '*'}: '{response.content}'")

        if chat.is_complete:
            is_complete = True
            break


if __name__ == "__main__":
    asyncio.run(main())