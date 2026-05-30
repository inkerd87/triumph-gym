import re


def format_phone(phone):
    if not phone:
        return phone
    digits = re.sub(r'\D', '', phone)
    if not digits:
        return phone
    if len(digits) == 11 and digits.startswith(('7', '8')):
        digits = digits[1:]
    elif len(digits) > 10:
        digits = digits[-10:]
    if len(digits) == 10:
        return f"+7 {digits[:3]} {digits[3:6]}-{digits[6:8]}-{digits[8:]}"
    return phone
