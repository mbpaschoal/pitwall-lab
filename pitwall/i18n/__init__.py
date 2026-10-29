"""Offline, deterministic presentation translations; canonical IDs never change."""

from contextvars import ContextVar
from functools import lru_cache
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from string import Formatter

_LANGUAGE = ContextVar("pitwall_language", default="pt")


def language():
    return _LANGUAGE.get()


def set_language(value):
    selected = value if value in ("pt", "en") else "pt"
    _LANGUAGE.set(selected)
    return selected


def in_language(text, selected):
    """Stable widget formatter even when called outside the render thread."""
    token = _LANGUAGE.set(selected)
    try:
        return translate(text)
    finally:
        _LANGUAGE.reset(token)


@lru_cache(maxsize=1)
def catalogue():
    return json.loads((Path(__file__).parent / "en.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def patterns():
    result = []
    for source, target in catalogue().items():
        if "{" not in source:
            continue
        try:
            parts = list(Formatter().parse(source))
        except ValueError:
            continue
        if not any(field is not None for _, field, _, _ in parts):
            continue
        # Match complete messages, never words inside URLs or canonical identifiers.
        literal_size = sum(len(text) for text, _, _, _ in parts)
        if literal_size < 4:
            continue
        pattern = "".join(
            re.escape(text) + ("(.*?)" if field is not None else "")
            for text, field, _, _ in parts
        )
        result.append(
            (re.compile("^" + pattern + "$", re.DOTALL), target, literal_size)
        )
    return sorted(result, key=lambda item: item[2], reverse=True)


def translate(text, depth=0):
    if language() == "pt" or not isinstance(text, str) or not text or depth > 5:
        return text
    if text in catalogue():
        return catalogue()[text]
    stripped = text.strip()
    if stripped != text and stripped in catalogue():
        return (
            text[: len(text) - len(text.lstrip())]
            + catalogue()[stripped]
            + text[len(text.rstrip()) :]
        )
    date_match = re.fullmatch(
        r"(\d{1,2}) (jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez) (\d{4})", text
    )
    if date_match:
        months = dict(
            zip(
                "jan fev mar abr mai jun jul ago set out nov dez".split(),
                "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(),
            )
        )
        return "{} {} {}".format(date_match[1], months[date_match[2]], date_match[3])
    if re.fullmatch(r"-?\d+,\d+(?: km| m| °C|%)?", text):
        return text.replace(",", ".")
    for pattern, target, _ in patterns():
        match = pattern.fullmatch(text)
        if match:
            # Values have already been formatted; format specs must not reinterpret them.
            values = iter(translate(value, depth + 1) for value in match.groups())
            return "".join(
                literal + (next(values) if field is not None else "")
                for literal, field, _, _ in Formatter().parse(target)
            )
    markdown_links = re.sub(
        r"(?<!!)\[([^\]]+)\]\(([^)]+)\)",
        lambda m: "[" + translate(m[1], depth + 1) + "](" + m[2] + ")",
        text,
    )
    if markdown_links != text:
        return markdown_links
    sentences = re.split(r"(?<=[.!?]) (?=[A-ZÁÉÓÍ])", text)
    if len(sentences) > 1:
        return " ".join(translate(sentence, depth + 1) for sentence in sentences)
    # Discrete lines include metadata in hover labels, without modifying identifiers.
    if "\n" in text and not text.startswith(("http://", "https://")):
        return "\n".join(translate(line, depth + 1) for line in text.split("\n"))
    return text


class _VisibleHTML(HTMLParser):
    """Translate text and accessibility labels, preserving URLs, CSS and IDs."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.output = []
        self.verbatim = 0

    def handle_starttag(self, tag, attrs):
        original = self.get_starttag_text()
        if tag in ("style", "script", "code", "pre"):
            self.verbatim += 1
        for key, value in attrs:
            if key in ("alt", "title", "aria-label", "placeholder") and value:
                converted = translate(value)
                if converted != value:
                    original = original.replace(
                        '"' + escape(value, quote=True) + '"',
                        '"' + escape(converted, quote=True) + '"',
                    )
        self.output.append(original)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        self.output.append("</" + tag + ">")
        if tag in ("style", "script", "code", "pre"):
            self.verbatim = max(0, self.verbatim - 1)

    def handle_data(self, value):
        self.output.append(value if self.verbatim else translate(value))

    def handle_entityref(self, name):
        self.output.append("&" + name + ";")

    def handle_charref(self, name):
        self.output.append("&#" + name + ";")

    def handle_comment(self, value):
        self.output.append("<!--" + value + "-->")


def visible_text(text):
    if not isinstance(text, str) or language() == "pt":
        return text
    if "`" in text:
        parts = re.split(r"(```[\s\S]*?```|`[^`\n]*`)", text)
        if len(parts) > 1:
            return "".join(
                part if index % 2 else visible_text(part)
                for index, part in enumerate(parts)
            )
    converted = translate(text)
    if "<" not in converted:
        return converted
    parser = _VisibleHTML()
    parser.feed(converted)
    return "".join(parser.output)


def display_value(value):
    """Copy presentation objects; do not mutate source data or scientific downloads."""
    if language() == "pt":
        return value
    if isinstance(value, str):
        return visible_text(value)
    if isinstance(value, list):
        return [display_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(display_value(item) for item in value)
    if isinstance(value, dict):
        return {key: display_value(item) for key, item in value.items()}
    return value
