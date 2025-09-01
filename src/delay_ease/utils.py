from src.delay_ease.const import TYPE_A_TOCS


def is_type_a_toc(train_operator: str) -> bool:
    return train_operator in TYPE_A_TOCS


def get_operator_website(train_operator: str) -> str:
    """Return the delay repay website URL for the given train operator"""
    return TYPE_A_TOCS.get(train_operator)
