MOOD_GENRES = {
    "Happy": ["Comedy", "Family", "Animation", "Musical"],
    "Excited": ["Action", "Adventure", "Sci-Fi", "Thriller"],
    "Relaxed": ["Documentary", "Drama", "Romance"],
    "Romantic": ["Romance", "Drama"],
    "Thoughtful": ["Documentary", "Drama", "Mystery"],
    "Scared": ["Horror", "Thriller", "Mystery"],
    "Nostalgic": ["Animation", "Family", "Fantasy"],
    "Sad": ["Drama", "Romance"],
}

MOOD_EMOJI = {
    "Happy": "😄",
    "Excited": "🤩",
    "Relaxed": "😌",
    "Romantic": "💘",
    "Thoughtful": "🤔",
    "Scared": "😱",
    "Nostalgic": "🕰️",
    "Sad": "😢",
}


def mood_genres(mood):
    return MOOD_GENRES.get(mood, [])
