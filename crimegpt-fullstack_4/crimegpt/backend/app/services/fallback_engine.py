import re

from app.models import Case, Criminal

CRIME_TYPE_ALIASES = {
    "burglary": ["burglary", "theft", "break-in", "stolen", "robbery", "house breaking"],
    "theft": ["theft", "stolen", "burglary", "shoplifting"],
    "cybercrime": ["cyber", "phishing", "otp", "scam", "digital", "online", "bank"],
    "homicide": ["homicide", "murder", "killed", "stabbed", "death", "fatal"],
    "fraud": ["fraud", "scam", "ponzi", "investment", "forged"],
    "armed robbery": ["robbery", "armed", "pistol", "gun", "weapon", "snatched"],
    "assault": ["assault", "clash", "fight", "beaten", "clashed", "bottles", "sticks", "harassment", "harassed"],
}

DISTRICT_ALIASES = {
    "Central District": ["central district", "central", "sector 1", "sector 6"],
    "North District": ["north district", "north", "sector 5"],
    "South District": ["south district", "south", "sector 2"],
    "District C": ["district c", "palace", "museum"],
    "District E": ["district e"],
    "District D": ["district d", "procession"],
}


def case_to_brief(f: Case) -> str:
    return (
        f"- **{f.firNumber}** ({f.crimeType} - {f.status})\n"
        f"  - *Description*: {f.description}\n"
        f"  - *District*: {f.district}\n"
        f"  - *Investigating Officer*: {f.investigatingOfficer}\n"
        f"  - *Risk Score*: {f.riskScore}/100"
    )


def fallback_reply(local_cases: list[Case], all_criminals: list[Criminal], message: str, user_name: str) -> str:
    """
    local_cases: already location-scoped list of cases (all cases if Admin, else
    only the caller's own district) - mirrors server.ts's dbContext scoping.
    """
    lower_msg = message.lower()

    fir_match = re.search(r"FIR-\d{4}-\d+", message.upper())
    if fir_match:
        case = next((c for c in local_cases if c.firNumber == fir_match.group()), None)
        if case:
            return (
                f"### 📑 Case Summary for {case.firNumber}\n\n"
                f"- **Date**: {case.date}\n"
                f"- **Crime Type**: {case.crimeType}\n"
                f"- **Investigating Officer**: {case.investigatingOfficer}\n"
                f"- **District**: {case.district}\n"
                f"- **Status**: **{case.status}**\n"
                f"- **Crime Description**: {case.description}\n"
                f"- **Risk Score**: **{case.riskScore}/100**\n\n"
                f"*Source: Local database lookup.*"
            )

    if "repeat" in lower_msg or "offender" in lower_msg:
        high_risk = [c for c in all_criminals if c.riskScore > 70]
        if high_risk:
            lines = [
                f"- **{c.name}** (Risk Score: **{c.riskScore}%**)\n  - *Address*: {c.address}\n  - *Criminal History*: {c.criminalHistory}"
                for c in high_risk
            ]
            return (
                f"### ⚠️ High-Risk Repeat Offenders\n\nFound **{len(high_risk)} repeat offenders** with active profiles:\n\n"
                + "\n\n".join(lines)
            )

    matched_types = [key for key, aliases in CRIME_TYPE_ALIASES.items() if any(a in lower_msg for a in aliases)]
    matched_districts = [key for key, aliases in DISTRICT_ALIASES.items() if any(a in lower_msg for a in aliases)]

    matches = local_cases
    if matched_types:
        matches = [c for c in matches if c.crimeType.lower() in matched_types]
    if matched_districts:
        matches = [c for c in matches if c.district in matched_districts]

    if matched_types or matched_districts:
        filter_bits = []
        if matched_types:
            filter_bits.append(f"Classification: **{', '.join(matched_types).upper()}**")
        if matched_districts:
            filter_bits.append(f"Region: **{', '.join(matched_districts)}**")
        filters = f" for ({' & '.join(filter_bits)})" if filter_bits else ""
        if matches:
            lines = [case_to_brief(c) for c in matches]
            return f"### 🔍 Local Database Search: Found {len(matches)} case(s){filters}\n\n" + "\n\n".join(lines)

    words = [w for w in re.sub(r"[.,/#!$%^&*;:{}=\-_`~()]", "", lower_msg).split() if len(w) > 2]
    if words:
        text_matches = [
            c for c in local_cases
            if any(w in f"{c.description} {c.crimeType} {c.district} {c.investigatingOfficer}".lower() for w in words)
        ]
        if text_matches:
            lines = [case_to_brief(c) for c in text_matches[:10]]
            return f"### 🔍 Local Database Search: Found {len(text_matches)} case(s)\n\n" + "\n\n".join(lines)

        crim_matches = [
            c for c in all_criminals if any(w in f"{c.name} {c.address} {c.criminalHistory}".lower() for w in words)
        ]
        if crim_matches:
            lines = [
                f"- **{c.name}** (Risk Score: **{c.riskScore}%**)\n  - *Address*: {c.address}\n  - *Criminal History*: {c.criminalHistory}"
                for c in crim_matches
            ]
            return f"### 👤 Local Database Search: Found {len(crim_matches)} offender profile(s)\n\n" + "\n\n".join(lines)

    return (
        f"### 🛡️ CrimeGPT Local Assistant\n\n"
        f"Welcome back, **{user_name}**. I searched the database but couldn't find records matching: *\"{message}\"*.\n\n"
        f"**Try asking about:**\n"
        f"- **Crime Types**: Burglary, Cybercrime, Theft, Homicide, Fraud, Armed Robbery, Assault\n"
        f"- **Districts**: Central District, North District, South District, District C, District E, District D\n"
        f"- **A specific case**: e.g. \"summary of FIR-2026-1024\"\n"
        f"- **Repeat offenders**: \"show me repeat offenders\"\n\n"
        f"*System Status: Running on local rule-engine. Add your Gemini API key in backend/.env to enable full AI reasoning.*"
    )
