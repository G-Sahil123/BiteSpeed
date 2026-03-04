from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timezone
from typing import Optional
from models import Contact, LinkPrecedence


def get_contacts_by_email_or_phone(
    db: Session, email: Optional[str], phone: Optional[str]
) -> list[Contact]:
    filters = []
    if email:
        filters.append(Contact.email == email)
    if phone:
        filters.append(Contact.phoneNumber == phone)

    if not filters:
        return []

    return (
        db.query(Contact)
        .filter(or_(*filters), Contact.deletedAt == None)
        .all()
    )


def get_all_linked_contacts(db: Session, primary_id: int) -> list[Contact]:
    primary = db.query(Contact).filter(Contact.id == primary_id).first()
    secondaries = (
        db.query(Contact)
        .filter(Contact.linkedId == primary_id, Contact.deletedAt == None)
        .all()
    )
    return [primary] + secondaries if primary else secondaries


def resolve_primary(db: Session, contacts: list[Contact]) -> Contact:
    primary_ids = set()
    for c in contacts:
        if c.linkPrecedence == LinkPrecedence.primary:
            primary_ids.add(c.id)
        elif c.linkedId:
            primary_ids.add(c.linkedId)

    primaries = (
        db.query(Contact)
        .filter(Contact.id.in_(primary_ids), Contact.deletedAt == None)
        .order_by(Contact.createdAt)
        .all()
    )
    return primaries[0] if primaries else contacts[0]


def merge_clusters(db: Session, winning_primary: Contact, losing_primary: Contact):
    now = datetime.now(timezone.utc)

    losing_primary.linkPrecedence = LinkPrecedence.secondary
    losing_primary.linkedId = winning_primary.id
    losing_primary.updatedAt = now
    db.flush()

    db.query(Contact).filter(
        Contact.linkedId == losing_primary.id,
        Contact.deletedAt == None
    ).update(
        {"linkedId": winning_primary.id, "updatedAt": now},
        synchronize_session="fetch"
    )
    db.flush()


def create_contact(
    db: Session,
    email: Optional[str],
    phone: Optional[str],
    linked_id: Optional[int],
    precedence: LinkPrecedence,
) -> Contact:
    now = datetime.now(timezone.utc)
    contact = Contact(
        email=email,
        phoneNumber=phone,
        linkedId=linked_id,
        linkPrecedence=precedence,
        createdAt=now,
        updatedAt=now,
    )
    db.add(contact)
    db.flush()
    return contact


def build_response_payload(db: Session, primary_id: int) -> dict:
    all_contacts = get_all_linked_contacts(db, primary_id)

    primary = next(c for c in all_contacts if c.id == primary_id)
    secondaries = [c for c in all_contacts if c.id != primary_id]

    seen_emails, seen_phones = set(), set()
    emails, phones = [], []

    for contact in [primary] + secondaries:
        if contact.email and contact.email not in seen_emails:
            seen_emails.add(contact.email)
            emails.append(contact.email)
        if contact.phoneNumber and contact.phoneNumber not in seen_phones:
            seen_phones.add(contact.phoneNumber)
            phones.append(contact.phoneNumber)

    return {
        "contact": {
            "primaryContatctId": primary.id,
            "emails": emails,
            "phoneNumbers": phones,
            "secondaryContactIds": [c.id for c in secondaries],
        }
    }


def identify(db: Session, email: Optional[str], phone: Optional[str]) -> dict:
    matched = get_contacts_by_email_or_phone(db, email, phone)

    if not matched:
        new_contact = create_contact(
            db, email, phone, linked_id=None, precedence=LinkPrecedence.primary
        )
        db.commit()
        db.refresh(new_contact)
        return build_response_payload(db, new_contact.id)

    root_primary_ids = set()
    for c in matched:
        if c.linkPrecedence == LinkPrecedence.primary:
            root_primary_ids.add(c.id)
        elif c.linkedId:
            root_primary_ids.add(c.linkedId)

    root_primaries = (
        db.query(Contact)
        .filter(Contact.id.in_(root_primary_ids), Contact.deletedAt == None)
        .order_by(Contact.createdAt)
        .all()
    )
    winning_primary = root_primaries[0]

    for other_primary in root_primaries[1:]:
        merge_clusters(db, winning_primary, other_primary)

    all_linked = get_all_linked_contacts(db, winning_primary.id)
    existing_emails = {c.email for c in all_linked if c.email}
    existing_phones = {c.phoneNumber for c in all_linked if c.phoneNumber}

    email_is_new = email and email not in existing_emails
    phone_is_new = phone and phone not in existing_phones

    if email_is_new or phone_is_new:
        create_contact(
            db,
            email=email,
            phone=phone,
            linked_id=winning_primary.id,
            precedence=LinkPrecedence.secondary,
        )

    db.commit()
    return build_response_payload(db, winning_primary.id)