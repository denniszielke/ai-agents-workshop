import ast
from dataclasses import dataclass
import os
import json
import sys
import uuid
import random
from typing import Any, Dict, List, Literal, Annotated, TypedDict, cast
from uuid import UUID
import dotenv
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
import streamlit as st
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.graph import MermaidDrawMethod
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.prebuilt import ToolNode
from langgraph.errors import NodeInterrupt
from langgraph.checkpoint.memory import MemorySaver
from langchain_qdrant import Qdrant
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain.tools.retriever import create_retriever_tool
from langchain_core.documents import Document

dotenv.load_dotenv()

st.set_page_config(
    page_title="AI agentic bot that can interact with a product index",
)

st.title("💬 AI agentic product recommendation")
st.caption("🚀 A Bot that can use different agents to retrieve, augment, generate, validate and iterate over a data warehouse")

def get_session_id() -> str:
    id = random.randint(0, 1000000)
    return "00000000-0000-0000-0000-" + str(id).zfill(12)

@st.cache_resource
def create_session(st: st) -> None:
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = get_session_id()
        print("started new session: " + st.session_state["session_id"])
        st.write("You are running in session: " + st.session_state["session_id"])

create_session(st)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

llm: AzureChatOpenAI = None
if "AZURE_OPENAI_API_KEY" in os.environ:
        # it seems codespaces messes with the proxy settings
    if "CODESPACES" in os.environ:
        from openai import DefaultHttpxClient
        import httpx
        http_client=DefaultHttpxClient()
        ahttp_client=httpx.AsyncClient()
        llm = AzureChatOpenAI(
            http_client=http_client,
            http_async_client=ahttp_client,
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_deployment=os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME"),
            openai_api_version=os.getenv("AZURE_OPENAI_VERSION"),
            temperature=0,
            streaming=False,
        )
    else:
        llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_deployment=os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME"),
            openai_api_version=os.getenv("AZURE_OPENAI_VERSION"),
            temperature=0,
            streaming=False
        )
    embeddings_model = AzureOpenAIEmbeddings(    
        azure_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME"),
        openai_api_version = os.getenv("AZURE_OPENAI_VERSION"),
        model= os.getenv("AZURE_OPENAI_EMBEDDING_MODEL"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY")
    )

else:
    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    llm = AzureChatOpenAI(
        azure_ad_token_provider=token_provider,
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_deployment=os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME"),
        openai_api_version=os.getenv("AZURE_OPENAI_VERSION"),
        temperature=0,
        openai_api_type="azure_ad",
        streaming=False
    )
    embeddings_model = AzureOpenAIEmbeddings(    
        azure_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME"),
        openai_api_version = os.getenv("AZURE_OPENAI_VERSION"),
        model= os.getenv("AZURE_OPENAI_EMBEDDING_MODEL"),
        azure_ad_token_provider = token_provider
    )

qdrant_client = QdrantClient(":memory:")
qdrant_client.create_collection(
    collection_name="products",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
)

vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name="products",
    embedding=embeddings_model,
)

retriever = vector_store.as_retriever()

@st.cache_resource
def load_data():

    with open(file='products.json', mode='r') as file:
        data = json.load(file)

    docs = []
    uuids = []
    for index, obj in enumerate(data):
        # Extract properties
        title: str = obj.get('title')
        id = "00000000-0000-0000-0000-" + str(obj.get('id')).zfill(12)  
        url = obj.get('url')
        description = obj.get('description')
        product_image_url = obj.get('product-image-url')
        measurements = obj.get('measurements')
        doc = Document(
            page_content=description,
            metadata={"url": url, "title": title, "id": id, "measurements": measurements, "product-image-url": product_image_url},
        )
        docs.append(doc)
        uuids.append(id)

    vector_store.add_documents(documents=docs, ids=uuids)

def search_index(query: str) -> List[Document]:
    return vector_store.similarity_search(query=query, k=5)

load_data()

# Define the state for the agent
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

# Define a new graph
workflow = StateGraph(State)

config = {"configurable": {"thread_id": "1"}, "recursion_limit":100}

@dataclass
class ProductSearchResult:
    id: str
    title: str
    url: str
    description: str
    measurements: str
    product_image_url: str

#-----------------------------------------------------------------------------------------------

@tool
def product_search_tool(query: str) -> List[ProductSearchResult]:
    """
    Search for relevant product information in the vector index based on the user's query.

    Args:
        query (str): The input query. This is used to search the vector index.

    Returns:
        List[str]: The list of product information that matches the query.

    """
    print("Searching for products with query: ", query)
    results = search_index(query)
    return [ProductSearchResult(
        id=result.metadata["id"],
        title=result.metadat["title"],
        url=result.metadata["url"],
        description=result.page_content, 
        measurements=result.metadata["measurements"],
        product_image_url=result.metadata["product-image-url"]) for result in results]


