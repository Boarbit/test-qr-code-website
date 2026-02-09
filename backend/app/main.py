from fastapi import Depends, FastAPI, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Tuple
import csv
import io
import json
import os
import qrcode
from sqlalchemy.orm import Session

from .database import Base, engine, get_db, SessionLocal
from . import models, crud

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
    details: Optional[Dict[str, str]] = None


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

DEFAULT_CONTAINER_FIELDS = ["qr_code", "name"]
ALLOWED_CONTAINER_FIELDS = set(DEFAULT_CONTAINER_FIELDS)

DEFAULT_ITEM_FIELDS = ["name", "quantity"]
ALLOWED_ITEM_FIELDS = set(DEFAULT_ITEM_FIELDS)


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

Base.metadata.create_all(bind=engine)


def seed_initial_data():
    db = SessionLocal()
    try:
        if crud.count_containers(db) == 0:
            for container in _initial_containers:
                crud.create_container(
                    db,
                    qr_code=container.qr_code,
                    name=container.name,
                    items=[
                        {
                            "name": item.name,
                            "quantity": item.quantity,
                            "details": item.details,
                        }
                        for item in container.contents
                    ],
                )
    finally:
        db.close()


seed_initial_data()


def item_model_to_schema(model: models.ItemModel) -> Item:
    details = None
    if model.details:
        try:
            details = json.loads(model.details)
        except json.JSONDecodeError:
            details = None
    return Item(name=model.name, quantity=model.quantity, details=details)


def container_model_to_schema(model: models.ContainerModel) -> Container:
    return Container(
        qr_code=model.qr_code,
        name=model.name,
        contents=[item_model_to_schema(item) for item in model.items],
    )


def serialized_items_from_container(container: Container) -> List[Dict]:
    return [
        {"name": item.name, "quantity": item.quantity, "details": item.details}
        for item in container.contents
    ]


def matches_search(container: Container, term: str) -> bool:
    lowered = term.lower()
    if lowered in container.qr_code.lower() or lowered in container.name.lower():
        return True

    for item in container.contents:
        if lowered in item.name.lower():
            return True
        quantity_text = str(item.quantity)
        if quantity_text and lowered in quantity_text.lower():
            return True
    return False


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


def normalize_field_list(
    values: Optional[List[str]], allowed: set, default_fields: List[str]
) -> List[str]:
    if values is None:
        return list(default_fields)

    normalized: List[str] = []
    seen = set()
    for value in values:
        trimmed = value.strip()
        if not trimmed:
            continue
        if trimmed not in allowed:
            raise HTTPException(status_code=400, detail=f"Unknown field '{trimmed}'")
        if trimmed not in seen:
            normalized.append(trimmed)
            seen.add(trimmed)

    return normalized


def normalize_detail_keys(keys: Optional[List[str]]) -> Tuple[List[str], bool]:
    if keys is None:
        return [], False

    normalized: List[str] = []
    seen = set()
    for key in keys:
        trimmed = key.strip()
        if trimmed and trimmed not in seen:
            normalized.append(trimmed)
            seen.add(trimmed)
    return normalized, True


def normalize_qr_codes(values: Optional[List[str]]) -> List[str]:
    if not values:
        return []

    normalized: List[str] = []
    seen = set()
    for value in values:
        trimmed = value.strip()
        if trimmed and trimmed not in seen:
            normalized.append(trimmed)
            seen.add(trimmed)
    return normalized


def parse_item_filters(raw_filters: Optional[List[str]]) -> List[Tuple[str, str]]:
    parsed: List[Tuple[str, str]] = []
    if not raw_filters:
        return parsed

    for raw in raw_filters:
        field, separator, value = raw.partition(":")
        field = field.strip()
        value = value.strip()
        if not separator or not field or not value:
            raise HTTPException(
                status_code=400, detail="Filters must be formatted as field:value pairs"
            )
        parsed.append((field, value))

    return parsed


