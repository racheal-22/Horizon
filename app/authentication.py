import jwt

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from app.models import User


class CustomJWTAuthentication(
    BaseAuthentication
):

    def authenticate(
        self,
        request
    ):

        auth_header = request.headers.get(
            "Authorization"
        )

        if not auth_header:

            return None

        try:

            token = auth_header.split(
                " "
            )[1]

        except IndexError:

            raise AuthenticationFailed(
                "Invalid token format"
            )

        try:

            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )

        except jwt.ExpiredSignatureError:

            raise AuthenticationFailed(
                "Token expired"
            )

        except jwt.InvalidTokenError:

            raise AuthenticationFailed(
                "Invalid token"
            )

        user_id = payload.get(
            "user_id"
        )

        user = User.objects.filter(
            id=user_id
        ).first()

        if not user:

            raise AuthenticationFailed(
                "User not found"
            )

        return (
            user,
            None
        )