"""Seed the demo database.

Produces:
- 20 users across 6 Ditto campuses: 6 UC Berkeley, 6 UC San Diego, 2 UCLA,
  2 USC, 2 UC Davis, 2 San Jose State. Flagships stay heavy because that is
  where the scripted scenarios run and where the matching engine has the most
  history; the new-campus cohort is lighter on purpose.
- 46 venues (15 UC Berkeley, 15 UC San Diego, 4 each at UCLA, USC, UC Davis,
  San Jose State) with tags the Venue Agent retrieves on. New-campus venues
  are placed in the neighborhoods each school actually dates in: Westwood
  for UCLA, USC Village for USC, downtown Davis for UC Davis, the SoFA
  district for San Jose State.
- 6 current matches -> 6 current dates (4 completed, 1 canceled, 1 scheduled).
  These are the "live" cohort the dashboard shows; scenario triggers create
  new matches/dates on top of them.
- 30 historical afters_sessions distributed across the last 14 days, weighted
  heavier on the flagships (9 UC Berkeley, 9 UC San Diego, 5 UCLA, 3 USC,
  2 UC Davis, 2 San Jose State). Outcome mix: ~35% both_again, ~20% both_group,
  ~15% both_pass, ~20% asymmetric, ~10% timed_out. Targets ~90%
  resolved-within-24h and ~10% ghost rate on the Metrics tiles.
- 30 rows appended to afters-orchestrator/feedback_training.jsonl so the
  "model signal density" tile opens non-zero.

Run:  pnpm seed    (or)    python -m scripts.seed
"""

from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from afters.db.mongo import collections, ensure_indexes, get_db
from afters.models import (
    AftersSession,
    DateRecord,
    FeedbackTrainingRow,
    Match,
    ParticipantDebrief,
    User,
    UserProfile,
    Venue,
)

FEEDBACK_FILE = Path(__file__).resolve().parents[1] / "feedback_training.jsonl"


# ---------- user cohort ----------

