from app.exceptions import AppError


class NotificationError(AppError):
    detail = "Notification internal error occured."


class PushNotificationError(NotificationError):
    detail = "Error occured while pushing new notification."


class SendNotificationMessageError(NotificationError):
    detail = "Error occured while sending notification message."
