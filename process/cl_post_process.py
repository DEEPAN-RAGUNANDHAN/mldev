def format_data(data):
    output_data = {
        "name": data["user_details"]["name"],
        "title": data["user_details"]["designation"],
        "mail": data["user_details"]["email"],
        "contact": data["user_details"]["contact"],
        "address": data["user_details"]["address"],
        "paragraphs": data["paragraphs"]
    }

    return output_data