USERS = [
    # UC Berkeley
    {
        "name": "Maya Chen",
        "campus": "UC Berkeley",
        "year": "sophomore",
        "pronouns": "she/her",
        "edu_email": "maya.chen@berkeley.edu",
        "interests": ["chess", "dim sum", "weird noodles", "studio ghibli"],
        "preferences": ["quiet venues", "walking conversations"],
        "persona": (
            "loves dim sum and weird noodle spots. does chess puzzles at the "
            "Bancroft-Telegraph benches. quiet laugher, allergic to small talk."
        ),
        "avatar_color": "#F4A261",
    },
    {
        "name": "Jordan Park",
        "campus": "UC Berkeley",
        "year": "junior",
        "pronouns": "they/them",
        "edu_email": "j.park@berkeley.edu",
        "interests": ["typefaces", "film photography", "coffee"],
        "preferences": ["walking over sitting", "daytime plans"],
        "persona": (
            "collects typefaces. films their coffee. prefers walking over sitting. "
            "gets shy when complimented. wears one earring."
        ),
        "avatar_color": "#E76F51",
    },
    {
        "name": "Rohan Gupta",
        "campus": "UC Berkeley",
        "year": "senior",
        "pronouns": "he/him",
        "edu_email": "rohan.g@berkeley.edu",
        "interests": ["run clubs", "novels", "indian home cooking"],
        "preferences": ["morning plans", "good conversation"],
        "persona": (
            "6am run club regular. always asking what youve read lately. laughs "
            "loud, gives compliments on purpose."
        ),
        "avatar_color": "#2A9D8F",
    },
    {
        "name": "Aditi Shah",
        "campus": "UC Berkeley",
        "year": "junior",
        "pronouns": "she/her",
        "edu_email": "aditi.shah@berkeley.edu",
        "interests": ["campaign finance", "bao", "oat lattes", "debate team"],
        "preferences": ["thoughtful venues", "coffee shops"],
        "persona": (
            "will argue about campaign finance for four hours. obsessed with bao. "
            "drinks oat lattes only. has opinions."
        ),
        "avatar_color": "#E9C46A",
    },
    {
        "name": "Sam Rivera",
        "campus": "UC Berkeley",
        "year": "freshman",
        "pronouns": "he/him",
        "edu_email": "sam.rivera@berkeley.edu",
        "interests": ["skateboarding", "lofi production", "tacos"],
        "preferences": ["chill", "outdoor"],
        "persona": (
            "skates at Cesar Chavez park. low-key makes lofi beats. "
            "says everything is 'tight'."
        ),
        "avatar_color": "#264653",
    },
    {
        "name": "Lucas Kim",
        "campus": "UC Berkeley",
        "year": "sophomore",
        "pronouns": "he/him",
        "edu_email": "lucas.kim@berkeley.edu",
        "interests": ["synths", "KALX shows", "philosophy"],
        "preferences": ["live music", "quieter afterward"],
        "persona": (
            "makes synth beats in his dorm. goes to every KALX show. quiet but "
            "funny once he warms up."
        ),
        "avatar_color": "#8D99AE",
    },
    # UC San Diego
    {
        "name": "Priya Patel",
        "campus": "UC San Diego",
        "year": "sophomore",
        "pronouns": "she/her",
        "edu_email": "priya.patel@ucsd.edu",
        "interests": ["painting", "pre-med", "sunday walks", "black coffee"],
        "preferences": ["outdoor walks", "daytime"],
        "persona": (
            "pre-med but also a painter. drinks black coffee. walks Torrey Pines "
            "every sunday like clockwork."
        ),
        "avatar_color": "#EF476F",
    },
    {
        "name": "Ethan Wu",
        "campus": "UC San Diego",
        "year": "senior",
        "pronouns": "he/him",
        "edu_email": "ethan.wu@ucsd.edu",
        "interests": ["burritos", "surfing", "engineering"],
        "preferences": ["good food", "active plans"],
        "persona": (
            "has strong opinions about burritos. surfs at la jolla. tends to "
            "overexplain how things work."
        ),
        "avatar_color": "#06AED5",
    },
    {
        "name": "Zoe Martinez",
        "campus": "UC San Diego",
        "year": "junior",
        "pronouns": "she/her",
        "edu_email": "zoe.m@ucsd.edu",
        "interests": ["zines", "journalism", "foreign cinema"],
        "preferences": ["quieter plans", "no loud clubs"],
        "persona": (
            "writes zines. wants to be a foreign correspondent. refuses loud "
            "clubs on principle."
        ),
        "avatar_color": "#F9844A",
    },
    {
        "name": "Noah Osei",
        "campus": "UC San Diego",
        "year": "freshman",
        "pronouns": "he/him",
        "edu_email": "noah.o@ucsd.edu",
        "interests": ["Hong Kong cinema", "film scoring"],
        "preferences": ["corner booths", "dimmer rooms"],
        "persona": (
            "obsessed with Hong Kong cinema. will quote Wong Kar-wai unprompted. "
            "loves a corner booth."
        ),
        "avatar_color": "#277DA1",
    },
    {
        "name": "Lena Schmidt",
        "campus": "UC San Diego",
        "year": "grad",
        "pronouns": "she/her",
        "edu_email": "l.schmidt@ucsd.edu",
        "interests": ["cognitive science", "reading three books at once"],
        "preferences": ["bookstores", "quiet cafes"],
        "persona": (
            "reads three books at once. drinks only bubly. patient listener, "
            "asks the followup question you didnt expect."
        ),
        "avatar_color": "#90BE6D",
    },
    {
        "name": "Tyler Brooks",
        "campus": "UC San Diego",
        "year": "sophomore",
        "pronouns": "he/him",
        "edu_email": "tyler.b@ucsd.edu",
        "interests": ["rock climbing", "card tricks", "vegetarian cooking"],
        "preferences": ["active plans", "casual"],
        "persona": (
            "rock climber. vegetarian mostly. will absolutely teach you his "
            "card tricks if you ask."
        ),
        "avatar_color": "#43AA8B",
    },
    # UCLA
    {
        "name": "Emma Nakamura",
        "campus": "UCLA",
        "year": "junior",
        "pronouns": "she/her",
        "edu_email": "emma.n@ucla.edu",
        "interests": ["jim jarmusch films", "vintage jackets", "hammer museum"],
        "preferences": ["indie screenings", "walking conversations"],
        "persona": (
            "dragged her roommates to three screenings at the hammer last week. "
            "wears exclusively vintage lee jackets. quotes mystery train unprompted."
        ),
        "avatar_color": "#A78BFA",
    },
    {
        "name": "Miguel Soto",
        "campus": "UCLA",
        "year": "senior",
        "pronouns": "he/him",
        "edu_email": "miguel.s@ucla.edu",
        "interests": ["legal aid", "over-sweetened coffee", "volunteering"],
        "preferences": ["morning plans", "longform conversation"],
        "persona": (
            "volunteers every saturday at la legal aid. drinks his coffee with "
            "four sugars. asks probing follow-up questions."
        ),
        "avatar_color": "#60A5FA",
    },
    # USC
    {
        "name": "Chloe Bennett",
        "campus": "USC",
        "year": "sophomore",
        "pronouns": "she/her",
        "edu_email": "chloe.b@usc.edu",
        "interests": ["hackathons", "matcha", "design systems"],
        "preferences": ["ambitious plans", "walking around"],
        "persona": (
            "pitched at three hackathons last quarter and won two. drinks matcha "
            "religiously. says 'lock in' as a greeting."
        ),
        "avatar_color": "#F472B6",
    },
    {
        "name": "Diego Ruiz",
        "campus": "USC",
        "year": "freshman",
        "pronouns": "he/him",
        "edu_email": "diego.r@usc.edu",
        "interests": ["film cameras", "sourdough", "gene sequencing"],
        "preferences": ["quieter spots", "daytime"],
        "persona": (
            "collects old contax cameras. bakes bread on sundays. will explain "
            "gene sequencing at length if you let him."
        ),
        "avatar_color": "#34D399",
    },
    # UC Davis
    {
        "name": "Hana Yamamoto",
        "campus": "UC Davis",
        "year": "junior",
        "pronouns": "she/her",
        "edu_email": "hana.y@ucdavis.edu",
        "interests": ["espresso extraction", "knitting", "cafe-hopping"],
        "preferences": ["coffee-first plans", "bookstores"],
        "persona": (
            "strong opinions about espresso extraction. drives to every cafe "
            "between davis and sacramento. knits during lectures."
        ),
        "avatar_color": "#FBBF24",
    },
    {
        "name": "Ollie Brennan",
        "campus": "UC Davis",
        "year": "sophomore",
        "pronouns": "he/him",
        "edu_email": "ollie.b@ucdavis.edu",
        "interests": ["lo-fi beats", "farmers market", "pizza rankings"],
        "preferences": ["food-forward", "casual"],
        "persona": (
            "runs a food blog about the davis farmers market. makes lo-fi beats "
            "at 2am. keeps a spreadsheet of favorite pizza places."
        ),
        "avatar_color": "#22D3EE",
    },
    # San Jose State
    {
        "name": "Nina Kapoor",
        "campus": "San Jose State",
        "year": "sophomore",
        "pronouns": "she/her",
        "edu_email": "nina.k@sjsu.edu",
        "interests": ["salsa dancing", "java debugging", "improv comedy"],
        "preferences": ["active plans", "lively venues"],
        "persona": (
            "salsa dances every wednesday. debugs java in her sleep. laughs at "
            "her own jokes first and that is somehow endearing."
        ),
        "avatar_color": "#FB7185",
    },
    {
        "name": "Luis Mendez",
        "campus": "San Jose State",
        "year": "senior",
        "pronouns": "he/him",
        "edu_email": "luis.m@sjsu.edu",
        "interests": ["street photography", "film stock", "editing captions"],
        "preferences": ["dawn walks", "gallery-ish spots"],
        "persona": (
            "shoots street photos on film. gets up at 5am to catch the light. "
            "will edit your instagram captions for free."
        ),
        "avatar_color": "#818CF8",
    },
]

