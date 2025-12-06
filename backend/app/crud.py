from __future__ import annotations

import json
from typing import List, Optional

from sqlalchemy.orm import Session, selectinload

from . import models


def list_containers(db: Session) -> List[models.ContainerModel]:
    return (
        db.query(models.ContainerModel)
        .options(selectinload(models.ContainerModel.items))
        .order_by(models.ContainerModel.id)
        .all()
    )


def get_container_by_qr(db: Session, qr_code: str) -> Optional[models.ContainerModel]:
    return (
        db.query(models.ContainerModel)
        .options(selectinload(models.ContainerModel.items))
        .filter(models.ContainerModel.qr_code == qr_code)
        .first()
    )


def count_containers(db: Session) -> int:
    return db.query(models.ContainerModel).count()


def create_container(db: Session, qr_code: str, name: str, items: List[dict]):
    container = models.ContainerModel(qr_code=qr_code, name=name)
    db.add(container)
    db.flush()

    for item in items:
        db_item = models.ItemModel(
            container_id=container.id,
            name=item["name"],
            quantity=item["quantity"],
            details=json.dumps(item["details"]) if item.get("details") else None,
        )
        db.add(db_item)

    db.commit()
    db.refresh(container)
    return container


def update_container(db: Session, container: models.ContainerModel, name: str, items: List[dict]):
    container.name = name
    container.items.clear()
    db.flush()

    for item in items:
        db_item = models.ItemModel(
            container_id=container.id,
            name=item["name"],
            quantity=item["quantity"],
            details=json.dumps(item["details"]) if item.get("details") else None,
        )
        container.items.append(db_item)

    db.commit()
    db.refresh(container)
    return container


def delete_container(db: Session, container: models.ContainerModel):
    db.delete(container)
    db.commit()
