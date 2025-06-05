import unittest
from fill_release_year import clean_artist_name

class TestCleanArtistName(unittest.TestCase):
    def test_basic_separators(self):
        self.assertEqual(clean_artist_name('Juan y Pedro'), 'Juan')
        self.assertEqual(clean_artist_name('Juan Y Pedro'), 'Juan')
        self.assertEqual(clean_artist_name('A & B'), 'A')
        self.assertEqual(clean_artist_name('A AND B'), 'A')
        self.assertEqual(clean_artist_name('Grupo / Colaborador'), 'Grupo')
        self.assertEqual(clean_artist_name('Grupo, Otro'), 'Grupo')

    def test_no_separator(self):
        self.assertEqual(clean_artist_name('SoloArtist'), 'SoloArtist')
        self.assertEqual(clean_artist_name('Beyoncé'), 'Beyonce')

if __name__ == '__main__':
    unittest.main()