# ---------- venues ----------

VENUES = [
    # UC Berkeley
    {"name": "Blue Bottle Coffee", "campus": "UC Berkeley", "type": "cafe",
     "tags": ["coffee", "daytime", "quiet", "walking"], "vibe": "bright, minimal, clean espresso",
     "address": "2118 University Ave", "price_level": 2, "walking_distance_from_campus_min": 6},
    {"name": "Caffe Strada", "campus": "UC Berkeley", "type": "cafe",
     "tags": ["coffee", "daytime", "outdoor", "people_watching"], "vibe": "classic student hangout, big patio",
     "address": "2300 College Ave", "price_level": 1, "walking_distance_from_campus_min": 3},
    {"name": "Philz Coffee (Shattuck)", "campus": "UC Berkeley", "type": "cafe",
     "tags": ["coffee", "daytime", "cozy", "walking"], "vibe": "pour-over, slow chat",
     "address": "1600 Shattuck Ave", "price_level": 2, "walking_distance_from_campus_min": 12},
    {"name": "Cheeseboard Collective", "campus": "UC Berkeley", "type": "pizza",
     "tags": ["casual", "cheap", "outdoor", "daytime", "food_forward"], "vibe": "cooperative pizza, lively",
     "address": "1512 Shattuck Ave", "price_level": 1, "walking_distance_from_campus_min": 14},
    {"name": "Ippuku", "campus": "UC Berkeley", "type": "izakaya",
     "tags": ["dinner", "japanese", "quiet", "low_alcohol", "date_night"], "vibe": "warm izakaya, small plates",
     "address": "2130 Center St", "price_level": 3, "walking_distance_from_campus_min": 8},
    {"name": "Fava", "campus": "UC Berkeley", "type": "italian",
     "tags": ["italian", "date_night", "quiet", "food_forward"], "vibe": "small italian plates, candlelit",
     "address": "1801 Shattuck Ave", "price_level": 3, "walking_distance_from_campus_min": 10},
    {"name": "Kirala", "campus": "UC Berkeley", "type": "sushi",
     "tags": ["sushi", "dinner", "conversation"], "vibe": "reliable sushi, booths",
     "address": "2100 Ward St", "price_level": 2, "walking_distance_from_campus_min": 15},
    {"name": "Zachary's Pizza", "campus": "UC Berkeley", "type": "pizza",
     "tags": ["casual", "group_friendly", "loud", "cheap"], "vibe": "chicago deep-dish, group vibe",
     "address": "1853 Solano Ave", "price_level": 2, "walking_distance_from_campus_min": 20},
    {"name": "Tilden Regional Park", "campus": "UC Berkeley", "type": "park",
     "tags": ["outdoor", "active", "daytime", "walking", "hike"], "vibe": "trails, lake, big sky",
     "address": "2501 Grizzly Peak Blvd", "price_level": 1, "walking_distance_from_campus_min": 25},
    {"name": "Lawrence Hall of Science", "campus": "UC Berkeley", "type": "museum",
     "tags": ["museum", "daytime", "creative", "walking"], "vibe": "kid-friendly but views are unreal",
     "address": "1 Centennial Dr", "price_level": 2, "walking_distance_from_campus_min": 20},
    {"name": "Berkeley Marina", "campus": "UC Berkeley", "type": "waterfront",
     "tags": ["outdoor", "walking", "daytime", "water", "quiet"], "vibe": "sailboats, long promenade",
     "address": "201 University Ave", "price_level": 1, "walking_distance_from_campus_min": 20},
    {"name": "Saha Cafe", "campus": "UC Berkeley", "type": "cafe",
     "tags": ["coffee", "daytime", "quiet", "bookish"], "vibe": "bright, lots of tables, chill music",
     "address": "2509 Telegraph Ave", "price_level": 2, "walking_distance_from_campus_min": 5},
    {"name": "Agrodolce", "campus": "UC Berkeley", "type": "italian",
     "tags": ["italian", "daytime", "outdoor", "food_forward"], "vibe": "counter-service pasta, bright",
     "address": "1730 Shattuck Ave", "price_level": 2, "walking_distance_from_campus_min": 11},
    {"name": "Moe's Books", "campus": "UC Berkeley", "type": "bookstore",
     "tags": ["bookish", "quiet", "daytime", "walking"], "vibe": "4 floors, smells like old books",
     "address": "2476 Telegraph Ave", "price_level": 1, "walking_distance_from_campus_min": 4},
    {"name": "Jupiter", "campus": "UC Berkeley", "type": "beer garden",
     "tags": ["dinner", "nightlife", "loud", "group_friendly"], "vibe": "beer garden, pizza, crowds",
     "address": "2181 Shattuck Ave", "price_level": 2, "walking_distance_from_campus_min": 9},

    # UC San Diego
    {"name": "James Coffee Co", "campus": "UC San Diego", "type": "cafe",
     "tags": ["coffee", "daytime", "quiet", "walking"], "vibe": "modern, good pour-overs",
     "address": "2355 India St", "price_level": 2, "walking_distance_from_campus_min": 15},
    {"name": "Better Buzz Coffee", "campus": "UC San Diego", "type": "cafe",
     "tags": ["coffee", "daytime", "outdoor", "casual"], "vibe": "big outdoor seating, friendly",
     "address": "4755 Voltaire St", "price_level": 2, "walking_distance_from_campus_min": 10},
    {"name": "Bread & Cie", "campus": "UC San Diego", "type": "bakery",
     "tags": ["daytime", "casual", "food_forward"], "vibe": "french bakery, brunch vibe",
     "address": "350 University Ave", "price_level": 2, "walking_distance_from_campus_min": 12},
    {"name": "Cesarina", "campus": "UC San Diego", "type": "italian",
     "tags": ["italian", "date_night", "quiet", "food_forward"], "vibe": "handmade pasta, romantic",
     "address": "4161 Voltaire St", "price_level": 3, "walking_distance_from_campus_min": 14},
    {"name": "Kettner Exchange", "campus": "UC San Diego", "type": "upscale",
     "tags": ["dinner", "date_night", "food_forward"], "vibe": "design-forward, strong food",
     "address": "2001 Kettner Blvd", "price_level": 3, "walking_distance_from_campus_min": 16},
    {"name": "Morning Glory", "campus": "UC San Diego", "type": "brunch",
     "tags": ["brunch", "daytime", "food_forward", "trendy"], "vibe": "pink everything, iconic souffle pancakes",
     "address": "550 W Date St", "price_level": 2, "walking_distance_from_campus_min": 15},
    {"name": "Underbelly", "campus": "UC San Diego", "type": "ramen",
     "tags": ["dinner", "casual", "loud"], "vibe": "tight ramen spot, quick",
     "address": "750 W Fir St", "price_level": 2, "walking_distance_from_campus_min": 14},
    {"name": "Puesto", "campus": "UC San Diego", "type": "mexican",
     "tags": ["casual", "group_friendly", "food_forward"], "vibe": "upscale tacos, good for groups",
     "address": "1026 Wall St", "price_level": 2, "walking_distance_from_campus_min": 6},
    {"name": "La Jolla Cove", "campus": "UC San Diego", "type": "beach",
     "tags": ["outdoor", "walking", "daytime", "water", "quiet"], "vibe": "cliffside, seals, postcard views",
     "address": "1100 Coast Blvd", "price_level": 1, "walking_distance_from_campus_min": 12},
    {"name": "Torrey Pines State Reserve", "campus": "UC San Diego", "type": "park",
     "tags": ["outdoor", "active", "daytime", "hike", "walking"], "vibe": "trail hikes with ocean views",
     "address": "12600 N Torrey Pines Rd", "price_level": 1, "walking_distance_from_campus_min": 10},
    {"name": "Museum of Contemporary Art", "campus": "UC San Diego", "type": "museum",
     "tags": ["museum", "daytime", "quiet", "creative"], "vibe": "clean white rooms, big windows",
     "address": "700 Prospect St", "price_level": 2, "walking_distance_from_campus_min": 11},
    {"name": "Balboa Park", "campus": "UC San Diego", "type": "park",
     "tags": ["outdoor", "walking", "daytime", "creative", "museum"], "vibe": "museums + lawns + gardens",
     "address": "1549 El Prado", "price_level": 1, "walking_distance_from_campus_min": 18},
    {"name": "Ocean Beach Pier", "campus": "UC San Diego", "type": "pier",
     "tags": ["outdoor", "walking", "water", "casual"], "vibe": "long pier, fish tacos nearby",
     "address": "5091 Niagara Ave", "price_level": 1, "walking_distance_from_campus_min": 16},
    {"name": "North Park Farmers Market", "campus": "UC San Diego", "type": "market",
     "tags": ["daytime", "outdoor", "casual", "food_forward"], "vibe": "thursdays, food stalls, music",
     "address": "3000 North Park Way", "price_level": 1, "walking_distance_from_campus_min": 17},
    {"name": "Geisel Library", "campus": "UC San Diego", "type": "landmark",
     "tags": ["quiet", "walking", "iconic", "study"], "vibe": "brutalist icon, great photo spot",
     "address": "9500 Gilman Dr", "price_level": 1, "walking_distance_from_campus_min": 0},

    # UCLA (Westwood)
    {"name": "Bluestone Lane", "campus": "UCLA", "type": "cafe",
     "tags": ["coffee", "daytime", "walking", "quiet"], "vibe": "australian-style flat white, airy",
     "address": "1069 Glendon Ave", "price_level": 2, "walking_distance_from_campus_min": 6},
    {"name": "Diddy Riese", "campus": "UCLA", "type": "dessert",
     "tags": ["dessert", "casual", "cheap", "group_friendly", "iconic"], "vibe": "cookie ice cream sandwiches, a line out the door",
     "address": "926 Broxton Ave", "price_level": 1, "walking_distance_from_campus_min": 5},
    {"name": "Skylight Gardens", "campus": "UCLA", "type": "upscale",
     "tags": ["dinner", "date_night", "outdoor", "food_forward"], "vibe": "string lights, pasta, courtyard",
     "address": "1139 Glendon Ave", "price_level": 3, "walking_distance_from_campus_min": 7},
    {"name": "Fundamental LA", "campus": "UCLA", "type": "cafe",
     "tags": ["coffee", "daytime", "bookish", "quiet", "walking"], "vibe": "small menu, thoughtful sandwiches",
     "address": "1303 Westwood Blvd", "price_level": 2, "walking_distance_from_campus_min": 9},

    # USC (USC Village)
    {"name": "Trojan Grounds", "campus": "USC", "type": "cafe",
     "tags": ["coffee", "daytime", "walking", "quiet"], "vibe": "campus-adjacent pourover",
     "address": "3335 S Figueroa St", "price_level": 1, "walking_distance_from_campus_min": 2},
    {"name": "The Lab Gastropub", "campus": "USC", "type": "gastropub",
     "tags": ["dinner", "casual", "loud", "group_friendly"], "vibe": "burgers, beer, crowd noise",
     "address": "3335 S Figueroa St #K-111", "price_level": 2, "walking_distance_from_campus_min": 3},
    {"name": "Cava", "campus": "USC", "type": "mediterranean",
     "tags": ["casual", "daytime", "food_forward", "mid_priced"], "vibe": "build-your-own bowls, bright",
     "address": "929 W Jefferson Blvd", "price_level": 2, "walking_distance_from_campus_min": 4},
    {"name": "Salt & Straw", "campus": "USC", "type": "dessert",
     "tags": ["dessert", "daytime", "walking", "casual"], "vibe": "weird flavor scoops, line moves fast",
     "address": "3335 S Figueroa St #M-140", "price_level": 2, "walking_distance_from_campus_min": 3},

    # UC Davis (downtown Davis)
    {"name": "Mishka's Cafe", "campus": "UC Davis", "type": "cafe",
     "tags": ["coffee", "daytime", "quiet", "bookish", "walking"], "vibe": "wood interior, grad student energy",
     "address": "610 2nd St", "price_level": 1, "walking_distance_from_campus_min": 9},
    {"name": "Dos Coyotes", "campus": "UC Davis", "type": "mexican",
     "tags": ["casual", "daytime", "cheap", "food_forward"], "vibe": "fish tacos, outdoor patio",
     "address": "1411 W Covell Blvd", "price_level": 1, "walking_distance_from_campus_min": 14},
    {"name": "Davis Farmers Market", "campus": "UC Davis", "type": "market",
     "tags": ["outdoor", "daytime", "casual", "food_forward", "walking"], "vibe": "saturday mornings, stalls, live music",
     "address": "301 C St", "price_level": 1, "walking_distance_from_campus_min": 11},
    {"name": "UC Davis Arboretum", "campus": "UC Davis", "type": "park",
     "tags": ["outdoor", "walking", "quiet", "daytime", "active"], "vibe": "3-mile loop along putah creek",
     "address": "1 Shields Ave", "price_level": 1, "walking_distance_from_campus_min": 0},

    # San Jose State (SoFA district)
    {"name": "Caffe Trieste", "campus": "San Jose State", "type": "cafe",
     "tags": ["coffee", "daytime", "quiet", "bookish"], "vibe": "old-school italian espresso bar",
     "address": "315 S 1st St", "price_level": 1, "walking_distance_from_campus_min": 8},
    {"name": "Forager Eatery", "campus": "San Jose State", "type": "restaurant",
     "tags": ["dinner", "casual", "mid_priced", "food_forward"], "vibe": "tap room plus small plates",
     "address": "420 S 1st St", "price_level": 2, "walking_distance_from_campus_min": 9},
    {"name": "SP2 Communal Bar", "campus": "San Jose State", "type": "gastropub",
     "tags": ["dinner", "loud", "group_friendly", "nightlife"], "vibe": "rooftop patio, communal tables",
     "address": "72 N Almaden Ave", "price_level": 2, "walking_distance_from_campus_min": 12},
    {"name": "Paper Plane", "campus": "San Jose State", "type": "cocktail_bar",
     "tags": ["nightlife", "date_night", "low_alcohol_option", "quieter_booths"], "vibe": "craft cocktails, dim booths, soft music",
     "address": "72 S 1st St", "price_level": 3, "walking_distance_from_campus_min": 7},
]

