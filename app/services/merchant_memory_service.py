from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional

from app.db.models import MerchantMemory


def extract_merchant_key(text: str) -> str:
    cleaned = text.strip().lower()

    parts = cleaned.split()
    words = []

    for p in parts:
        if any(ch.isdigit() for ch in p):
            continue
        words.append(p)

    if not words:
        return cleaned

    return " ".join(words[:2]).strip()



def upsert_memory(
    db: Session,
    scope_type: str,
    scope_id: Optional[int],
    merchant_key: str,
    category: str,
    tx_type: str,
):
    memory = (
        db.query(MerchantMemory)
        .filter(
            MerchantMemory.scope_type == scope_type,
            MerchantMemory.scope_id == scope_id,
            MerchantMemory.merchant_key == merchant_key,
            MerchantMemory.category == category,
            MerchantMemory.tx_type == tx_type,
        )
        .first()
    )

    if memory:
        memory.count += 1
        memory.last_used_at = datetime.utcnow()
    else:
        memory = MerchantMemory(
            scope_type=scope_type,
            scope_id=scope_id,
            merchant_key=merchant_key,
            category=category,
            tx_type=tx_type,
            count=1,
            last_used_at=datetime.utcnow(),
        )
        db.add(memory)

    db.commit()
    db.refresh(memory)
    return memory

def find_memory_candidates(db: Session, user_id: int, family_id: int, merchant_key: str):
    user_memories = (
        db.query(MerchantMemory)
        .filter(
            MerchantMemory.scope_type == "user",
            MerchantMemory.scope_id == user_id,
            MerchantMemory.merchant_key == merchant_key,
        )
        .order_by(MerchantMemory.count.desc())
        .all()
    )

    family_memories = (
        db.query(MerchantMemory)
        .filter(
            MerchantMemory.scope_type == "family",
            MerchantMemory.scope_id == family_id,
            MerchantMemory.merchant_key == merchant_key,
        )
        .order_by(MerchantMemory.count.desc())
        .all()
    )

    global_memories = (
        db.query(MerchantMemory)
        .filter(
            MerchantMemory.scope_type == "global",
            MerchantMemory.merchant_key == merchant_key,
        )
        .order_by(MerchantMemory.count.desc())
        .all()
    )

    return {
        "user": user_memories,
        "family": family_memories,
        "global": global_memories,
    }