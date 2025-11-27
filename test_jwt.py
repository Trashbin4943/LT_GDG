#!/usr/bin/env python
"""
JWT 토큰 생성 및 검증 테스트 스크립트
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linguaproject.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.jwt_auth import RefreshToken, JWTAuth

User = get_user_model()

def test_jwt():
    print("=" * 60)
    print("JWT 토큰 생성 및 검증 테스트")
    print("=" * 60)
    
    # 테스트 사용자 생성 또는 기존 사용자 사용
    try:
        user = User.objects.get(username='admin')
        print(f"✅ 기존 사용자 사용: {user.username}")
    except User.DoesNotExist:
        print("❌ admin 사용자를 찾을 수 없습니다.")
        return
    
    # 1. RefreshToken 생성 테스트
    print("\n[1] RefreshToken 생성 테스트")
    try:
        refresh = RefreshToken.for_user(user)
        print(f"✅ RefreshToken 생성 성공")
        print(f"   Refresh Token (처음 100자): {str(refresh)[:100]}...")
        print(f"   Access Token (처음 100자): {str(refresh.access_token)[:100]}...")
    except Exception as e:
        print(f"❌ RefreshToken 생성 실패: {e}")
        return
    
    # 2. 토큰 검증 테스트
    print("\n[2] JWT 토큰 검증 테스트")
    try:
        access_token = str(refresh.access_token)
        jwt_auth = JWTAuth()
        
        # 더미 request 객체 생성
        class DummyRequest:
            pass
        
        authenticated_user = jwt_auth.authenticate(DummyRequest(), access_token)
        
        if authenticated_user and authenticated_user.username == user.username:
            print(f"✅ Access Token 검증 성공")
            print(f"   인증된 사용자: {authenticated_user.username}")
        else:
            print(f"❌ Access Token 검증 실패 또는 사용자 불일치")
    except Exception as e:
        print(f"❌ Access Token 검증 중 오류: {e}")
    
    # 3. 잘못된 토큰 검증 테스트
    print("\n[3] 잘못된 토큰 검증 테스트")
    try:
        fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        jwt_auth = JWTAuth()
        
        class DummyRequest:
            pass
        
        authenticated_user = jwt_auth.authenticate(DummyRequest(), fake_token)
        
        if authenticated_user is None:
            print(f"✅ 잘못된 토큰 정상적으로 거부됨")
        else:
            print(f"❌ 잘못된 토큰이 인증됨 (보안 문제!)")
    except Exception as e:
        print(f"✅ 잘못된 토큰 검증 실패 (예상된 동작): {type(e).__name__}")
    
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)

if __name__ == '__main__':
    test_jwt()
