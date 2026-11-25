"""Uygulamaya özgü hata türleri."""


class AppError(Exception):
    """Tüm uygulama hatalarının ortak atası."""


class ValidationError(AppError):
    """Kullanıcı girdisi veya iş kuralı ihlali.

    ``field`` hatanın ait olduğu form alanının adıdır (ör. "Puan"); arayüz bu
    bilgiyle ilgili alanı işaretleyip hatayı alanın yanında gösterir.
    """

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field


class NotFoundError(AppError):
    """İstenen kayıt veritabanında bulunamadı."""


class AuthError(AppError):
    """Giriş veya yetki hatası."""
