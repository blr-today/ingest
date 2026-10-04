from datetime import time

from typesafe_sdk import Choice, Noul

from .tz import IST

NONE = "none"
MIN_CONFIDENCE = 0.5
HOURS = {
    str(h): f"{(h - 1) % 12 + 1} {'AM' if h < 12 else 'PM'} ({h:02d}:00)"
    for h in range(24)
}
MINUTES = [str(m) for m in range(60)]


def pick(question, options):
    if not options:
        return None
    criteria = options if isinstance(options, dict) else {o: None for o in options}
    return Choice(
        instructions=question, criteria=criteria | {NONE: "None of these fits."}
    )


def time_questions(subject):
    # Hours and minutes are read as parts so code, not the model, builds the time
    return {
        "has_end": Noul(instructions=f"Does the text state when {subject} ends?"),
        "start_hour": pick(f"In which hour of the day does {subject} start?", HOURS),
        "start_minute": pick(
            f"At which minute past the hour does {subject} start?", MINUTES
        ),
        "end_hour": pick(f"In which hour of the day does {subject} end?", HOURS),
        "end_minute": pick(
            f"At which minute past the hour does {subject} end?", MINUTES
        ),
    }


def ask(client, state, questions):
    questions = {k: q for k, q in questions.items() if q is not None}
    response = client.system_one(state=state, questions=questions)
    nouls = {k: a.noul for k, a in response.nouls.items()}
    picks = {k: (a.choice, a.confidence) for k, a in response.choices.items()}
    return nouls, picks


def value(picks, key):
    choice, confidence = picks.get(key, (NONE, 0.0))
    return None if choice == NONE or confidence < MIN_CONFIDENCE else choice


def clock(picks, prefix):
    hour = value(picks, f"{prefix}_hour")
    if hour is None:
        return None
    return time(int(hour), int(value(picks, f"{prefix}_minute") or 0), tzinfo=IST)


def end_clock(nouls, picks):
    start, end = clock(picks, "start"), clock(picks, "end")
    if start and end and end > start and nouls.get("has_end", 0) >= MIN_CONFIDENCE:
        return end
    return None
