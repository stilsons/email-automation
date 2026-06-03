import html
import re

# Patterns to identify reply markers, noise lines, and multi-line blocks to remove from email bodies.
REPLY_MARKER_PATTERNS = [
    r"^On .+ wrote:\s*$",
]

# Lines that are common in email replies but don't necessarily indicate the start of a thread, such as "From:", "Sent:", "To:", "Subject:", etc.
NOISE_LINE_PATTERNS = [
    r"^Sent from Yahoo Mail.*$",
    r"^Get Outlook for .*?$",
    r"^CAUTION:.*$",
    r"^WARNING:.*$",
    r"^-+Original Message-+$",
    r"^Begin forwarded message:\s*$",
    r"^-+\s*Forwarded Message\s*-+.*$",
    r"^From:\s+.*$",
    r"^Sent:\s+.*$",
    r"^To:\s+.*$",
    r"^Subject:\s+.*$",
    r"^Cc:\s+.*$",
    r"^Bcc:\s+.*$",
    r"^From my iPhone\s*$",
    r"^Sent from my iPhone\s*$",
    r"^External Email.*$",
    r"^Need help\?\s*Click for assistance\s*$",
    r"^Confidentiality Notice:\s*$",
]

# Multi-line blocks to remove, such as legal disclaimers or survey requests.
BLOCK_PATTERNS = [
    r"CONFIDENTIALITY NOTICE:.*?(?=\n\n|\Z)",
    r"How am I doing\?.*?(?=\n\n|\Z)",
    r"(CCPA|CCCPA)\s+Privacy Notice.*?(?=\n\n|\Z)",
    r"All qualified applicants will receive consideration for employment.*?(?=\n\n|\Z)",
    r"To unsubscribe.*?(?=\n\n|\Z)",
    r"unsubscribe.*?(?=\n\n|\Z)",
    r"(equal opportunity employer|reasonable accommodation|protected veteran|characteristic protected by law).*?(?=\n\n|\Z)",
    r"(confidentiality notice|privileged and confidential information).*?(?=\n\n|\Z)",
    r"(privacy notice|email confidentiality and privacy).*?(?=\n\n|\Z)",
    r"Confidentiality Notice:.*?(?=\n\n|\Z)",
    r"The information contained in this message may be privileged and confidential and protected from disclosure.*?(?=\n\n|\Z)",
]

# Helper function to check if a line matches any pattern in a list.
def matches_any_pattern(text: str, patterns: list[str]) -> bool:
    return any(re.match(pattern, text, re.IGNORECASE) for pattern in patterns)

# Remove characters from Unicode Private Use Area, such as Gmail/Outlook.
def remove_private_unicode(text: str) -> str:
    """
    Remove characters from Unicode Private Use Area, such as Gmail/Outlook
    icon glyphs like '', which do not represent meaningful text content.
    """
    return re.sub(r"[\uE000-\uF8FF]", "", text)

# Main function to clean email body text.
def truncate(value, length=200):
    text = repr(value)
    return text[:length] + ("..." if len(text) > length else "")

def debug_log(before, after, reason):
    print("\n--- DEBUG ---")
    print(f"Reason: {reason}")
    print("BEFORE:")
    print(truncate(before))
    print("AFTER:")
    print(truncate(after))
    print("-------------\n")

