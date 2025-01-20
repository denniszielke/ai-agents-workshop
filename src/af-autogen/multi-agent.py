import dotenv
import os
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.projects.models import CodeInterpreterTool

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import BingGroundingTool

dotenv.load_dotenv()

# Create the token provider
token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")

az_model_client = AzureOpenAIChatCompletionClient(
    azure_deployment=os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME"),
    model=os.getenv("AZURE_OPENAI_COMPLETION_MODEL"),
    api_version=os.getenv("AZURE_OPENAI_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_ad_token_provider=token_provider,  # Optional if you choose key-based authentication.
    # api_key="sk-...", # For key-based authentication.
)

conn_id = None

with AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=os.environ["PROJECT_CONNECTION_STRING"],
) as project_client:
    
    bing_connection = project_client.connections.get(
        connection_name='bing',
    )

    conn_id = bing_connection.id

async def web_ai_agent(query: str) -> str:
    print("This is Bing for Azure AI Agent Service .......")
    bing = BingGroundingTool(connection_id=conn_id)
    with project_client:
        agent = project_client.agents.create_agent(
            model="gpt-4",
            name="my-assistant",
            instructions="""        
                You are a web search agent.
                Your only tool is search_tool - use it to find information.
                    You make only one search call at a time.
                    Once you have the results, you never do calculations based on them.
                """,
                tools=bing.definitions,
                headers={"x-ms-enable-preview": "true"}
            )
        print(f"Created agent, ID: {agent.id}")

        # Create thread for communication
        thread = project_client.agents.create_thread()
        print(f"Created thread, ID: {thread.id}")

        # Create message to thread
        message = project_client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=query,
        )
        print(f"SMS: {message}")
        # Create and process agent run in thread with tools
        run = project_client.agents.create_and_process_run(thread_id=thread.id, assistant_id=agent.id)
        print(f"Run finished with status: {run.status}")

        if run.status == "failed":
            print(f"Run failed: {run.last_error}")

        # Delete the assistant when done
        project_client.agents.delete_agent(agent.id)
        print("Deleted agent")

        # Fetch and log all messages
        messages = project_client.agents.list_messages(thread_id=thread.id)
        print("Messages:"+ messages["data"][0]["content"][0]["text"]["value"])
    return messages["data"][0]["content"][0]["text"]["value"]

async def save_blog_agent(blog_content: str) -> str:

    print("This is Code Interpreter for Azure AI Agent Service .......")


    code_interpreter = CodeInterpreterTool()
        
    agent = project_client.agents.create_agent(
            model="gpt-4o-mini",
            name="my-agent",
            instructions="You are helpful agent",
            tools=code_interpreter.definitions,
            # tool_resources=code_interpreter.resources,
    )

    thread = project_client.agents.create_thread()

    message = project_client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content="""
        
                    You are my Python programming assistant. Generate code,save """+ blog_content +
                    
                """    
                    and execute it according to the following requirements

                    .Save blog content to blog-{YYMMDDHHMMSS}.md

                    .give me the download this file link
                """,
    )
    # create and execute a run
    run = project_client.agents.create_and_process_run(thread_id=thread.id, assistant_id=agent.id)
    print(f"Run finished with status: {run.status}")

    if run.status == "failed":
            # Check if you got "Rate limit is exceeded.", then you want to get more quota
        print(f"Run failed: {run.last_error}")

        # # delete the original file from the agent to free up space (note: this does not delete your version of the file)
        # project_client.agents.delete_file(file.id)
        # print("Deleted file")

        # print the messages from the agent
    messages = project_client.agents.get_messages(thread_id=thread.id)
    print(f"Messages: {messages}")

        # get the most recent message from the assistant
    last_msg = messages.get_last_text_message_by_sender("assistant")
    if last_msg:
        print(f"Last Message: {last_msg.text.value}")

        # print(f"File: {messages.file_path_annotations}")


    for file_path_annotation in messages.file_path_annotations:

        file_name = os.path.basename(file_path_annotation.text)

        project_client.agents.save_file(file_id=file_path_annotation.file_path.file_id, file_name=file_name,target_dir="./blog")
        

    project_client.agents.delete_agent(agent.id)
    print("Deleted agent")


        # project_client.close()


    return "Saved"
   

    
bing_search_agent = AssistantAgent(
    name="bing_search_agent",
    model_client=az_model_client,
    tools=[web_ai_agent],
    system_message="You are a search expert, help me use tools to find relevant knowledge",
)

save_blog_content_agent = AssistantAgent(
    name="save_blog_content_agent",
    model_client=az_model_client,
    tools=[save_blog_agent],
    system_message="""
        Save blog content. Respond with 'Saved' to when your blog are saved.
    """
)

write_agent = AssistantAgent(
    name="write_agent",
    model_client=az_model_client,
    system_message="""
        You are a blog writer, please help me write a blog based on bing search content."
    """
)

text_termination = TextMentionTermination("Saved")
# Define a termination condition that stops the task after 5 messages.
max_message_termination = MaxMessageTermination(10)
# Combine the termination conditions using the `|`` operator so that the
# task stops when either condition is met.
termination = text_termination | max_message_termination

reflection_team = RoundRobinGroupChat([bing_search_agent, write_agent,save_blog_content_agent], termination_condition=termination)

async def assistant_run() -> None:

    await Console(
        reflection_team.run_stream(task="""

                        I am writing a blog about machine learning. Search for the following 3 questions and write a Chinese blog based on the search results ,save it
                        
                        1. What is Machine Learning?
                        2. The difference between AI and ML
                        3. The history of Machine Learning
                                

        """)
    ) 

asyncio.run(assistant_run())