from dataclasses import dataclass
import math
import re
import statistics

from matplotlib import pyplot as plt


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
            ("v", "b"), ("x", "gs"),
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
        name="Tok Pisin",
        iso="tpi",
        funny_words={},
        replacement_rules=[],
        multigraphs=["ng", "ai", "au", "oi"],
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


def whitespace_words(sentence: str):
    return re.findall("[^\\W\\d_]+", sentence.lower())


def segment_word(lang: LanguageSpecification, word: str):
    for x, y in lang.replacement_rules:
        word = word.replace(x, y)

    i = 0
    segments = []
    while i < len(word):
        segment = next_segment(lang.multigraphs, word, i)
        i += len(segment)
        if segment not in lang.silent_segments:
            segments.append(segment)

    return segments


def segment_words(lang: LanguageSpecification, sentence: str):
    words = [lang.funny_words.get(w, w) for w in whitespace_words(sentence)]
    word_segments = []
    for word in words:
        word_segments.append(segment_word(lang, word))

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


def all_segmented_words(lang: LanguageSpecification):
    sentences = load_sentences(lang)
    out: list[list[str]] = []
    for s in sentences:
        out += segment_words(lang, s)
    return out


EDGE_SEGMENT = "#"


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

    def add_all(self, segmented_words: list[list[str]], n: int):
        for segments in segmented_words:
            self.add(segments, n)

    def segment_bytes(self, segment: str, context: list[str]):
        d = self.ngram_continuations[tuple(context)]
        odds = d[segment] / sum(d.values())
        return -math.log2(odds)

    def bytes(self, segments: list[str], n: int):
        segments_with_edge = [EDGE_SEGMENT]*n + segments + [EDGE_SEGMENT]
        out = 0
        for i in range(len(segments)):
            out += self.segment_bytes(segments_with_edge[i+n], segments_with_edge[i:i+n])
        return out


DEFAULT_N = 2
MAX_N = 8


def show_basic_stats():
    n = DEFAULT_N
    for lang in LANGUAGES:
        print(lang.name)

        segmented_words = all_segmented_words(lang)
        print(f"{len(segmented_words)} total words")

        sentences = load_sentences(lang)
        orthographic_words = set()
        for sentence in sentences:
            words = whitespace_words(sentence)
            orthographic_words |= set(words)
        print(f"{len(orthographic_words)} distinct orthographic words")

        num_segments = 0
        all_segments = set()
        for segments in segmented_words:
            num_segments += len(segments)
            for s in segments:
                all_segments.add(s)
        print(f"{num_segments} total segments")
        print(f"{num_segments/len(segmented_words):.2f} average segments per word")
        print(f"{len(all_segments)} distinct segments")

        ss = SegmentSummary()
        ss.add_all(segmented_words, n)

        total_bytes = 0
        for segments in segmented_words:
            total_bytes += ss.bytes(segments, n)
        print(f"{round(total_bytes)} bytes")

        print()


def show_segmentation():
    for lang in LANGUAGES:
        sentences = load_sentences(lang)
        segmented_words = segment_words(lang, sentences[0])
        print(lang.name)
        print(sentences[0])
        print(segmented_words)
        print()


def show_bytes_per_segment():
    data = [
        (lang, [])
        for lang in LANGUAGES
    ]

    for n in range(0, MAX_N):
        for lang, bytes_per_segment in data:
            print(lang.name)

            segmented_words = all_segmented_words(lang)

            num_segments = 0
            segment_freqs = {}
            for segments in segmented_words:
                num_segments += len(segments)
                for s in segments:
                    segment_freqs[s] = segment_freqs.get(s, 0) + 1
            print(f"{len(segment_freqs)} distinct segments")
            for segment, count in sorted(list(segment_freqs.items()), key=lambda x: -x[1]):
                print(segment, count)

            ss = SegmentSummary()
            ss.add_all(segmented_words, n)

            total_bytes = 0
            for segments in segmented_words:
                total_bytes += ss.bytes(segments, n)

            bytes_per_segment.append(total_bytes / num_segments)
            print(f"{round(total_bytes / num_segments, 2)} bytes per segment")

            print()
        print('---')

    for lang, bytes_per_segment in data:
        plt.plot(*zip(*list(enumerate(bytes_per_segment))), label=lang.name)

    plt.title("Average bytes per segment by n")
    plt.legend()
    plt.show()


