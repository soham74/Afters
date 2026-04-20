"""Hand-labeled eval set for the Debrief Intake Agent.

20 examples mixing:
- clearly interested (expect choice=again, wants_second_date=True)
- clearly uninterested (expect choice=pass, wants_second_date=False)
- group-hang intent (expect choice=group, willing_to_group_hang=True)
- ambiguous / tricky cases (boundary conditions)
- voice-note style (long, rambling)
- short text style (terse)

Each row has:
- id
- reply text
- is_voice_note
- expected.choice  (ground truth)
- expected.wants_second_date
- expected.willing_to_group_hang
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class Example:
    id: str
    reply: str
    is_voice_note: bool
    expected_choice: Literal["again", "group", "pass"]
    expected_wants_second: bool
    expected_willing_group: bool
    note: str = ""


DATASET: list[Example] = [
    # clearly interested
    Example(
        id="clear_again_01",
        reply="omg so good. hes actually hilarious. would 100% see him again",
        is_voice_note=False,
        expected_choice="again",
        expected_wants_second=True,
        expected_willing_group=True,
    ),
    Example(
        id="clear_again_02",
        reply=(
            "honestly the best first date ive had in a long time. we ended up talking for "
            "three hours. id genuinely want another one on one"
        ),
        is_voice_note=True,
        expected_choice="again",
        expected_wants_second=True,
        expected_willing_group=True,
    ),
    Example(
        id="clear_again_03",
        reply="yes!! another date please",
        is_voice_note=False,
        expected_choice="again",
        expected_wants_second=True,
        expected_willing_group=True,
    ),
    Example(
        id="clear_again_04",
        reply=(
            "she was so thoughtful and the conversation never dipped. i want to see "
            "her again like honestly if possible this week"
        ),
        is_voice_note=True,
        expected_choice="again",
        expected_wants_second=True,
        expected_willing_group=True,
    ),
    # clearly uninterested
    Example(
        id="clear_pass_01",
        reply="not a match. nice person but no romantic spark. pass for me",
        is_voice_note=False,
        expected_choice="pass",
        expected_wants_second=False,
        expected_willing_group=False,
    ),
    Example(
        id="clear_pass_02",
        reply=(
            "yeah im gonna pass. felt like we were on different wavelengths the whole "
            "time. i dont think a second date would change that"
        ),
        is_voice_note=True,
        expected_choice="pass",
        expected_wants_second=False,
        expected_willing_group=False,
    ),
    Example(
        id="clear_pass_03",
        reply="no thanks, not feeling it",
        is_voice_note=False,
        expected_choice="pass",
        expected_wants_second=False,
        expected_willing_group=False,
    ),
    # group
    Example(
        id="clear_group_01",
        reply=(
            "she was genuinely cool and id love to stay in her orbit but more as a "
            "friend. a group hang would be perfect"
        ),
        is_voice_note=False,
        expected_choice="group",
        expected_wants_second=False,
        expected_willing_group=True,
    ),
    Example(
        id="clear_group_02",
        reply=(
            "honestly kind of friend energy. no spark but id 100% be down to hang in a "
            "group or like a friend of friends thing"
        ),
        is_voice_note=True,
        expected_choice="group",
        expected_wants_second=False,
        expected_willing_group=True,
    ),
    Example(
        id="clear_group_03",
        reply="group vibes only. nothing romantic but theyre great",
        is_voice_note=False,
        expected_choice="group",
        expected_wants_second=False,
        expected_willing_group=True,
    ),
    # ambiguous / tricky
    Example(
        id="ambig_01",
        reply=(
            "it was fine. not bad. i dont know. maybe a second would answer the "
            "question but im not dying to"
        ),
        is_voice_note=False,
        expected_choice="group",
        expected_wants_second=False,
        expected_willing_group=True,
        note="soft neutral. model should read 'not dying to' as not-again.",
    ),
    Example(
        id="ambig_02",
        reply=(
            "we laughed a lot but i dont think they were into me. id say again but i "
            "dont want to be embarrassed"
        ),
        is_voice_note=True,
        expected_choice="again",
        expected_wants_second=True,
        expected_willing_group=True,
        note="self-reported again despite asymmetry fear. we go with what they say.",
    ),
    Example(
        id="ambig_03",
        reply=(
            "i liked them but the place was so loud we barely talked. want another shot "
            "somewhere quieter"
        ),
        is_voice_note=False,
        expected_choice="again",
        expected_wants_second=True,
        expected_willing_group=True,
    ),
    Example(
        id="ambig_04",
        reply=(
            "hmm. i liked them as a person a lot. not sure romantically. would need to see "
            "them again in a different setting to know"
        ),
        is_voice_note=True,
        expected_choice="again",
        expected_wants_second=True,
        expected_willing_group=True,
        note="leaning again to disambiguate, not group.",
    ),
    Example(
        id="ambig_05",
        reply="really sweet but honestly just no chemistry. pass",
        is_voice_note=False,
        expected_choice="pass",
        expected_wants_second=False,
        expected_willing_group=False,
        note="kindness language can throw a model; outcome is still pass.",
    ),
    # voice-note rambly
    Example(
        id="voice_long_01",
        reply=(
            "okay so it was really funny because i thought it was gonna be boring. "
            "we went to a coffee place and then ended up walking around campus for an "
            "hour and a half. i think we saw every squirrel in berkeley. anyway yeah. "
            "id definitely see them again"
        ),
        is_voice_note=True,
        expected_choice="again",
        expected_wants_second=True,
        expected_willing_group=True,
    ),
    Example(
        id="voice_long_02",
        reply=(
            "um so like. yeah. the food was great and they were nice but every time i "
            "tried to like get deeper they kind of deflected. so i think the friendly "
            "version is where im at"
        ),
        is_voice_note=True,
        expected_choice="group",
        expected_wants_second=False,
        expected_willing_group=True,
    ),
    # short text
    Example(
        id="short_01",
        reply="again!!",
        is_voice_note=False,
        expected_choice="again",
        expected_wants_second=True,
        expected_willing_group=True,
    ),
    Example(
        id="short_02",
        reply="group hang pls",
        is_voice_note=False,
        expected_choice="group",
        expected_wants_second=False,
        expected_willing_group=True,
    ),
    Example(
        id="short_03",
        reply="pass",
        is_voice_note=False,
        expected_choice="pass",
        expected_wants_second=False,
        expected_willing_group=False,
    ),
]

assert len(DATASET) == 20