def item_matches_filters(item: Item, filters: List[Tuple[str, str]]) -> bool:
    for field, expected in filters:
        expected_lower = expected.lower()
        if field == "name":
            if expected_lower not in item.name.lower():
                return False
        elif field == "quantity":
            if str(item.quantity) != expected:
                return False
        elif field.startswith("detail."):
            key = field.split(".", 1)[1]
            details = item.details or {}
            value = details.get(key)
            if value is None or expected_lower not in value.lower():
                return False
        else:
            raise HTTPException(
                status_code=400,
                detail="Filters support 'name', 'quantity', or 'detail.<key>' fields",
            )
    return True


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
def list_containers(
    search: Optional[str] = None,
    current_user: MockUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_permission(current_user, VIEW_PERMISSION)
    records = crud.list_containers(db)
    containers_list = [container_model_to_schema(record) for record in records]

    if search:
        containers_list = [container for container in containers_list if matches_search(container, search)]

    return containers_list


@app.get("/containers/export")
def export_containers_csv(
    container_fields: Optional[List[str]] = Query(default=None),
    item_fields: Optional[List[str]] = Query(default=None),
    detail_keys: Optional[List[str]] = Query(default=None),
    item_filter: Optional[List[str]] = Query(default=None),
    container_qr: Optional[List[str]] = Query(default=None),
    current_user: MockUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_permission(current_user, VIEW_PERMISSION)

    resolved_container_fields = normalize_field_list(
        container_fields, ALLOWED_CONTAINER_FIELDS, DEFAULT_CONTAINER_FIELDS
    )
    resolved_item_fields = normalize_field_list(
        item_fields, ALLOWED_ITEM_FIELDS, DEFAULT_ITEM_FIELDS
    )
    normalized_detail_keys, detail_keys_requested = normalize_detail_keys(detail_keys)
    filters = parse_item_filters(item_filter)
    has_filters = bool(filters)
    selected_qr_codes = normalize_qr_codes(container_qr)
    selected_qr_set = set(selected_qr_codes)

    prepared_rows: List[Tuple[Container, Optional[Item]]] = []
    auto_detail_keys: List[str] = []
    seen_detail_keys = set()
    include_items = bool(resolved_item_fields or normalized_detail_keys or detail_keys_requested)

    records = crud.list_containers(db)
    containers_list = [container_model_to_schema(record) for record in records]
    if selected_qr_set:
        containers_list = [
            container for container in containers_list if container.qr_code in selected_qr_set
        ]

    for container in containers_list:
        contents = list(container.contents or [])
        if has_filters:
            matching_items = [item for item in contents if item_matches_filters(item, filters)]
            if not matching_items:
                continue
            row_items: List[Optional[Item]] = matching_items
        else:
            row_items = contents or [None]

        if include_items:
            for item in row_items:
                prepared_rows.append((container, item))
                if item and item.details:
                    for key in item.details.keys():
                        if key not in seen_detail_keys:
                            seen_detail_keys.add(key)
                            auto_detail_keys.append(key)
        else:
            prepared_rows.append((container, None))

    selected_detail_keys = normalized_detail_keys if detail_keys_requested else auto_detail_keys

    header: List[str] = []
    header.extend([f"container_{field}" for field in resolved_container_fields])
    header.extend([f"item_{field}" for field in resolved_item_fields])
    header.extend([f"detail_{key}" for key in selected_detail_keys])

    if not header:
        raise HTTPException(status_code=400, detail="Select at least one column to export.")

    def stream_rows():
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        writer.writerow(header)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)

        for container, item in prepared_rows:
            row: List[str] = []
            for field in resolved_container_fields:
                value = getattr(container, field, "")
                row.append("" if value is None else str(value))

            for field in resolved_item_fields:
                if item is None:
                    row.append("")
                else:
                    value = getattr(item, field, "")
                    row.append("" if value is None else str(value))

            detail_source = item.details if (item and item.details) else {}
            for key in selected_detail_keys:
                detail_value = detail_source.get(key)
                row.append("" if detail_value is None else str(detail_value))

            writer.writerow(row)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    filename = "containers-export.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(stream_rows(), media_type="text/csv", headers=headers)


@app.get("/containers/{qr_code}", response_model=Container)
def get_container(
    qr_code: str,
    current_user: MockUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_permission(current_user, VIEW_PERMISSION)
    data = crud.get_container_by_qr(db, qr_code)
    if not data:
        raise HTTPException(status_code=404, detail="Container not found")
    return container_model_to_schema(data)


@app.put("/containers/{qr_code}", response_model=Container)
def update_container(
    qr_code: str,
    container: Container,
    current_user: MockUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_permission(current_user, UPDATE_PERMISSION)
    existing = crud.get_container_by_qr(db, qr_code)
    if not existing:
        raise HTTPException(status_code=404, detail="Container not found")
    if container.qr_code != qr_code:
        raise HTTPException(status_code=400, detail="QR code mismatch")

    updated = crud.update_container(
        db,
        existing,
        name=container.name,
        items=serialized_items_from_container(container),
    )
    return container_model_to_schema(updated)


@app.delete("/containers/{qr_code}", status_code=204)
def delete_container_endpoint(
    qr_code: str,
    current_user: MockUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_permission(current_user, UPDATE_PERMISSION)
    existing = crud.get_container_by_qr(db, qr_code)
    if not existing:
        raise HTTPException(status_code=404, detail="Container not found")

    crud.delete_container(db, existing)


@app.post("/containers", response_model=Container, status_code=201)
def create_container(
    container: Container,
    current_user: MockUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_permission(current_user, CREATE_PERMISSION)
    existing = crud.get_container_by_qr(db, container.qr_code)
    if existing:
        raise HTTPException(status_code=400, detail="Container with this QR code already exists")

    saved = crud.create_container(
        db,
        qr_code=container.qr_code,
        name=container.name,
        items=serialized_items_from_container(container),
    )
    return container_model_to_schema(saved)


@app.get("/containers/{qr_code}/qrcode", responses={200: {"content": {"image/png": {}}}})
def generate_qr(qr_code: str, current_user: MockUser = Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission(current_user, VIEW_PERMISSION)
    existing = crud.get_container_by_qr(db, qr_code)
    if not existing:
        raise HTTPException(status_code=404, detail="Container not found")

    frontend_url = os.getenv("FRONTEND_URL", f"http://localhost:5173/scan/{qr_code}")
    img = qrcode.make(frontend_url)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")
