from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest


def test_recommend_save_remove_and_filter():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "Watchwise.py")).run()
    assert not app.exception
    app.multiselect(key="seeds").set_value([0]).run()
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state["results"]
    save = next(button for button in app.button if button.label == "Save for later")
    save.click().run()
    assert len(app.session_state["watchlist"]) == 1
    remove = next(button for button in app.button if button.label == "Remove from watchlist")
    remove.click().run()
    assert not app.session_state["watchlist"]
    assert not app.exception


def test_filters_with_no_matches_show_empty_state():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "Watchwise.py")).run()
    app.multiselect(key="seeds").set_value([0]).run()
    app.slider[0].set_value(9.0).run()
    app.button[0].click().run()
    assert not app.exception
    assert not app.session_state["results"]
    assert any("No movies match" in info.value for info in app.info)


def test_catalog_change_clears_previous_row_identifiers():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "Watchwise.py")).run()
    if not hasattr(app.file_uploader[0], "set_value"):
        pytest.skip("Upload testing requires a recent Streamlit release")
    app.multiselect(key="seeds").set_value([0]).run()
    app.button[0].click().run()
    next(button for button in app.button if button.label == "Save for later").click().run()
    csv = b"title,overview\nOne,Space travel adventure\nTwo,Space journey planet\n"
    app.file_uploader[0].set_value(("new.csv", csv, "text/csv")).run()
    assert not app.exception
    assert not app.session_state["watchlist"]
    assert not app.session_state["results"]
    assert not app.session_state["seeds"]


def test_malformed_catalog_displays_error_without_crashing():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "Watchwise.py")).run()
    if not hasattr(app.file_uploader[0], "set_value"):
        pytest.skip("Upload testing requires a recent Streamlit release")
    app.file_uploader[0].set_value(("bad.csv", b"wrong,columns\n1,2", "text/csv")).run()
    assert app.error
    assert not app.exception
