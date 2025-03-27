class SendMessageError(Exception):
    """Исключение, которое выбрасывается при ошибке отправки сообщения."""

    pass


class StatusError(Exception):
    """Исключение кода статуса, отличного от 200."""

    pass


class HomeworkStatusError(Exception):
    """Исключение, которое выбрасывается при ошибке отправки сообщения."""

    pass
