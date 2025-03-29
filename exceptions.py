class StatusError(Exception):
    """Исключение кода статуса, отличного от 200."""


class HomeworkStatusError(Exception):
    """Исключение, которое выбрасывается при ошибке отправки сообщения."""
