import os, time
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import FileSearchTool, VectorStoreDataSource, VectorStoreDataSourceAssetType
from opentelemetry import trace
from azure.monitor.opentelemetry import configure_azure_monitor
from azure.ai.projects.models import FunctionTool, ToolSet, CodeInterpreterTool
from user_functions import user_functions

load_dotenv()

with AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=os.environ["PROJECT_CONNECTION_STRING"],
) as project_client:

    # Enable Azure Monitor tracing
    application_insights_connection_string = project_client.telemetry.get_connection_string()
    if not application_insights_connection_string:
        print("Application Insights was not enabled for this project.")
        print("Enable it via the 'Tracing' tab in your AI Foundry project page.")
        exit()
    configure_azure_monitor(connection_string=application_insights_connection_string)

    scenario = os.path.basename(__file__)
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span(scenario):

        vector_store_name = os.environ["VECTOR_STORE_NAME"]
        vector_store_id = os.environ["VECTOR_STORE_ID"]

        path = "/Users/dennis/labs/multi-contextual-agents/markdown/102065.md"

        _, asset_uri = project_client.upload_file(path)

        # vector_store = project_client.agents.create_vector_store(name=vector_store_name)

        ds = VectorStoreDataSource(asset_identifier=asset_uri, asset_type=VectorStoreDataSourceAssetType.URI_ASSET)
        vector_store = project_client.agents.create_vector_store_and_poll(data_sources=[ds], name=vector_store_name)
        print(f"Created vector store, vector store ID: {vector_store.id}")
        print(f"Vector Store: {vector_store}")

        # create a file search tool
        file_search_tool = FileSearchTool(vector_store_ids=[vector_store.id])
        functions = FunctionTool(user_functions)
        code_interpreter = CodeInterpreterTool()

        toolset = ToolSet()
        toolset.add(functions)
        toolset.add(code_interpreter)
        toolset.add(file_search_tool)

        # notices that FileSearchTool as tool and tool_resources must be added or the assistant unable to search the file
        agent = project_client.agents.create_agent(
            model="gpt-4o-mini",
            name="my-assistant",
            instructions="You are helpful assistant",
            toolset=toolset,
            tool_resources=file_search_tool.resources,
        )
        # [END upload_file_and_create_agent_with_file_search]
        print(f"Created agent, agent ID: {agent.id}")

        thread = project_client.agents.create_thread()
        print(f"Created thread, thread ID: {thread.id}")

        message = project_client.agents.create_message(
            thread_id=thread.id, role="user", content="I need a new mattres how wide is it?"
        )
        print(f"Created message, message ID: {message.id}")

        run = project_client.agents.create_and_process_run(thread_id=thread.id, assistant_id=agent.id)
        print(f"Created run, run ID: {run.id}")

        messages = project_client.agents.list_messages(thread_id=thread.id)
        print(f"Messages: {messages}")

        last_msg = messages.get_last_text_message_by_sender("assistant")
        if last_msg:
            print(f"Last Message: {last_msg.text.value}")
        
        project_client.agents.delete_agent(agent.id)
        print("Deleted agent")

    # project_client.agents.delete_vector_store(vector_store.id)
    # print("Deleted vector store")