def show_total_bytes():
    data = [
        (lang, [])
        for lang in LANGUAGES
    ]

    for n in range(0, MAX_N):
        for lang, total_bytes_list in data:
            segmented_words = all_segmented_words(lang)

            ss = SegmentSummary()
            ss.add_all(segmented_words, n)

            total_bytes = 0
            for segments in segmented_words:
                total_bytes += ss.bytes(segments, n)
            print(lang.name, round(total_bytes))
            total_bytes_list.append(total_bytes)

        print()

    for lang, total_bytes_list in data:
        plt.plot(*zip(*list(enumerate(total_bytes_list))), label=lang.name)

    plt.title("Total bytes by n")
    plt.legend()
    plt.show()


def show_first_segments():
    n = 1
    print("First segments")
    print()
    for lang in LANGUAGES:
        print(lang.name)
        segmented_words = all_segmented_words(lang)

        ss = SegmentSummary()
        ss.add_all(segmented_words, n)

        left_edge = tuple([EDGE_SEGMENT]*n)
        first_segments = ss.ngram_continuations[left_edge]
        total_words = sum(first_segments.values())
        expected_bytes = 0
        for segment, times in sorted(list(first_segments.items()), key=lambda x: -x[1]):
            odds = times/total_words
            expected_bytes += -math.log2(odds)*odds
            print(f"  {segment:<3} {times:>4}  {100*odds:.2f}%")
        print(f"Expected bytes: {expected_bytes:.2f}")
    print()


def show_segment_position_bytes():
    n = DEFAULT_N
    max_position = 10
    for lang in LANGUAGES:
        segmented_words = all_segmented_words(lang)
        ss = SegmentSummary()
        ss.add_all(segmented_words, n)

        position_bytes = []
        for _ in range(max_position):
            position_bytes.append([])

        for word in segmented_words:
            segments = [EDGE_SEGMENT]*n
            for i, segment in enumerate(word):
                if i >= max_position:
                    break

                context = segments[-n:] if n > 0 else ()
                position_bytes[i].append(ss.segment_bytes(segment, context))
                segments.append(segment)

        avgs = []
        for bs in position_bytes:
            if not bs:
                break
            avgs.append(statistics.mean(bs))
        plt.plot(*zip(*list(enumerate(avgs))), label=lang.name)

    plt.title(f"Average bytes for segment at word position (n = {n})")
    plt.legend()
    plt.show()


def show_most_common_words():
    n = DEFAULT_N
    for lang in LANGUAGES:
        print(lang.name)
        sentences = load_sentences(lang)
        words = []
        for sentence in sentences:
            words += whitespace_words(sentence)
        segmented_words = []
        for word in words:
            segmented_words.append(segment_word(lang, word))

        ss = SegmentSummary()
        ss.add_all(segmented_words, n)

        word_freqs = {}
        for word in words:
            word_freqs[word] = word_freqs.get(word, 0) + 1

        word_bytes = []
        for word, count in sorted(list(word_freqs.items()), key=lambda x: -x[1])[:30]:
            segments = segment_word(lang, word)
            bs = ss.bytes(segments, n)
            print(f"{word:<8} {count:>4} {bs:.2f}")
            word_bytes.append(bs)

        print()

        plt.plot(*zip(*enumerate(word_bytes)), label=lang.name)

    plt.title(f"Bytes of most common words (n = {n})")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    show_basic_stats()
