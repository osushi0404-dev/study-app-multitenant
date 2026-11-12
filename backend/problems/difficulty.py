"""
問題の難易度の数字（Problem.difficulty）と、表示・分析で使う文字の対応（ここだけに書く）

学習記録の分析（studylogs）は文字（'easy'・'medium'・'hard'）で扱い、
DB の欄を絞るときだけ数字に直す。
"""
LABEL_BY_LEVEL = {1: 'easy', 2: 'medium', 3: 'hard'}
LEVEL_BY_LABEL = {label: level for level, label in LABEL_BY_LEVEL.items()}
LABELS = tuple(LABEL_BY_LEVEL.values())  # ('easy', 'medium', 'hard')


def label_of(level):
    """数字を文字に。知らない値は None"""
    return LABEL_BY_LEVEL.get(level)
