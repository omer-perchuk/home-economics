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


def remember_user_category_choice(
    db: Session,
    user_id: Optional[int],
    family_id: Optional[int],
    source_text: Optional[str],
    category: str,
    tx_type: str,
):
    if not source_text or not category or not tx_type:
        return

    merchant_key = extract_merchant_key(source_text)
    if not merchant_key:
        return

    if user_id is not None:
        upsert_memory(
            db,
            scope_type="user",
            scope_id=user_id,
            merchant_key=merchant_key,
            category=category,
            tx_type=tx_type,
        )

    if family_id is not None:
        upsert_memory(
            db,
            scope_type="family",
            scope_id=family_id,
            merchant_key=merchant_key,
            category=category,
            tx_type=tx_type,
        )

    upsert_memory(
        db,
        scope_type="global",
        scope_id=None,
        merchant_key=merchant_key,
        category=category,
        tx_type=tx_type,
    )


def remember_transaction_choice(
    db: Session,
    user_id: Optional[int],
    family_id: Optional[int],
    original_text: Optional[str],
    description: Optional[str],
    category: str,
    tx_type: str,
):
    candidate_texts = []

    for value in [original_text, description]:
        normalized = (value or "").strip()
        if normalized and normalized not in candidate_texts:
            candidate_texts.append(normalized)

    for text in candidate_texts:
        remember_user_category_choice(
            db=db,
            user_id=user_id,
            family_id=family_id,
            source_text=text,
            category=category,
            tx_type=tx_type,
        )