# What calls clean_email_body?  Two places: text_exporter.py and word_Exporter.py.
def clean_email_body(body: str, trim_thread: bool = False) -> str:
    if not body:
        return ""

    # Unescape HTML entities and normalize line breaks.
    text = html.unescape(body)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove known glyph junk and private-use characters.
    text = text.replace("", "")
    text = remove_private_unicode(text)

    # Normalize line breaks to \n for consistent processing.
    lines = text.split("\n")
    cleaned_lines = []

    # First pass: remove noise lines and trim thread if needed.
    i = 0

    # Iterate through lines, applying patterns to identify reply markers and noise lines.
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Single-line reply marker
        if matches_any_pattern(stripped, REPLY_MARKER_PATTERNS):
            debug_log(line, "", "Removed reply marker")
            if trim_thread:
                break
            i += 1
            continue

        # Two-line reply marker:
        # On Monday, March 30, 2026, ...
        # wrote:
        if (
            re.match(r"^On .+$", stripped, re.IGNORECASE)
            and i + 1 < len(lines)
            and re.match(r"^wrote:\s*$", lines[i + 1].strip(), re.IGNORECASE)
        ):
            debug_log(line + "\n" + lines[i + 1], "", "Removed two-line reply marker")
            if trim_thread:
                break
            i += 2
            continue

        # Generic noise/header lines
        if matches_any_pattern(stripped, NOISE_LINE_PATTERNS):
            debug_log(line, "", "Removed noise line")
            i += 1
            continue

        # If we reach here, it's a line we want to keep.
        cleaned_lines.append(line)
        i += 1

    # Collapse large gaps before block cleanup.
    text = "\n".join(cleaned_lines)

    # Collapse large gaps before block cleanup.
    new_text = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", text)
    if new_text != text:
        debug_log(text, new_text, "Collapsed multiple blank lines")
    text = new_text

    # Remove multi-line footer/legal blocks.
    for pattern in BLOCK_PATTERNS:
        matches = list(re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL))
        for m in matches:
            debug_log(m.group(0), "", f"Removed block pattern: {pattern}")

        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)

    # Collapse again.
    new_text = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", text)
    if new_text != text:
        debug_log(text, new_text, "Collapsed blank lines after block removal")
    text = new_text

    # Remove leading/trailing whitespace from each line, and collapse multiple spaces.
    lines = text.split("\n")
    cleaned_lines = []
    previous_was_blank = False

    # Remove lines that do not contain visible character content,
    # and normalize spacing on lines that do.
    for line in lines:
        original_line = line

        # The following replace clauses are all case-sensitive:
        line = (
            line.replace("\u00A0", " ")
                .replace("\u2007", " ")
                .replace("\u202F", " ")
                .replace("If you would like", "")
                .replace("   ", " ")
                .replace("+1", "")
                .replace(" :", ":")
                .replace(" .", ".")
                .replace(" ,", ",")
                .replace(",Iselin", ", Iselin")
                .replace("::", " ")
                .replace("͏­", "")
                .replace(" ", " ")
                .replace(" ", " ")
                .replace("/)", ")")
                .replace("!!", "!")
                .replace("&nbsp;"," ")
                .replace("privacy", "")
                .replace("Privacy", "")
                .replace("Note: ", "")
                .replace("{JobPosting: city}", "")
                .replace("MIssion", "Mission")
                .replace("(Onsite)","onsite")
                .replace(".ceipalmm.com", "")
                .replace(":-", ":")
                .replace("Job Title","Title")
                .replace("Job Location","Location")
                .replace("Job Type","Type")
                .replace("Skip to content","")
                .replace("United States","")
                .replace("USA","")
                .replace("Full stack","Full Stack")
                .replace("Best Regards", "Best regards")
                .replace("Stilson", "")
                .replace("Steve", "Dominick")
                .replace("Your Email Title", "")
                .replace("Thanks & Regards", "\nThanks and regards")
                .replace(" in Massachusetts-*", "")
                .replace("Pulled from the full job description","")
                .replace("This message is intended solely for the addressee", "")
                .replace("Please review the job description below.", "")
                .replace("Professional References:(Preferably Supervisory", "professional references (preferably supervisory")
        )
        line = re.sub(r"[\u200B-\u200D\uFEFF]", "", line)

        # Normalize odd spaces / invisible chars per line.
        normalized = re.sub(r"[ \t]+", " ", line).strip()

        # Remove leading pipe/table artifacts.
        normalized = re.sub(r"^[\|\s]+", "", normalized)
        if (line != original_line):
            debug_log(original_line, normalized, "Normalized whitespace and unicode chars and leading formatting")

        # Remove lines that are only formatting junk.
        if normalized and re.fullmatch(r"[|_\-=~ ]+", normalized):
            debug_log(original_line, "", "Removed formatting junk line")
            continue

        # Remove lines that are only blank after normalization, but ensure we don't add multiple blank lines in a row.
        if not normalized:
            if not previous_was_blank:
                cleaned_lines.append("")
                previous_was_blank = True
            else:
                debug_log(original_line, "", "Removed extra blank line")
            continue

        # Check for two-line reply marker again after normalization, to catch cases where noise lines are interspersed.
        cleaned_lines.append(normalized)
        previous_was_blank = False

    # Final check for two-line reply marker in cleaned lines, to catch cases where noise lines are interspersed.
    text = "\n".join(cleaned_lines)

    # Clean bullet indentation.
    new_text = re.sub(r"\n\s*-\s*", "\n- ", text)
    if new_text != text:
        debug_log(text, new_text, "Normalized bullet indentation")
    text = new_text

    # Final safety pass: at most one blank line between text blocks.
    new_text = re.sub(r"\n(?:\s*\n)+", "\n\n", text)
    if new_text != text:
        debug_log(text, new_text, "Final blank line normalization")
    text = new_text

    return text.strip()


