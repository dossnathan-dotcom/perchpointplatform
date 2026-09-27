"""Document byte checks do not require a database."""
from perchpoint.phase5_files import EICAR, inspect_upload


def test_clean_text_is_accepted():
    decision = inspect_upload("note.txt", "text/plain", b"Synthetic lease note")
    assert decision.verdict == "clean"


def test_extension_mismatch_is_rejected():
    decision = inspect_upload("note.txt", "application/pdf", b"not a pdf")
    assert decision.reason == "declared_type_mismatch"


def test_executable_is_rejected():
    decision = inspect_upload("run.exe", "application/octet-stream", b"MZ")
    assert decision.reason == "type_not_allowed"


def test_eicar_is_quarantined():
    decision = inspect_upload("note.txt", "text/plain", b"prefix " + EICAR)
    assert decision.verdict == "quarantined"
    assert decision.reason == "malware_signature"


def test_pdf_signature_mismatch_is_rejected():
    decision = inspect_upload("scan.pdf", "application/pdf", b"not-a-pdf")
    assert decision.reason == "signature_mismatch"
