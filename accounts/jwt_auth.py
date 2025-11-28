# JWT Authentication module for Django Ninja
# simple-jwt를 기반으로 한 구현

from rest_framework_simplejwt.tokens import RefreshToken as DRFRefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication as DRFJWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from ninja.security import HttpBearer
from django.contrib.auth.models import AnonymousUser
from typing import Optional


class RefreshToken(DRFRefreshToken):
    """
    Django REST Framework의 RefreshToken을 래핑한 클래스
    사용자를 위한 refresh token 생성
    """
    @classmethod
    def for_user(cls, user):
        """Create a RefreshToken for a given user."""
        return super().for_user(user)


class JWTAuth(HttpBearer):
    """
    Django Ninja용 JWT 인증 클래스
    Authorization: Bearer <token> 형식의 토큰을 검증
    """
    
    def authenticate(self, request, token: str) -> Optional[object]:
        """
        JWT 토큰을 검증하고 사용자를 반환합니다.
        
        Args:
            request: Django request 객체
            token: Bearer 토큰 (Bearer 접두사 없음)
            
        Returns:
            인증된 사용자 객체 또는 None
        """
        try:
            # DRF의 JWTAuthentication 인스턴스 생성
            jwt_authenticator = DRFJWTAuthentication()
            
            # 토큰 검증
            validated_token = jwt_authenticator.get_validated_token(token)
            
            # 사용자 획득
            user = jwt_authenticator.get_user(validated_token)

            request.user = user
            
            return user
        except (InvalidToken, AuthenticationFailed) as e:
            print(f"JWT 인증 오류: {e}")
            return None
        except Exception as e:
            print(f"JWT 인증 중 예상치 못한 오류: {e}")
            return None

