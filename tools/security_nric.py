from presidio_analyzer import PatternRecognizer, Pattern

class SingaporeNRICRecognizer(PatternRecognizer):
    """
    Recognizes Singapore NRIC/FIN using Regex.
    """
    def __init__(self):
        nric_pattern = Pattern("NRIC/FIN", r"\b[STFGM]\d{7}[A-Z]\b", 0.5)
        super().__init__(supported_entity="NRIC",
                         patterns=[nric_pattern],
                         supported_language="en")
