import os
import asyncio
import logging
import sys
import dotenv
from typing import Any, List
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from llama_index.llms.azure_openai import AzureOpenAI

from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.tools import FunctionTool

from llama_index.core.llms import ChatMessage
from llama_index.core.tools import ToolSelection, ToolOutput
from llama_index.core.workflow import Event

from llama_index.core.llms.function_calling import FunctionCallingLLM
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.tools.types import BaseTool
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, step

dotenv.load_dotenv()

logging.basicConfig(
    stream=sys.stdout, level=logging.INFO
)  # logging.DEBUG for more verbose output
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

azureOpenAI: AzureOpenAI = None
embeddings_model: AzureOpenAIEmbedding = None
if "AZURE_OPENAI_API_KEY" in os.environ:
    azureOpenAI = AzureOpenAI(
        model=os.getenv("AZURE_OPENAI_COMPLETION_MODEL"),
        azure_deployment=os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("OPENAI_API_VERSION")
    )
else:
    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    azureOpenAI = AzureOpenAI(
        azure_ad_token_provider=token_provider,
        use_azure_ad=True,
        model=os.getenv("AZURE_OPENAI_COMPLETION_MODEL"),
        azure_deployment=os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME"),
        api_key=token_provider(),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("OPENAI_API_VERSION")
    )

# handle events
class InputEvent(Event):
    input: list[ChatMessage]

class ToolCallEvent(Event):
    tool_calls: list[ToolSelection]

class FunctionOutputEvent(Event):
    output: ToolOutput

# define agents


class FuncationCallingAgent(Workflow):
    def __init__(
        self,
        *args: Any,
        llm: FunctionCallingLLM | None = None,
        tools: List[BaseTool] | None = None,
        **kwargs: Any,
    ) -> None:
        print("starting up")
        super().__init__(*args, **kwargs)
        self.tools = tools or []

        self.llm = llm
        assert self.llm.metadata.is_function_calling_model

        self.memory = ChatMemoryBuffer.from_defaults(llm=llm)
        self.sources = []

    @step
    async def prepare_chat_history(self, ev: StartEvent) -> InputEvent:
        # clear sources
        self.sources = []

        # get user input
        user_input = str(ev.get("input", ""))
        user_msg = ChatMessage(role="user", content=user_input)
        self.memory.put(user_msg)

        # get chat history
        chat_history = self.memory.get()
        return InputEvent(input=chat_history)

    @step
    async def handle_llm_input(
        self, ev: InputEvent
    ) -> ToolCallEvent | StopEvent:
        chat_history = ev.input

        response = await self.llm.achat_with_tools(
            self.tools, chat_history=chat_history
        )
        self.memory.put(response.message)

        tool_calls = self.llm.get_tool_calls_from_response(
            response, error_on_no_tool_call=False
        )

        if not tool_calls:
            return StopEvent(
                result={"response": response, "sources": [*self.sources]}
            )
        else:
            return ToolCallEvent(tool_calls=tool_calls)

    @step
    async def handle_tool_calls(self, ev: ToolCallEvent) -> InputEvent:
        tool_calls = ev.tool_calls
        tools_by_name = {tool.metadata.get_name(): tool for tool in self.tools}

        tool_msgs = []

        # call tools -- safely!
        for tool_call in tool_calls:
            tool = tools_by_name.get(tool_call.tool_name)
            additional_kwargs = {
                "tool_call_id": tool_call.tool_id,
                "name": tool.metadata.get_name(),
            }
            if not tool:
                tool_msgs.append(
                    ChatMessage(
                        role="tool",
                        content=f"Tool {tool_call.tool_name} does not exist",
                        additional_kwargs=additional_kwargs,
                    )
                )
                continue

            try:
                tool_output = tool(**tool_call.tool_kwargs)
                self.sources.append(tool_output)
                tool_msgs.append(
                    ChatMessage(
                        role="tool",
                        content=tool_output.content,
                        additional_kwargs=additional_kwargs,
                    )
                )
            except Exception as e:
                tool_msgs.append(
                    ChatMessage(
                        role="tool",
                        content=f"Encountered error in tool call: {e}",
                        additional_kwargs=additional_kwargs,
                    )
                )

        for msg in tool_msgs:
            self.memory.put(msg)

        chat_history = self.memory.get()
        return InputEvent(input=chat_history)

# define tools
def get_the_secret_fact() -> str:
    """Returns the secret fact."""
    return "The secret fact is: A baby llama is called a 'Cria'."

def add(x: int, y: int) -> int:
    """Useful function to add two numbers."""
    return x + y


def multiply(x: int, y: int) -> int:
    """Useful function to multiply two numbers."""
    return x * y

tools = [
    FunctionTool.from_defaults(get_the_secret_fact),
    FunctionTool.from_defaults(add),
    FunctionTool.from_defaults(multiply),
]

agent_workflow = FuncationCallingAgent(
    llm=azureOpenAI, tools=tools, timeout=120, verbose=True
)

async def main():
    ret = await agent_workflow.run(input="Hello!")
    print(ret["response"])

    ret = await agent_workflow.run(input="What is (2123 + 2321) * 312?")
    print(ret["response"])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())