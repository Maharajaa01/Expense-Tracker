"""Default categories and starter account seeded for every new user.

Icons are Lucide icon names (https://lucide.dev); the frontend renders them.
"""

EXPENSE_CATEGORIES = [
	("Food & Dining", "utensils", "#f97316"),
	("Groceries", "shopping-basket", "#84cc16"),
	("Shopping", "shopping-bag", "#ec4899"),
	("Transportation", "bus", "#3b82f6"),
	("Fuel", "fuel", "#f59e0b"),
	("Rent", "house", "#8b5cf6"),
	("Utilities", "zap", "#eab308"),
	("Healthcare", "heart-pulse", "#ef4444"),
	("Entertainment", "clapperboard", "#a855f7"),
	("Education", "graduation-cap", "#0ea5e9"),
	("Travel", "plane", "#06b6d4"),
	("Personal Care", "sparkles", "#f472b6"),
	("Insurance", "shield-check", "#14b8a6"),
	("Subscriptions", "repeat", "#6366f1"),
	("EMI & Loan Interest", "landmark", "#64748b"),
	("Other", "circle-ellipsis", "#94a3b8"),
]

INCOME_CATEGORIES = [
	("Salary", "briefcase", "#16a34a"),
	("Freelancing", "laptop", "#0d9488"),
	("Business Income", "store", "#059669"),
	("Investments", "trending-up", "#7c3aed"),
	("Interest", "percent", "#2563eb"),
	("Gifts", "gift", "#db2777"),
	("Other Income", "circle-plus", "#65a30d"),
]

STARTER_ACCOUNT = {"account_name": "Cash", "account_type": "Cash", "icon": "wallet", "color": "#10b981"}
