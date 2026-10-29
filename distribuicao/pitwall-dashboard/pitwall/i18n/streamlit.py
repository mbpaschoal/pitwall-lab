"""Small presentation adapter. Widget values, keys and callbacks stay canonical.

Only display arguments are translated. No global monkey patches, network calls,
model inference or changes to scientific files happen here.
"""

from functools import wraps
import streamlit as native
from . import display_value, in_language, language, translate, visible_text

_TEXT_METHODS = frozenset(
    {
        "markdown",
        "caption",
        "subheader",
        "header",
        "title",
        "info",
        "warning",
        "error",
        "success",
        "text",
        "write",
        "button",
        "checkbox",
        "text_input",
        "expander",
        "popover",
        "download_button",
        "metric",
        "selectbox",
        "multiselect",
        "radio",
    }
)
_CONTAINER_METHODS = frozenset({"container", "expander", "popover", "empty"})


def dataframe(frame):
    if language() == "pt":
        return frame
    if isinstance(frame, list):
        return [
            {translate(k): display_value(v) for k, v in row.items()} for row in frame
        ]
    if hasattr(frame, "columns"):
        result = frame.copy(deep=True)
        result.columns = [translate(str(col)) for col in result.columns]
        for col in result.columns:
            if str(result[col].dtype) in ("object", "string"):
                result[col] = result[col].map(display_value)
        return result
    return frame


class Presentation:
    def __init__(self, target):
        self.target = target

    def __enter__(self):
        self.target.__enter__()
        return self

    def __exit__(self, *args):
        return self.target.__exit__(*args)

    def __getattr__(self, name):
        if name == "sidebar":
            return Presentation(self.target.sidebar)
        member = getattr(self.target, name)
        if not callable(member) or name in {"cache_data", "cache_resource"}:
            return member

        @wraps(member)
        def render(*args, **kwargs):
            # A translated label/options list can change Streamlit's widget ID.
            # Explicitly retain the canonical value before registering its new ID.
            state_key = kwargs.get("key")
            if (
                name in {"radio", "selectbox", "multiselect", "checkbox", "text_input"}
                and native.session_state.get("_preserve_language_widgets")
                and state_key is not None
                and state_key in native.session_state
            ):
                native.session_state[state_key] = native.session_state[state_key]
            values = list(args)
            if name in _TEXT_METHODS and values:
                values[0] = visible_text(values[0])
            for key in ("label", "help", "placeholder", "title"):
                if key in kwargs:
                    kwargs[key] = visible_text(kwargs[key])
            if name in ("selectbox", "radio", "multiselect"):
                formatter = kwargs.get("format_func", str)
                selected_language = language()
                kwargs["format_func"] = lambda item: in_language(
                    formatter(item), selected_language
                )
            if name == "tabs":
                values[0] = [translate(item) for item in values[0]]
                if "default" in kwargs:
                    kwargs["default"] = translate(kwargs["default"])
            if name == "dataframe" and values:
                values[0] = dataframe(values[0])
                if "column_config" in kwargs:
                    kwargs["column_config"] = {translate(key): display_value(config)
                        for key, config in kwargs["column_config"].items()}
            if name == "plotly_chart" and values and language() == "en":
                import plotly.graph_objects as go

                values[0] = go.Figure(display_value(values[0].to_plotly_json()))
            if name == "metric":
                for index in (1, 2):
                    if len(values) > index:
                        values[index] = translate(values[index])
            result = member(*values, **kwargs)
            if name in _CONTAINER_METHODS:
                return Presentation(result)
            if name in ("columns", "tabs"):
                return [Presentation(item) for item in result]
            return result

        return render


st = Presentation(native)
