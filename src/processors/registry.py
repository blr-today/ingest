from .allevents import AllEvents
from .bhaagoindia import BhaagoIndia
from .bookmyshow import BookMyShow
from .cost import Cost
from .costly import Costly
from .district import District
from .eventtype import EventType
from .exhibition import Exhibition
from .geo import GeoProcessor
from .highape import HighApe
from .ignored_events import IgnoredEvents
from .koota import Koota
from .languages import ScriptLanguage
from .lastcall import LastCall
from .patch import Patch
from .schemafixer import SchemaFixer
from .venues import Venues

# Run in this order; a DROP skips the rest
PROCESSORS = [
    Koota,
    SchemaFixer,
    Costly,
    BookMyShow,
    Exhibition,
    GeoProcessor,
    AllEvents,
    BhaagoIndia,
    District,
    HighApe,
    IgnoredEvents,
    ScriptLanguage,
    Patch,
    Venues,
    EventType,
    Cost,
    LastCall,
]