# ---------- current cohort ----------

CURRENT_PAIRS = [
    ("Maya Chen", "Jordan Park"),  # reserved for scenario both_again
    ("Rohan Gupta", "Aditi Shah"),  # reserved for scenario both_group
    ("Sam Rivera", "Lucas Kim"),  # reserved for scenario timeout
    ("Priya Patel", "Ethan Wu"),  # reserved for scenario asymmetric_again_pass
    ("Zoe Martinez", "Tyler Brooks"),  # reserved for scenario asymmetric_again_group
    ("Lena Schmidt", "Noah Osei"),  # filler current match
]

CURRENT_STATUSES = ["completed", "completed", "completed", "completed", "canceled", "scheduled"]

# ---------- historical distribution ----------

OUTCOME_DIST = (
    ["both_again"] * 10
    + ["both_group"] * 6
    + ["both_pass"] * 5
    + ["asymmetric_again_pass"] * 3
    + ["asymmetric_again_group"] * 2
    + ["asymmetric_group_pass"] * 1
    + ["timed_out"] * 3
)  # total 30

MOMENTS_POOL = [
    "laughed about weird food",
    "walked campus after coffee",
    "shared taste in music",
    "good banter about movies",
    "quiet pier conversation",
    "bonded over indie bands",
    "talked about travel plans",
    "argued about the best boba place",
    "same niche podcast",
    "both like chess puzzles",
    "shared obsession with noodles",
    "talked about favorite bookstores",
    "traded film recommendations",
    "compared morning routines",
    "good coffee conversation",
]
CONCERNS_POOL = [
    "place was too loud",
    "felt a little rushed",
    "different energy levels",
    "conversation hit a wall",
    "schedules don't overlap much",
    "vibe was more friendly than romantic",
    "big difference in social batteries",
]


