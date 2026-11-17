"""Money rules shared by every calculation. All amounts are integer piastres."""


def whole_pound_discount(gross, raw_discount):
    """The discount to use so that (gross - discount) is whole pounds.

    Prices are never touched; only the discount moves, by less than 1 pound:
    rounded DOWN normally, or UP when rounding down would make it negative."""
    frac = (gross - raw_discount) % 100
    if frac == 0:
        return raw_discount
    down = raw_discount - (100 - frac)
    if down >= 0:
        return down
    return raw_discount + frac
