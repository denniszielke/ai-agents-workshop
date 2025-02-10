# AI Agent workshop

Regions that this deployment can be executed:
- northeurope (azure location)
- swedencentral (aiResourceLocation)

## Quickstart & Infrastructure setup

The following lines of code will connect your Codespace az cli and azd cli to the right Azure subscription:

```
# log in with the provided credentials - OPEN A PRIVATE BROWSER SESSION
az login --use-device-code

# if you need to log into a specific tenant - use the --tenant 00000000-0000-0000-0000-000000000000 parameter
az login --use-device-code --tenant 00000000-0000-0000-0000-000000000000 

# "log into azure dev cli - only once" - OPEN A PRIVATE BROWSER SESSION
azd auth login --use-device-code

# press enter open up https://microsoft.com/devicelogin and enter the code

```

Now deploy the infrastructure components with azure cli

```
azd up
```

Get the values for some env variables
```
azd env get-values | grep AZURE_ENV_NAME
source <(azd env get-values | grep AZURE_ENV_NAME)
```

deploy the project lc-react-tools in Azure Container Apps. 
```
bash ./azd-hooks/deploy.sh lc-react-tools $AZURE_ENV_NAME
```


# Workshop agenda

The scope of this workshop covers the following scenarios and technology stacks:

| Name | Description | Technology  |
| :-- | :--| :-- |
| [af-simple](./src/af-simple/code-run.py) | Single Agent | AgentService, RAG |
| [af-autogen](./src/af-autogen/simple.py) | Single Agent | AgentService, Autogen |
| [lc-react-tools](./src/lc-react-tools/Readme.md) | Single Agent | Streamlit, Azure OpenAI, Langchain |
| [lg-agents-01-coding](./src/lg-agents-01-coding/Readme.md) | Multi-agent code reviews | LangGraph, Azure OpenAI, Otel |
| [lg-agents-02-shop](./src/lg-agents-02-shop/Readme.md) | Human in the loop | LangGraph, Qdrant, Azure OpenAI |
| [li-workflows-01-simple](./src/li-workflows-01-simple/Readme.md) | Simple event driven workflow | Llama agents, Azure OpenAI |
| [li-workflows-02-events](./src/li-workflows-02-events/Readme.md) | Event driven agent collaboration | Llama agents, Azure OpenAI |
| [sk-agents-01-collaboration](./src/sk-agents-01-collaboration/Readme.md) | Simple mult agent discussion | Semantic kernel, Azure OpenAI |
| [sk-agents-02-tools](./src/sk-agents-02-tools/Readme.md) | Using tools from agents | Semantic kernel, Azure OpenAI |
| [sk-agents-03-creative](./src/sk-agents-03-creative/Readme.md) | Multi-turn multi agent discussion | Semantic kernel, Azure OpenAI |
| [sk-agents-04-process](./src/sk-agents-04-process/Readme.md) | Event driven flow | Semantic kernel, Azure OpenAI |
