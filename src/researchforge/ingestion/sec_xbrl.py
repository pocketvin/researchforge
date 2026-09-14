"""SEC XBRL metric aliases and period semantics used by V2 deterministic extraction."""

DURATION_METRICS = frozenset({"revenue", "operating_cost", "net_income", "operating_cash_flow"})

TAG_ALIASES: dict[str, tuple[str, ...]] = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ),
    "operating_cost": (
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization",
    ),
    "net_income": ("NetIncomeLoss",),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "accounts_receivable": ("AccountsReceivableNetCurrent", "AccountsReceivableNet"),
    "inventory": ("InventoryNet",),
}
