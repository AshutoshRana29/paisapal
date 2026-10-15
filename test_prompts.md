# PaisaPal – Test Prompts

These are the **5 mandatory prompts** from the acceptance criteria.  
Run the agent and try them (after seeding data).

---

### 1. Spent 250 on pizza yesterday and 120 on an auto today.

**Expected:**  
Agent should add two expenses:
- Food – 250 – yesterday
- Travel – 120 – today  

It should confirm both and warn if any budget is crossed.

---

### 2. How much did I spend on food this month?

**Expected:**  
Calls `get_spending_summary` or filters `list_transactions` and returns the Food total for current month.

---

### 3. Set my shopping budget to 3000 for this month.

**Expected:**  
Calls `set_budget` with category=Shopping, limit=3000, current month.  
Confirms the action.

---

### 4. Am I over budget anywhere?

**Expected:**  
Calls `check_budget_status` and lists categories that are ≥80% or over 100%.

---

### 5. Compare my spending this month with last month and give me 3 saving tips.

**Expected:**  
Agent fetches summaries for both months and gives practical tips (based on actual numbers, not invented).

---

## Extra: Business Rule Violation

**Try:** "Delete transaction 5"  
→ Agent must ask for confirmation before calling `delete_transaction`.

**Try:** "Spent -100 on food"  
→ Agent should reject negative amount.

---

All tools hit the real SQLite database. No hard-coded answers.
