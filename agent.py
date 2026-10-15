import os
import json
from openai import OpenAI
from dotenv import load_dotenv
import tools

load_dotenv()

# Groq
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

SYSTEM_PROMPT = """
You are PaisaPal, a friendly and practical personal expense & budget coach for students and young professionals.

You help users:
- Log income and expenses in plain English
- Track spending by category
- Set and monitor monthly budgets
- Give simple insights and saving tips

Rules you must follow:
- Always introduce yourself as PaisaPal on first message.
- If amount, category, or date is missing or unclear, ASK the user instead of guessing.
- Convert relative dates (yesterday, today, last Monday, etc.) correctly.
- Confirm before deleting any transaction.
- When an expense pushes a category over 80% of budget, warn the user. Over 100% → clear alert.
- Amounts must be positive.
- Be concise, helpful, and a bit Gen-Z friendly but professional.
- Never invent data. Always use the tools.
- Support multiple users (identify by name).

Available categories: Food, Travel, Rent, Shopping, Bills, Entertainment, Other.
"""

#tool definitions
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_transaction",
            "description": "Add an income or expense transaction",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"},
                    "amount": {"type": "number"},
                    "category": {"type": "string"},
                    "note": {"type": "string"},
                    "date_text": {"type": "string", "description": "yesterday, today, 2026-10-10, etc."},
                    "txn_type": {"type": "string", "enum": ["INCOME", "EXPENSE"]}
                },
                "required": ["user_id", "amount", "note", "date_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_transactions",
            "description": "List transactions with optional filters",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "category": {"type": "string"},
                    "txn_type": {"type": "string"},
                    "limit": {"type": "integer"}
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_spending_summary",
            "description": "Get spending total per category for a month",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"},
                    "month": {"type": "string", "description": "YYYY-MM"}
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_budget",
            "description": "Set or update monthly budget for a category",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"},
                    "category": {"type": "string"},
                    "month": {"type": "string"},
                    "limit_amount": {"type": "number"}
                },
                "required": ["user_id", "category", "month", "limit_amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_budget_status",
            "description": "Check spent vs budget limit for this month",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"},
                    "month": {"type": "string"}
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_transaction",
            "description": "Delete a transaction (only after user confirmation)",
            "parameters": {
                "type": "object",
                "properties": {
                    "txn_id": {"type": "integer"},
                    "user_id": {"type": "integer"}
                },
                "required": ["txn_id", "user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_or_create_user",
            "description": "Get user_id by name, create if new",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                },
                "required": ["name"]
            }
        }
    }
]

TOOL_MAP = {
    "add_transaction": tools.add_transaction,
    "list_transactions": tools.list_transactions,
    "get_spending_summary": tools.get_spending_summary,
    "set_budget": tools.set_budget,
    "check_budget_status": tools.check_budget_status,
    "delete_transaction": tools.delete_transaction,
    "get_or_create_user": tools.get_or_create_user,
}


def run_agent():
    print("PaisaPal is ready. Type 'quit' to exit.\n")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "bye"):
            print("PaisaPal: See you! Keep tracking those expenses.")
            break

        messages.append({"role": "user", "content": user_input})

        # called groq model here
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3
        )

        msg = response.choices[0].message
        messages.append(msg)

        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                print(f"  [Calling tool: {name}]")

                try:
                    result = TOOL_MAP[name](**args)
                except Exception as e:
                    result = {"error": str(e)}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })

            #response after tools
            final = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=messages,
                temperature=0.3
            )
            reply = final.choices[0].message.content
            messages.append({"role": "assistant", "content": reply})
        else:
            reply = msg.content

        print(f"PaisaPal: {reply}\n")


if __name__ == "__main__":
    run_agent()