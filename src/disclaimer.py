"""In-product disclaimer (PRD §4).

The product explains documents; it does not provide legal or financial advice.
This must be stated clearly in-product.
"""

DISCLAIMER_EN = (
    "DISCLAIMER: This tool explains documents in plain language. "
    "It does NOT provide legal or financial advice. "
    "For important decisions, consult a qualified professional."
)

DISCLAIMER_HI = (
    "अस्वीकरण: यह उपकरण दस्तावेज़ों को सरल भाषा में समझाता है। "
    "यह कानूनी या वित्तीय सलाह नहीं देता। "
    "महत्वपूर्ण निर्णयों के लिए किसी योग्य पेशेवर से परामर्श करें।"
)

DISCLAIMERS: dict[str, str] = {
    "en": DISCLAIMER_EN,
    "hi": DISCLAIMER_HI,
}


def get_disclaimer(language: str = "en") -> str:
    """Get the in-product disclaimer for the given language.

    Falls back to English if the language is not supported.
    """
    return DISCLAIMERS.get(language, DISCLAIMER_EN)
