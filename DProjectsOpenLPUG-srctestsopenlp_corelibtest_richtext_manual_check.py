

REAL_DB_VERSES = [
    # From the actual local songs.sqlite - "Come Holy Spirit" (id 430), verse 1
    "[Bm] Come[A] Holy[F#m] Spir[G]it,[Bm] fall[A] on[G] us\n"
    "[Bm] Burn[A] like a[F#m] fir[G]e\n"
    "{sfp3}Living[Em] flame[D] of[A] love\u271d\ufe0f{/sfp3}",
    # From the actual local songs.sqlite - "Fragrance to Fire" (id 686), verse 1
    "{The Fragrance of my Worship\nRose up to the Father\nNoises, Thundering's, Earthquakes\n"
    "Were the Response to my Worship\nThe Fragrance of my Worship\nRose up to the Father\n"
    "Noises, Thundering's, Lightnings\nWere the Response to my Worship} [x2]",
]


@pytest.mark.parametrize('text', REAL_DB_VERSES)
def test_real_local_song_round_trip(settings, text):
    FormattingTags.load_tags()
    document = QtGui.QTextDocument()
    tags_to_document(text, document)
    result = document_to_tags(document)
    assert result == text, f'ROUND-TRIP MISMATCH:\n  original: {text!r}\n  result:   {result!r}'
