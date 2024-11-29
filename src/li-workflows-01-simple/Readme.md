# li-workflows-01-simple: Simple event driven workflow

Prep:
```
python -m pip install -r requirements.txt
```

Commands:

1. Deploy control plane
```
python -m llama_deploy.apiserver
```

2. Deploy manifest
```
llamactl deploy deployment.yml
``` 

3. Send message from lamactl
```
llamactl run --deployment QuickStart --arg message 'Hello from my shell!'
```

## Objective:

The objective is to learn how to set up a simple event driven workflow

![process](./image.png)

External reference: https://github.com/run-llama/llama_deploy/tree/main/examples/quick_start 

## Tasks:

- Run the sample to get familar with events
- Add custom event types to your flow
