def format_data(data):
    user = data.get("user_details", {})
    output_data = {
        "name": data["user_details"]["name"],
        "title": data["job_description"]["job_title"],
        "mail": data["user_details"]["email"],
        "contact": data["user_details"]["contact"],
        "address": data["user_details"]["address"],
        "paragraphs": data["paragraphs"]
    }

    return output_data