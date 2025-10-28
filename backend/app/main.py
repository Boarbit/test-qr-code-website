from fastapi import Depends, FastAPI, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import io
import os
import qrcode

app = FastAPI(title="Container Tracker (Static)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://0.0.0.0:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Item(BaseModel):
    name: str
    quantity: int = Field(..., ge=0, description="Number of units for the item")


class Container(BaseModel):
    qr_code: str
    name: str
    contents: List[Item]


class MockUser(BaseModel):
    id: str
    name: str
    role: str
    permissions: List[str]
    is_admin: bool = False


VIEW_PERMISSION = "view"
UPDATE_PERMISSION = "update"
CREATE_PERMISSION = "create"
ASSIGN_PERMISSION = "assign"

ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "Viewer": [VIEW_PERMISSION],
    "Editor": [VIEW_PERMISSION, UPDATE_PERMISSION],
    "Creator": [VIEW_PERMISSION, CREATE_PERMISSION],
    "Admin": [VIEW_PERMISSION, UPDATE_PERMISSION, CREATE_PERMISSION, ASSIGN_PERMISSION],
}


_mock_users = [
    MockUser(
        id="admin",
        name="Alex Admin",
        role="Admin",
        permissions=[],
        is_admin=True,
    ),
    MockUser(
        id="editor",
        name="Erin Editor",
        role="Viewer",
        permissions=[],
    ),
    MockUser(
        id="creator",
        name="Casey Creator",
        role="Viewer",
        permissions=[],
    ),
    MockUser(
        id="viewer",
        name="Vic Viewer",
        role="Viewer",
        permissions=[],
    ),
]


def apply_role(user: MockUser, role: str) -> MockUser:
    if user.is_admin:
        role = "Admin"
    permissions = ROLE_PERMISSIONS.get(role)
    if not permissions:
        raise HTTPException(status_code=400, detail="Unknown role")

    return MockUser(
        id=user.id,
        name=user.name,
        role=role,
        permissions=list(permissions),
        is_admin=user.is_admin,
    )


mock_users: Dict[str, MockUser] = {
    user.id: apply_role(user, user.role) for user in _mock_users
}
DEFAULT_USER_ID = _mock_users[0].id


_initial_containers = [
    Container(
        qr_code="QR123",
        name="Red Cryo Rack",
        contents=[
            Item(name="Genome of BRX1 (Frozen vials)", quantity=1),
            Item(name="BRX1 Swabs (Frozen)", quantity=2),
        ],
    ),
    Container(
        qr_code="QR456",
        name="Blue Storage Drawer",
        contents=[
            Item(name="Thermal Gloves", quantity=2),
            Item(name="PCR Tubes", quantity=4),
            Item(name="Parafilm Roll", quantity=1),
        ],
    ),
]

containers: Dict[str, Dict] = {
    container.qr_code: container.dict() for container in _initial_containers
}


def get_current_user(
    mock_user_id: Optional[str] = Header(None, alias="X-Mock-User"),
    mock_user_query: Optional[str] = Query(None, alias="mock_user"),
) -> MockUser:
    identifier = mock_user_id or mock_user_query
    if identifier is None:
        return mock_users[DEFAULT_USER_ID]

    user = mock_users.get(identifier)
    if not user:
        raise HTTPException(status_code=401, detail="Unknown mock user")

    return user


def require_permission(user: MockUser, permission: str) -> None:
    if permission not in user.permissions:
        raise HTTPException(status_code=403, detail="Insufficient permissions for this action")


class RoleUpdate(BaseModel):
    role: str


@app.get("/users", response_model=List[MockUser])
def list_users(current_user: MockUser = Depends(get_current_user)):
    # In this mock setup every user can see the available personas
    return list(mock_users.values())


@app.get("/users/{user_id}", response_model=MockUser)
def get_user(user_id: str, current_user: MockUser = Depends(get_current_user)):
    user = mock_users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/users/{user_id}/role", response_model=MockUser)
def set_user_role(
    user_id: str,
    update: RoleUpdate,
    current_user: MockUser = Depends(get_current_user),
):
    target = mock_users.get(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can change roles")

    if target.is_admin:
        raise HTTPException(status_code=400, detail="Cannot modify the primary admin role")

    updated = apply_role(target, update.role)
    mock_users[user_id] = updated
    return updated


@app.get("/roles", response_model=List[str])
def list_roles(current_user: MockUser = Depends(get_current_user)):
    return list(ROLE_PERMISSIONS.keys())


@app.get("/containers", response_model=List[Container])
def list_containers(search: Optional[str] = None, current_user: MockUser = Depends(get_current_user)):
    require_permission(current_user, VIEW_PERMISSION)
    """Return all containers or those matching the search term."""
    results = containers.values()
    if search:
        term = search.lower()
        filtered = []
        for data in results:
            if term in data["qr_code"].lower() or term in data["name"].lower():
                filtered.append(data)
                continue

            for item in data.get("contents", []):
                item_name = item.get("name", "").lower()
                quantity_text = str(item.get("quantity", "")).lower()
                if term in item_name or (quantity_text and term in quantity_text):
                    filtered.append(data)
                    break
        results = filtered

    return [Container(**data) for data in results]


@app.get("/containers/{qr_code}", response_model=Container)
def get_container(qr_code: str, current_user: MockUser = Depends(get_current_user)):
    require_permission(current_user, VIEW_PERMISSION)
    data = containers.get(qr_code)
    if not data:
        raise HTTPException(status_code=404, detail="Container not found")
    # print(data)
    return Container(**data)


@app.put("/containers/{qr_code}", response_model=Container)
def update_container(
    qr_code: str, container: Container, current_user: MockUser = Depends(get_current_user)
):
    require_permission(current_user, UPDATE_PERMISSION)
    if qr_code not in containers:
        raise HTTPException(status_code=404, detail="Container not found")
    if container.qr_code != qr_code:
        raise HTTPException(status_code=400, detail="QR code mismatch")

    containers[qr_code] = container.dict()
    return container


@app.post("/containers", response_model=Container, status_code=201)
def create_container(container: Container, current_user: MockUser = Depends(get_current_user)):
    require_permission(current_user, CREATE_PERMISSION)
    if container.qr_code in containers:
        raise HTTPException(status_code=400, detail="Container with this QR code already exists")

    containers[container.qr_code] = container.dict()
    return container


@app.get("/containers/{qr_code}/qrcode", responses={200: {"content": {"image/png": {}}}})
def generate_qr(qr_code: str, current_user: MockUser = Depends(get_current_user)):
    require_permission(current_user, VIEW_PERMISSION)
    if qr_code not in containers:
        raise HTTPException(status_code=404, detail="Container not found")

    frontend_url = os.getenv("FRONTEND_URL", f"http://localhost:5173/scan/{qr_code}")
    img = qrcode.make(frontend_url)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")
