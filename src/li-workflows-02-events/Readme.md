# li-workflows-02-events: Event driven agent collaboration

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

The objective is to learn how to set up a custom event driven flow

![process](./image.png)

## Tasks:

- Enhance the metadata of the workflow
- Add additional event types for processing custom agent logic for math