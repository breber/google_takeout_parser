"""
Models for the data parsed by this module

Each top-level dataclass here has a 'key' property
which determines unique events while merging
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Any, Union, Iterator, TYPE_CHECKING
from dataclasses import dataclass

from .common import Res


Details = str


# because of https://github.com/karlicoss/cachew/issues/28, need
# to do these as tuples instead of NamedTuples
MetaData = Optional[str]
# name, url, source, sourceUrl
LocationInfo = Tuple[MetaData, MetaData, MetaData, MetaData]

# name, url
Subtitles = Tuple[str, MetaData]

if TYPE_CHECKING:
    try:
        from typing import Protocol
    except ImportError:
        from typing_extensions import Protocol  # type: ignore[misc]
else:
    Protocol = object


class BaseEvent(Protocol):
    @property
    def key(self) -> Any:
        ...


@dataclass
class Activity(BaseEvent):
    header: str
    title: str
    time: datetime
    description: Optional[str]
    titleUrl: Optional[str]
    # note: in HTML exports, there is no way to tell the difference between
    # a description and a subtitle, so they end up as subtitles
    # more lines of text describing this
    subtitles: List[Subtitles]
    details: List[Details]
    locationInfos: List[LocationInfo]
    products: List[str]

    @property
    def dt(self) -> datetime:
        return self.time

    @property
    def products_desc(self) -> str:
        return ", ".join(sorted(self.products))

    @property
    def key(self) -> Tuple[str, str, int]:
        return (self.header, self.title, int(self.time.timestamp()))


@dataclass
class YoutubeComment(BaseEvent):
    content: str
    dt: datetime
    urls: List[str]

    @property
    def key(self) -> int:
        return int(self.dt.timestamp())


@dataclass
class LikedYoutubeVideo(BaseEvent):
    title: str
    desc: str
    link: str
    dt: datetime

    @property
    def key(self) -> int:
        return int(self.dt.timestamp())


@dataclass
class PlayStoreAppInstall(BaseEvent):
    title: str
    dt: datetime
    device_name: Optional[str]

    @property
    def key(self) -> int:
        return int(self.dt.timestamp())


@dataclass
class Location(BaseEvent):
    lng: float
    lat: float
    accuracy: Optional[int]
    dt: datetime

    @property
    def key(self) -> Tuple[float, float, Optional[int], int]:
        return (self.lng, self.lat, self.accuracy, int(self.dt.timestamp()))


@dataclass
class ChromeHistory(BaseEvent):
    title: str
    url: str
    dt: datetime

    @property
    def key(self) -> Tuple[str, int]:
        return (self.url, int(self.dt.timestamp()))


@dataclass
class Contact(BaseEvent):
    tel: str
    name: str

    @property
    def key(self) -> str:
        return self.tel

    def __str__(self) -> str:
        if self.name is None or len(self.name) == 0:
            return self.tel
        return self.name


@dataclass
class MmsImage(BaseEvent):
    sources: List[str]
    message: Optional[str]

    @property
    def key(self) -> str:
        return "|".join(self.sources)

    def __str__(self) -> str:
        if self.message:
            return f"{self.key}: {self.message}"
        else:
            return self.key


@dataclass
class Message(BaseEvent):
    dt: datetime
    contact: Contact
    message: Union[str, MmsImage]

    @property
    def key(self) -> Tuple[datetime, Contact]:
        return (self.dt, self.contact)

    def __str__(self) -> str:
        return f"{datetime.strftime(self.dt, '%c')} - {self.contact}: {self.message}"


@dataclass
class Conversation(BaseEvent):
    contacts: List[Contact]
    message: Message

    @property
    def key(self) -> List[Contact]:
        return self.contacts


@dataclass
class Jpeg(BaseEvent):
    path: Path

    @property
    def key(self) -> Path:
        return self.path


# cant compute this dynamically -- have to write it out
# if you want to override, override both global variable types with new types
DEFAULT_MODEL_TYPE = Union[
    Activity,
    LikedYoutubeVideo,
    PlayStoreAppInstall,
    Location,
    ChromeHistory,
    YoutubeComment,
    Contact,
    Message,
    Conversation,
    Jpeg,
]

CacheResults = Iterator[Res[DEFAULT_MODEL_TYPE]]
