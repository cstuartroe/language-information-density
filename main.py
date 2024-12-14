from dataclasses import dataclass
import math
import re


@dataclass
class LanguageSpecification:
    name: str
    iso: str
    funny_words: dict[str, str]  # Irregularly spelled words, like Spanish "y"
    replacement_rules: list[tuple[str, str]]
    multigraphs: list[str]  # Multigraphs, like Spanish "ch"
    silent_segments: list[str]


LANGUAGES = [
    LanguageSpecification(
        name="Finnish",
        iso="fin",
        funny_words={},
        replacement_rules=[],
        multigraphs=["ng", "aa", "ää", "ee", "ii", "oo", "öö", "uu", "yy", "ie", "uo", "yö"],
        silent_segments=[],
    ),
    LanguageSpecification(
        name="Māori",
        iso="mri",
        funny_words={},
        replacement_rules=[],
        multigraphs=["wh", "ng"],
        silent_segments=[],
    ),
    LanguageSpecification(
        name="Somali",
        iso="som",
        funny_words={},
        replacement_rules=[],
        multigraphs=["kh", "sh", "dh", "aa", "ee", "ii", "oo", "uu"],
        silent_segments=[],
    ),
    LanguageSpecification(
        name="Spanish",
        iso="spa",
        funny_words={"y": "i"},
        replacement_rules=[
            ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
            ("v", "b"),
            ("que", "ke"), ("qui", "ki"),
            ("ge", "je"), ("gi", "ji"), ("gue", "ge"), ("gui", "gi"),
            ("ce", "ze"), ("ci", "zi"), ("ca", "ka"), ("co", "ko"), ("cu", "ku"),
        ],
        multigraphs=["ch", "ll"],
        silent_segments=["h"],
    ),
    LanguageSpecification(
        name="Albanian",
        iso="sqi",
        funny_words={},
        replacement_rules=[],
        multigraphs=["dh", "gj", "ll", "nj", "rr", "sh", "th", "xh", "zh"],
        silent_segments=[],
    ),
    LanguageSpecification(
        name="Tagalog",
        iso="tgl",
        funny_words={"ng": "nang", "mga": "manga"},
        replacement_rules=[],
        multigraphs=["ng"],
        silent_segments=[],
    ),
    LanguageSpecification(
        name="Toki Pona",
        iso="tok",
        funny_words={},
        replacement_rules=[],
        multigraphs=[],
        silent_segments=[],
    ),
]


def next_segment(multigraphs: list[str], word: str, i: int):
    for multigraph in multigraphs:
        if word[i:i+len(multigraph)] == multigraph:
            return multigraph
    return word[i]


def segment_words(lang: LanguageSpecification, sentence: str):
    words = re.findall("[^\\W\\d_]+", sentence.lower())
    words = [lang.funny_words.get(w, w) for w in words]
    for i, w in enumerate(words):
        for x, y in lang.replacement_rules:
            w = w.replace(x, y)
        words[i] = w

    word_segments = []
    for w in words:
        i = 0
        segments = []
        while i < len(w):
            segment = next_segment(lang.multigraphs, w, i)
            i += len(segment)
            if segment not in lang.silent_segments:
                segments.append(segment)
        word_segments.append(segments)

    return word_segments


def load_sentences(lang: LanguageSpecification):
    with open(f"translations/lamentations-{lang.iso}.txt", "r") as fh:
        content = fh.read()

    sentences: list[str] = []

    for line in content.split("\n"):
        m = re.match("\\d+: ", line)
        if m is not None:
            sentences.append(line[m.span()[1]:])

    assert len(sentences) == 110

    return sentences


class SegmentSummary:
    def __init__(self):
        self.ngram_continuations: dict[tuple, dict[str, int]] = {}

    def add(self, segments: list[str], n: int):
        segments_with_edge = ["#"] * n + segments + ["#"]
        for i in range(len(segments)):
            start = tuple(segments_with_edge[i:i+n])
            segment = segments_with_edge[i+n]
            if start not in self.ngram_continuations:
                self.ngram_continuations[start] = {}
            self.ngram_continuations[start][segment] = self.ngram_continuations[start].get(segment, 0) + 1

    def bytes(self, segments: list[str], n: int):
        segments_with_edge = ["#"]*n + segments + ["#"]
        out = 0
        for i in range(len(segments)):
            d = self.ngram_continuations[tuple(segments_with_edge[i:i+n])]
            odds = d[segments_with_edge[i+n]]/sum(d.values())
            out += -math.log2(odds)
        return out


if __name__ == "__main__":
    for lang in LANGUAGES:
        # print(lang.name)

        sentences = load_sentences(lang)
        all_segment_words: list[list[str]] = []
        for s in sentences:
            all_segment_words += segment_words(lang, s)

        n = 3
        ss = SegmentSummary()
        for segments in all_segment_words:
            ss.add(segments, n)

        total_bytes = 0
        for segments in all_segment_words:
            total_bytes += ss.bytes(segments, n)
        print(lang.name, round(total_bytes))

        # sentence = sentences[0]
        # print(sentence)
        # sentence_bytes = 0
        # for segments in segment_words(lang, sentence):
        #     b = ss.bytes(segments, n)
        #     print(segments, b)
        #     sentence_bytes += b
        # print(sentence_bytes)
        # print()
