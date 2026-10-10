from decimal import Decimal

from app.services import normalization as norm


def test_normalize_text_removes_accents_and_punctuation():
    assert norm.normalize_text("Poços de Caldas - MG!") == "pocos de caldas mg"
    assert norm.normalize_text("Medicamento: R$ 1.234,56") == "medicamento r 1 234 56"


def test_normalize_document_validates_length():
    assert norm.normalize_document("12.345.678/0001-99") == "12345678000199"
    assert norm.normalize_document("123.456.789-00") == "12345678900"
    assert norm.normalize_document("123") is None


def test_parse_decimal_brazilian_format():
    assert norm.parse_decimal("R$ 1.234,56") == Decimal("1234.56")
    assert norm.parse_decimal("35.5") == Decimal("35.5")
    assert norm.parse_decimal(175000.0) == Decimal("175000.0")
    assert norm.parse_decimal("") is None
    assert norm.parse_decimal(None) is None


def test_map_modality_and_status():
    assert norm.map_modality(6).value == "6"
    assert norm.map_modality(999).value == "0"
    assert norm.map_procurement_status("Divulgada no PNCP").value == "divulgada"


def test_derive_category_key_prefers_catalog_code():
    assert norm.derive_category_key("qualquer coisa", "12345") == "cat:12345"
    assert norm.derive_category_key("CIMENTO PORTLAND CP II").startswith("heur:material_construcao")
    assert norm.derive_category_key("peça técnica genérica xyz").startswith("txt:")


def test_map_item_kind():
    assert norm.map_item_kind("M").value == "material"
    assert norm.map_item_kind("S").value == "servico"
    assert norm.map_item_kind(None, "Serviço de manutenção predial").value == "servico"
