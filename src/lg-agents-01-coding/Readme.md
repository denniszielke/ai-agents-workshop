# lg-agents-01-coding: Iterative code reviews

Prep:
```
python -m pip install -r requirements.txt
```

Commands:

```
python -m streamlit run app.py --server.port=8000
```

## Objective:

The objective is to learn how to solve complex problems using a structured guided multi agent collaboration.

![process](./diagram.png)

## Tasks:

- Add an additional validation step where you rate the code quality using some KPIs (like length of a method, number of variables) in a numeric number.
- Implement the validation in an agent that executes in the reviewer.
- Output the metric in the UI
