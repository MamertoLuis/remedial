from django import template
from django.template.defaultfilters import register


@register.filter(name="get_item")
def get_item(dictionary, key):
    if hasattr(dictionary, "get"):  # Check if it's a dictionary-like object
        return dictionary.get(key)
    return None  # Return None if not a dictionary, or if key not found