def _choices(outcome: str) -> tuple[str | None, str | None]:
    mapping = {
        "both_again": ("again", "again"),
        "both_group": ("group", "group"),
        "both_pass": ("pass", "pass"),
        "asymmetric_again_pass": ("again", "pass"),
        "asymmetric_again_group": ("again", "group"),
        "asymmetric_group_pass": ("group", "pass"),
        "timed_out": ("again", None),
    }
    return mapping[outcome]


def _build_participant(
    user_id: str,
    choice: str | None,
    rnd: random.Random,
    reply_at: datetime,
) -> ParticipantDebrief:
    if choice is None:
        return ParticipantDebrief(user_id=user_id, response_state="pending")
    if choice == "again":
        interest = rnd.randint(7, 10)
        moments = rnd.sample(MOMENTS_POOL, 2)
        concerns = [] if rnd.random() < 0.7 else rnd.sample(CONCERNS_POOL, 1)
    elif choice == "group":
        interest = rnd.randint(5, 7)
        moments = rnd.sample(MOMENTS_POOL, 2)
        concerns = rnd.sample(CONCERNS_POOL, 1)
    else:  # pass
        interest = rnd.randint(2, 5)
        moments = rnd.sample(MOMENTS_POOL, 1)
        concerns = rnd.sample(CONCERNS_POOL, rnd.randint(1, 2))
    return ParticipantDebrief(
        user_id=user_id,
        response_state="revealed",
        choice=choice,  # type: ignore[arg-type]
        interest_level=interest,
        memorable_moments=moments,
        concerns=concerns,
        wants_second_date=choice == "again",
        willing_to_group_hang=choice in ("again", "group"),
        free_text_note=f"read as a {choice} outcome from their reply",
        raw_reply_text="[historical, synthesized]",
        submitted_at=reply_at,
    )


