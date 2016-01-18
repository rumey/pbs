def field_range(start, finish, percentage=False):
    if start or finish:
        if start is None: start = "N/A"
        if finish is None: finish = "N/A"
        if percentage:
            field_range = "{}%-{}%".format(start, finish)
        else:
            field_range = "{}-{}".format(start, finish)
    else:
        field_range = "N/A"
    return field_range
