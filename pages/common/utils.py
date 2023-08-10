import re


def get_same_prefix(input_item, item_list):
    prefix = input_item.split("_")[0]  # Extract the prefix before any trailing number
    matching_items = [item for item in item_list if item.startswith(prefix)]

    return prefix, matching_items


def get_highest_number(input_item, item_list):
    prefix, matching_items = get_same_prefix(input_item, item_list)
    highest_item = None
    highest_number = -1

    for item in matching_items:
        match = re.match(rf"{input_item}_\d+", item)
        if match:
            # trailing_number = int(item.split("_")[1])
            trailing_number = int(item[len(input_item) + 1 :])
            if trailing_number > highest_number:
                highest_number = trailing_number
                highest_item = item

    return highest_item


def get_next_item(input_item, item_list):
    prefix, _ = get_same_prefix(input_item, item_list)
    highest_item = get_highest_number(prefix, item_list)

    if highest_item:
        highest_number = int(highest_item.split("_")[1])
        next_available_number = highest_number + 1
        next_available_item = f"{prefix}_{next_available_number}"
        return next_available_item
    else:
        return f"{input_item}_1"


def convert_template(input_data):
    output = []

    for question_name, question_data in input_data.items():
        # category = question_data.get("category", "")
        fun = question_data.get("fun", "")
        # input_fields = question_data.get("input", [])
        variants = question_data.get("variants", [])

        if variants:
            for idx, variant in enumerate(variants):
                name = f"{question_name}_{idx}" if idx > 0 else question_name
                variant_data = {"name": name, "fun": fun, "options": variant}
                output.append(variant_data)
        else:
            variant_data = {"name": question_name, "fun": fun}
            output.append(variant_data)

    return output


if __name__ == "__main__":
    # Test cases
    items = ["How", "Why", "Why_3", "Why_12", "What"]
    for item in items:
        next_available_item = get_next_item(item, items)
        print(f"{item}: {next_available_item}")
