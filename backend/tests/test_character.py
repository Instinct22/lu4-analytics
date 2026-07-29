"""Character dataset normalization and the sliced endpoints replacing 20 MB."""

from __future__ import annotations

from types import SimpleNamespace

from models.character import CharacterClass, CharacterRace, CharacterSkill
from services.normalizers.character import META_KEY, normalize_character
from tests.conftest import scalars_by_model

PAYLOAD = {
    "generated_at": "2026-07-27T00:50:58+00:00",
    "wiki_base": "https://masterwork.wiki",
    "races": [
        {
            "id": "human",
            "name": "Human",
            "branches": [
                {
                    "type": "warrior",
                    "root": {
                        "id": 0,
                        "name": "Fighter",
                        "slug": "0-fighter",
                        "icon": "i0",
                        "portrait": "p0",
                        "children": [
                            {
                                "id": 1,
                                "name": "Warrior",
                                "slug": "1-warrior",
                                "icon": "i1",
                                "portrait": "p1",
                                "children": [],
                            }
                        ],
                    },
                }
            ],
        }
    ],
    "classes": {
        "0": {
            "id": 0,
            "name": "Fighter",
            "slug": "0-fighter",
            "icon": "i0",
            "portrait": "p0",
            "levels": [1, 5],
            "skills_by_level": {"1": [{"skill_id": 3, "skill_level": 1, "name": "Slash"}]},
            "skills_up_to_level": {"5": []},
        },
        "3000": {"id": 3000, "name": "Pledge", "slug": "3000-pledge", "levels": [1]},
    },
    "skills": {
        "3": {
            "id": 3,
            "name": "Slash",
            "icon": "s3",
            "type": "Physical",
            "levels": {"1": {"description": "cut", "stats": {}}},
            "available_for": [{"class_name": "Fighter", "level": 1}],
        }
    },
}


class RecordingSession:
    """Collects added rows; delete/flush are no-ops for a full rewrite."""

    def __init__(self):
        self.added: list = []
        self.deleted_tables: list = []

    def execute(self, stmt):
        self.deleted_tables.append(stmt.table.name)
        return None

    def flush(self):
        pass

    def add(self, obj):
        self.added.append(obj)

    def scalar(self, _stmt):
        return None


def added_of(db, model):
    return [row for row in db.added if isinstance(row, model)]


def test_normalizer_splits_dataset():
    db = RecordingSession()
    normalize_character(db, PAYLOAD)

    races = added_of(db, CharacterRace)
    classes = added_of(db, CharacterClass)
    skills = added_of(db, CharacterSkill)

    assert [r.id for r in races] == ["human"]
    assert races[0].payload["branches"][0]["type"] == "warrior"
    assert {c.id for c in classes} == {0, 3000}
    assert [s.id for s in skills] == [3]
    assert skills[0].payload["available_for"] == [{"class_name": "Fighter", "level": 1}]


def test_normalizer_maps_classes_to_races_via_tree():
    db = RecordingSession()
    normalize_character(db, PAYLOAD)

    by_id = {c.id: c for c in added_of(db, CharacterClass)}
    assert by_id[0].race_id == "human"
    # Pledge is not part of any race tree.
    assert by_id[3000].race_id is None


def test_normalizer_clears_all_three_tables():
    db = RecordingSession()
    normalize_character(db, PAYLOAD)
    assert set(db.deleted_tables) == {
        "character_classes",
        "character_skills",
        "character_races",
    }


def test_normalizer_stores_meta_blob():
    db = RecordingSession()
    normalize_character(db, PAYLOAD)

    meta = next(row for row in db.added if getattr(row, "dataset_key", None) == META_KEY)
    assert meta.payload == {
        "generated_at": "2026-07-27T00:50:58+00:00",
        "wiki_base": "https://masterwork.wiki",
    }


def test_races_endpoint_falls_back_to_default_wiki_base(client, mock_db):
    race = SimpleNamespace(id="human", name="Human", payload={"branches": []})
    mock_db.scalars.side_effect = scalars_by_model({"CharacterRace": [race]})
    mock_db.scalar.return_value = None

    r = client.get("/api/character/races")
    assert r.status_code == 200
    body = r.json()
    assert body["wiki_base"] == "https://masterwork.wiki"
    assert body["races"] == [{"id": "human", "name": "Human", "branches": []}]


def test_class_endpoint_flattens_payload(client, mock_db):
    mock_db.get.return_value = SimpleNamespace(
        id=0,
        name="Fighter",
        slug="0-fighter",
        icon="i0",
        portrait="p0",
        race_id="human",
        payload={"levels": [1, 5], "skills_by_level": {"1": []}, "skills_up_to_level": {}},
    )
    r = client.get("/api/character/classes/0")
    assert r.status_code == 200
    assert r.json()["levels"] == [1, 5]
    assert r.json()["race_id"] == "human"


def test_class_endpoint_404(client, mock_db):
    mock_db.get.return_value = None
    assert client.get("/api/character/classes/999").status_code == 404


def test_skill_endpoint_404(client, mock_db):
    mock_db.get.return_value = None
    assert client.get("/api/character/skills/999").status_code == 404