async def run_seed(*, clear_core: bool = True, seed_rng: int = 42) -> dict:
    rnd = random.Random(seed_rng)
    db = get_db()
    await ensure_indexes()
    seed_epoch = datetime.utcnow()

    if clear_core:
        for c in (
            collections.users,
            collections.matches,
            collections.dates,
            collections.venues,
            collections.sessions,
            collections.traces,
            collections.messages,
            collections.closure_reviews,
            collections.second_dates,
            collections.group_queue,
        ):
            await db[c].delete_many({})
        FEEDBACK_FILE.write_text("")

    # Users
    users = [
        User(
            name=u["name"],
            edu_email=u["edu_email"],
            campus=u["campus"],  # type: ignore[arg-type]
            year=u["year"],  # type: ignore[arg-type]
            pronouns=u["pronouns"],
            profile=UserProfile(
                preferences=u["preferences"],
                interests=u["interests"],
                persona_summary=u["persona"],
            ),
            avatar_color=u["avatar_color"],
        )
        for u in USERS
    ]
    await db[collections.users].insert_many([u.model_dump(by_alias=True) for u in users])
    by_name = {u.name: u for u in users}

    # Venues
    venues = [Venue(**v) for v in VENUES]
    await db[collections.venues].insert_many([v.model_dump(by_alias=True) for v in venues])
    venues_by_campus: dict[str, list[Venue]] = {}
    for v in venues:
        venues_by_campus.setdefault(v.campus, []).append(v)

    # Current matches + dates
    current_matches: list[Match] = []
    current_dates: list[DateRecord] = []
    for i, (a_name, b_name) in enumerate(CURRENT_PAIRS):
        a = by_name[a_name]
        b = by_name[b_name]
        match = Match(
            user_a_id=a.id,
            user_b_id=b.id,
            campus=a.campus,
            compatibility_score=round(rnd.uniform(0.68, 0.92), 2),
            explanation=f"seeded current pairing: {a.name} + {b.name}",
            matched_at=seed_epoch - timedelta(days=8),
        )
        current_matches.append(match)

        status = CURRENT_STATUSES[i]
        venue = rnd.choice(venues_by_campus[a.campus])
        if status == "scheduled":
            scheduled = seed_epoch + timedelta(days=3)
            completed_at = None
        elif status == "canceled":
            scheduled = seed_epoch - timedelta(days=2)
            completed_at = None
        else:
            scheduled = seed_epoch - timedelta(days=2, hours=rnd.randint(0, 6))
            completed_at = scheduled + timedelta(hours=2)
        current_dates.append(
            DateRecord(
                match_id=match.id,
                venue_id=venue.id,
                scheduled_for=scheduled,
                status=status,  # type: ignore[arg-type]
                completed_at=completed_at,
                canceled_reason="had an exam overlap" if status == "canceled" else None,
                campus=a.campus,
            )
        )
    await db[collections.matches].insert_many(
        [m.model_dump(by_alias=True) for m in current_matches]
    )
    await db[collections.dates].insert_many(
        [d.model_dump(by_alias=True) for d in current_dates]
    )

    # Historical cohort. Flagship-weighted so the Metrics view reads as a
    # deployed product (heavy on UC Berkeley and UC San Diego, lighter on the
    # four newer campuses). Each campus still gets >=2 sessions so the Sessions
    # filter buttons all resolve non-empty.
    rnd.shuffle(OUTCOME_DIST)
    campus_targets = (
        ["UC Berkeley"] * 9
        + ["UC San Diego"] * 9
        + ["UCLA"] * 5
        + ["USC"] * 3
        + ["UC Davis"] * 2
        + ["San Jose State"] * 2
    )  # total 30, matches len(OUTCOME_DIST)
    rnd.shuffle(campus_targets)

    hist_matches: list[Match] = []
    hist_dates: list[DateRecord] = []
    hist_sessions: list[AftersSession] = []
    feedback_rows: list[FeedbackTrainingRow] = []

    for outcome, campus in zip(OUTCOME_DIST, campus_targets, strict=True):
        # pick two users on the same campus
        pool = [u for u in users if u.campus == campus]
        a, b = rnd.sample(pool, 2)

        days_ago = rnd.uniform(0.5, 14)
        created_at = seed_epoch - timedelta(days=days_ago)

        match = Match(
            user_a_id=a.id,
            user_b_id=b.id,
            campus=campus,  # type: ignore[arg-type]
            compatibility_score=round(rnd.uniform(0.55, 0.92), 2),
            explanation=f"historical pairing: {a.name} + {b.name}",
            matched_at=created_at - timedelta(days=1, hours=rnd.randint(1, 6)),
        )
        hist_matches.append(match)

        venue = rnd.choice(venues_by_campus[campus])
        date = DateRecord(
            match_id=match.id,
            venue_id=venue.id,
            scheduled_for=created_at - timedelta(hours=3),
            status="completed",
            completed_at=created_at - timedelta(hours=1),
            campus=campus,  # type: ignore[arg-type]
        )
        hist_dates.append(date)

        c_a, c_b = _choices(outcome)
        part_a = _build_participant(
            a.id, c_a, rnd, created_at + timedelta(minutes=rnd.randint(5, 60))
        )
        part_b = _build_participant(
            b.id, c_b, rnd, created_at + timedelta(minutes=rnd.randint(60, 720))
        )

        if outcome == "timed_out":
            resolved_at = created_at + timedelta(hours=48)
            state = "closed"
        else:
            # 85% resolved within 24h, 15% longer
            hours = rnd.choice([1, 2, 4, 8, 14, 22]) if rnd.random() < 0.9 else rnd.choice([26, 34, 45])
            resolved_at = created_at + timedelta(hours=hours)
            state = "resolved"

        session = AftersSession(
            date_id=date.id,
            match_id=match.id,
            campus=campus,  # type: ignore[arg-type]
            participants=[part_a, part_b],
            state=state,  # type: ignore[arg-type]
            resolved_outcome=outcome,  # type: ignore[arg-type]
            resolved_at=resolved_at,
            timeout_at=created_at + timedelta(hours=48),
            created_at=created_at,
            updated_at=resolved_at,
        )
        hist_sessions.append(session)

        feedback_rows.append(
            FeedbackTrainingRow(
                session_id=session.id,
                match_id=match.id,
                campus=campus,  # type: ignore[arg-type]
                compatibility_score_pre=match.compatibility_score,
                user_a_wanted_second=c_a == "again",
                user_b_wanted_second=c_b == "again" if c_b else False,
                user_a_interest=part_a.interest_level or 0,
                user_b_interest=part_b.interest_level or 0,
                outcome=outcome,  # type: ignore[arg-type]
                venue_tags=venue.tags,
                time_to_resolution_hours=(resolved_at - created_at).total_seconds() / 3600,
                shared_moments=part_a.memorable_moments[:2],
                concerns=list({*part_a.concerns, *part_b.concerns})[:2],
                label_success=outcome in ("both_again", "both_group"),
                created_at=resolved_at,
            )
        )

    await db[collections.matches].insert_many(
        [m.model_dump(by_alias=True) for m in hist_matches]
    )
    await db[collections.dates].insert_many(
        [d.model_dump(by_alias=True) for d in hist_dates]
    )
    await db[collections.sessions].insert_many(
        [s.model_dump(by_alias=True) for s in hist_sessions]
    )

    with FEEDBACK_FILE.open("a") as fh:
        for row in feedback_rows:
            fh.write(json.dumps(row.model_dump(), default=str) + "\n")

    summary = {
        "users": len(users),
        "venues": len(venues),
        "current_matches": len(current_matches),
        "current_dates": len(current_dates),
        "historical_sessions": len(hist_sessions),
        "feedback_rows": len(feedback_rows),
        "outcome_mix": {
            o: sum(1 for s in hist_sessions if s.resolved_outcome == o)
            for o in sorted({s.resolved_outcome for s in hist_sessions if s.resolved_outcome})
        },
        "campus_mix": {
            c: sum(1 for s in hist_sessions if s.campus == c)
            for c in sorted({s.campus for s in hist_sessions})
        },
        "users_per_campus": {
            c: sum(1 for u in users if u.campus == c)
            for c in sorted({u.campus for u in users})
        },
    }
    return summary


async def _main():
    summary = await run_seed()
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(_main())
