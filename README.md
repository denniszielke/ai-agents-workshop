# AI Agent workshop

Regions that this deployment can be executed:
- uksouth
- swedencentral
- canadaeast
- australiaeast

## Quickstart & Infrastructure setup

The following lines of code will connect your Codespace az cli and azd cli to the right Azure subscription:

```
az login

azd auth login

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

Last but not least: deploy a dummy container in Azure Container Apps. 
```
bash ./azd-hooks/deploy.sh web $AZURE_ENV_NAME

```


# Workshop agenda

The scope of this workshop covers the following scenarios and technology stacks:

| Name | Description | Technology  |
| :-- | :--| :-- |
| [lc-react-tools](./src/lc-react-tools/Readme.md) | Single Agent: Implementation of a react based scenarios to leverage multiple tools | Streamlit, Azure OpenAI, Langchain |
| [lg-agents-01-coding:](./src/lg-agents-01-coding:/Readme.md) | Iterative code reviews | LangGraph, Azure OpenAI |
| [lg-agents-02-shop:](./src/lg-agents-02-shop:/Readme.md) | Human in the loop | LangGraph, Qdrant, Azure OpenAI |
| [li-workflows-01-simple](./src/li-workflows-01-simple/Readme.md) | Simple event driven workflow | Llama agents, Azure OpenAI |
| [li-workflows-02-events](./src/li-workflows-02-events/Readme.md) | Event driven agent collaboration | Llama agents, Azure OpenAI |
| [sk-agents-01-collaboration](./src/sk-agents-01-collaboration/Readme.md) | Simple mult agent discussion | Semantic kernel, Azure OpenAI |
| [sk-agents-02-creative](./src/sk-agents-02-creative/Readme.md) | Multi-turn multi agent discussion | Semantic kernel, Azure OpenAI |
