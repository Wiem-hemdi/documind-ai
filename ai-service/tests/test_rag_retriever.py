import unittest
from unittest.mock import MagicMock, patch

from app.document_processing.cleaner import clean_text
from app.document_processing.models import ExtractedSection
from app.document_processing.splitter import split_sections
from app.rag.vector_store import _document_filter, _point_id, delete_document


class RagPipelineTests(unittest.TestCase):
    def test_clean_text(self):
        raw = "  Hel-\nlo   world \x00 مرحبا  "
        cleaned = clean_text(raw)
        self.assertIn("Hello", cleaned)
        self.assertIn("مرحبا", cleaned)
        self.assertNotIn("\x00", cleaned)

    def test_split_sections(self):
        sections = [
            ExtractedSection(text="Bonjour monde.", page=1, location="Page 1"),
            ExtractedSection(text="Deuxième section.", page=2, location="Page 2"),
        ]
        chunks = split_sections(iter(sections))
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].chunk_index, 0)
        self.assertEqual(chunks[1].chunk_index, 1)
        self.assertEqual(chunks[0].page, 1)
        self.assertEqual(chunks[1].page, 2)

    def test_deterministic_point_id(self):
        id1 = _point_id("user1", "doc1", 0)
        id2 = _point_id("user1", "doc1", 0)
        id3 = _point_id("user1", "doc1", 1)
        self.assertEqual(id1, id2)
        self.assertNotEqual(id1, id3)

    def test_document_filter(self):
        f = _document_filter("user-1", "doc-1")
        conditions = f.must
        self.assertEqual(len(conditions), 2)
        self.assertEqual(conditions[0].key, "user_id")
        self.assertEqual(conditions[0].match.value, "user-1")
        self.assertEqual(conditions[1].key, "document_id")
        self.assertEqual(conditions[1].match.value, "doc-1")

    @patch("app.rag.vector_store._get_client")
    def test_delete_document_calls_qdrant(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.collection_exists.return_value = True
        mock_get_client.return_value = mock_client

        delete_document("user-1", "doc-1")
        mock_client.delete.assert_called_once()
        selector = mock_client.delete.call_args.kwargs["points_selector"]
        must = selector.filter.must
        self.assertEqual(must[0].match.value, "user-1")
        self.assertEqual(must[1].match.value, "doc-1")


if __name__ == "__main__":
    unittest.main()