@tool
def ask_human(question: str):
    """
    Ask the user for more information.
    """
    raise NodeInterrupt(f"AskHuman: {question}")

#-----------------------------------------------------------------------------------------------

def product_inquiry_orchestrator(state: State) -> dict[str, list[AIMessage]]:
    prompt = """Your are an orchestrator agent that manages the comunication between the user and the provided agents.
    Use the following prefixes to redirect the flow of information. DO NOT ask the user to detail his request. This needs to be delegated to the other agents.

    - 'AskAgent-ProductSearchAgent:' for asking the product search agent to search for product information.
    - 'AskAgent-ProductAssemblyAgent:' for asking the product assembly agent to read the manual and provide the user with the information they need.

    If you are done, calling your agents, prepare an answer to the users, containing all relevant information. Ask the human by calling the appropriate tool.
    Close the conversation if the user is satisfied or if the user is not satisfied, ask the user for more information and continue the conversation.

    """

    prompt_template = ChatPromptTemplate.from_messages(
        [("system", prompt), ("placeholder", "{input}")]
    )
    call = prompt_template | llm
    return {"messages": [call.invoke({"input": state["messages"]})]}


workflow.add_node("product_inquiry_orchestrator", product_inquiry_orchestrator)

#-----------------------------------------------------------------------------------------------

search_tools = [product_search_tool, ask_human]

def product_search_agent(state: State) -> dict[str, list[AIMessage]]:
    prompt = """Your are an agent that searches for products and returns the results to the user or other agents'.
    Use the provided tools to search for the products the user is looking for. 
    
    Ask the user for the product they are looking for and use the search tools to find the relevant information. Try to push the user
    for more detailed information before doing the search. Call the corresponding tool to initiate the interaction with the user'.

    If your are satisfied with your results, send out a final questions to the user to ask if he is also satisfied.
    If yes, send out your final answer with a prefix 'Product-Search-Agent-Results:'.

    Iterate if required.
    """

    prompt_template = ChatPromptTemplate.from_messages(
        [("system", prompt), ("placeholder", "{input}")]
    )
    call = prompt_template | llm.bind_tools(search_tools, tool_choice="auto")
    return {"messages": [call.invoke({"input": state["messages"]}, config)]}


workflow.add_node("product_search_agent", product_search_agent)
workflow.add_node("search_tools", ToolNode(search_tools))

#-----------------------------------------------------------------------------------------------

def agent_tool_router(state: State):
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tool_node"
    elif isinstance(last_message, HumanMessage):
        return "agent_name"
    return "end_node"
#-----------------------------------------------------------------------------------------------

def orchestrator_router(state: State) -> Literal["product_search_agent", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]
    if "AskAgent-ProductSearchAgent:" in last_message.content:
        return "product_search_agent"
    return "__end__"

# Specify the edges between the nodes
workflow.add_edge(START, "product_inquiry_orchestrator")
workflow.add_conditional_edges(
    "product_inquiry_orchestrator", 
    orchestrator_router,
)

workflow.add_conditional_edges(
    "product_search_agent",
    agent_tool_router,
    {
        "end_node": "product_inquiry_orchestrator",
        "tool_node": "search_tools",
        "agent_name": "product_search_agent"
    }
)

workflow.add_edge("search_tools", "product_search_agent")

@st.cache_resource
def init_memory() -> MemorySaver:
    return MemorySaver()

memory = init_memory()

app = workflow.compile(checkpointer=memory)

human_query = st.chat_input()

if human_query:
    message = {"role": "user", "content": human_query}
    app.update_state(config, {"messages": [message]})
    st.session_state.chat_history.append(message)
    with st.chat_message("user"):
        st.markdown(human_query)

    for event in app.stream(None, config):  
        key = list(event.keys())[0]
        for value in event.values():
            if "messages" not in value:
                continue
            message = value["messages"][-1]
            message.pretty_print()
            if (isinstance(message, AIMessage)):
                role = key
                if message.content != "":
                    with st.chat_message(role, avatar="💭"):
                        st.markdown(message.content)
                    st.session_state.chat_history.append({"role": role, "content": message.content})
                elif message.additional_kwargs["tool_calls"]:
                    for tool_call in message.additional_kwargs["tool_calls"]:
                        if tool_call["function"]["name"] == "ask_human":
                            args = tool_call["function"]["arguments"]
                            content = ast.literal_eval(args)["question"]
                            id = tool_call["id"]
                            app.update_state(config, {"messages": [ToolMessage(content, tool_call_id=id)]})
                            with st.chat_message(role, avatar="💭"):
                                st.markdown(content)
                            st.session_state.chat_history.append({"role": role, "content": content})

