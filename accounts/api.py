# account/api.py
from ninja import Router
from ninja.errors import HttpError
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from django.db import transaction 
from django.contrib.auth import authenticate

from ninja.errors import HttpError
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.authentication import JWTAuth
from .schemas import UserInfoSchema, UserSignupSchema, UserLoginSchema, LoginResponseSchema, CompanyCreateSchema, DepartmentCreateSchema

from .models import User, Company, Department
from .schemas import *

router = Router()

@router.post("/companies")
def create_company(request, payload: CompanyCreateSchema):
    if Company.objects.filter(registration_number=payload.registration_number).exists():
        raise HttpError(409, "이미 등록된 사업자번호입니다.")

    company = Company.objects.create(
        name=payload.name,
        registration_number=payload.registration_number,
        industry=payload.industry
    )
    
    return {
        "message": "회사가 생성되었습니다.",
        "company_id": company.id,
        "company_name": company.name
    }


@router.post("/departments")
def create_department(request, payload: DepartmentCreateSchema):
    """
    [Step 2] 회사 안에 부서를 만듭니다.
    Step 1에서 받은 'company_id'가 필요합니다.
    """

    company = get_object_or_404(Company, id=payload.company_id)

    if Department.objects.filter(company=company, code=payload.code).exists():
        raise HttpError(409, f"[{company.name}]에 이미 존재하는 부서 코드입니다.")

    dept = Department.objects.create(
        company=company,
        code=payload.code,
        name=payload.name
    )

    return {
        "message": "부서가 생성되었습니다.",
        "department_id": dept.id,
        "department_name": dept.name
    }


@router.post("/signup")
def signup(request, payload: UserSignupSchema):

    if payload.password != payload.password_confirm:
        raise HttpError(400, "비밀번호가 일치하지 않습니다.")


    if User.objects.filter(username=payload.username).exists():
        raise HttpError(409, "이미 존재하는 아이디입니다.")

    company = get_object_or_404(Company, id=payload.company_id)
    
    department = None
    if payload.department_id:
        department = get_object_or_404(Department, id=payload.department_id)
        if department.company_id != company.id:
            raise HttpError(400, "선택한 부서가 해당 회사 소속이 아닙니다.")

    if User.objects.filter(company=company, employee_id=payload.employee_id).exists():
        raise HttpError(409, "우리 회사에 이미 등록된 사원번호입니다.")

    with transaction.atomic():
        user = User.objects.create(
            username=payload.username,
            password=make_password(payload.password),
            korean_name=payload.korean_name,
            employee_id=payload.employee_id,
            company=company,
            department=department,
            phone_number=payload.phone_number,
            email=payload.email,
        )

    return {"status": "success", "user_id": user.id, "username": user.username}

@router.post("/login", response=LoginResponseSchema)
def login(request, payload: UserLoginSchema):
    user = authenticate(username=payload.username, password=payload.password)

    if user:
        print("로그인 시도한 사용자:", user.username)
    if user is None:
        raise HttpError(401, "아이디 또는 비밀번호가 올바르지 않습니다.")

    if not user.is_active:
        raise HttpError(403, "비활성화된 계정입니다. 관리자에게 문의하세요.")

    # 2. 토큰 수동 생성
    refresh = RefreshToken.for_user(user)
    
    return {
        "message": "로그인 성공",
        "token": {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        },
        "user": {
            "id": user.id,
            "username": user.username,
            "korean_name": user.korean_name,
            "employee_id": user.employee_id,
            "company_name": user.company.name if user.company else None,
            "department_name": user.department.name if user.department else None,
        }
    }

@router.get("/me", response=UserInfoSchema, auth=JWTAuth())
def get_user_profile(request):
    return {
        "id": request.user.id,
        "username": request.user.username,
        "korean_name": request.user.korean_name,
        "employee_id": request.user.employee_id,
        "company_name": request.user.company.name if request.user.company else "소속 없음",
        "department_name": request.user.department.name if request.user.department else "-"
    }