"""
Parses the HTML Google Voice conversations files
"""

import warnings
from pathlib import Path
from datetime import datetime
from typing import List, Iterator

import bs4  # type: ignore[import]
from bs4.element import Tag  # type: ignore[import]

from ..models import Conversation, Contact, Jpeg, Message, MmsImage
from ..common import Res
from ..log import logger


def clean_latin1_chars(s: str) -> str:
    # these are latin1 encoded space characters, replace them with spaces
    return s.replace("\xa0", " ").replace("\u2003", " ")


def _parse_contact_div(div: bs4.element.Tag) -> List[Contact]:
    contacts = []
    for sender in div.select("cite.sender"):
        assert sender is not None
        tel = sender.select_one("a.tel")
        assert tel is not None
        assert tel.has_attr("href")
        contacts.append(Contact(tel.attrs["href"], tel.getText()))
    return contacts


def _parse_message_div(div: bs4.element.Tag) -> Message:
    contact = _parse_contact_div(div)
    assert len(contact) == 1
    contact = contact[0]

    dt = div.select_one("abbr.dt")
    assert dt is not None
    assert dt.has_attr("title")
    message_time = datetime.fromisoformat(dt.attrs["title"])

    q = div.select_one("q")
    assert q is not None
    q = clean_latin1_chars(q.get_text()) if q.get_text() != "" else None

    images = []
    for img in div.select("img"):
        assert img.has_attr("src")
        img_src = img.attrs["src"]
        assert img_src != "" and img_src is not None
        images.append(img_src)

    if q is None and len(images) == 0:
        logger.warning(f"Warning: Empty message found")

    if len(images) > 0:
        contents = MmsImage(images, q)
    else:
        contents = q

    return Message(message_time, contact, contents)


def _parse_html_call(p: Path) -> Iterator[Res[Conversation]]:
    soup = bs4.BeautifulSoup(p.read_text(), "lxml")

    # For group messages, parse the list of (other) participants
    participants = soup.select_one("div.participants")
    if participants:
        participants = _parse_contact_div(participants)

    other_participant = None

    pending = []

    for outer_div in soup.select("div.message"):
        try:
            message = _parse_message_div(outer_div)

            conversation_participants = None

            # For group messages, validate that the sender is in the conversation
            # or that the message was sent by "Me" (since the participants list
            # does not contain the "Me" reference)
            if participants:
                assert message.contact.tel != "tel:"
                assert message.contact in participants or message.contact.name == "Me"
                conversation_participants = participants

            # For one-on-one messages, only include the other person
            else:
                if other_participant is not None:
                    if message.contact.tel == "tel:":
                        message.contact = other_participant

                    assert (
                        message.contact == other_participant
                        or message.contact.name == "Me"
                    )
                elif message.contact.name != "Me" and message.contact.tel != "tel:":
                    other_participant = message.contact
                else:
                    pending.append(message)
                    continue

                conversation_participants = [other_participant]

            if len(pending) > 0:
                # For group messages, we shouldn't ever get pending messages
                assert participants is None
                # And we should have the other participant by this point
                assert other_participant is not None

                for m in pending:
                    if m.contact is None:
                        m.contact = other_participant

                    yield Conversation(conversation_participants, m)
                pending = []

            yield Conversation(conversation_participants, message)
        except Exception as ae:
            print(p)
            raise

    if len(pending) != 0:
        logger.warning(f"Unexpected pending messages: {p}")
        # TODO: figure out dynamically?
        # assert len(pending) == 0


_parse_html_call.return_type = Message  # type: ignore[attr-defined]


def _parse_image(p: Path) -> Iterator[Res[Jpeg]]:
    yield Jpeg(p)


_parse_image.return_type = Jpeg  # type: ignore[attr-defined]
