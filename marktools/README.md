# archaitools

SDK for the Mark AI Agent Workflow Marketplace — search, buy, and rate pre-solved reasoning workflows for your AI agents.

Add pre-solved reasoning workflows to any AI agent in 3 lines:

```python
from archaitools import MarkClient

mark = MarkClient(api_key="mk_...")

# Agent autonomously: estimate → buy → execute → rate
receipt = mark.solve("File Ohio 2024 taxes with W2 and itemized deductions")
print(f"Tokens saved: {receipt.tokens_saved}")
```

## Installation

```bash
pip install archaitools                   # core
pip install archaitools[anthropic]        # + Claude support
pip install archaitools[openai]           # + OpenAI support
pip install archaitools[all]              # everything
```

## Usage with Claude

```python
import anthropic
from archaitools import MarkTools

client = anthropic.Anthropic()
tools = MarkTools(api_key="mk_...")

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=tools.to_anthropic(),
    messages=[{"role": "user", "content": "File my Ohio 2024 taxes, W2, itemized"}],
)
```

## Usage with OpenAI

```python
from openai import OpenAI
from archaitools import MarkTools

client = OpenAI()
tools = MarkTools(api_key="mk_...")

response = client.chat.completions.create(
    model="gpt-4",
    tools=tools.to_openai(),
    messages=[{"role": "user", "content": "File my Ohio 2024 taxes"}],
)
```
