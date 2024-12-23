from dataclasses import dataclass
import math
import os
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


LANGUAGES = {
    l.iso: l
    for l in [
        LanguageSpecification(
            name="Finnish",
            iso="fin",
            funny_words={},
            replacement_rules=[
                ("b", "p"),
                ("ng", "G"), ("g", "k"), ("G", "ng"),
            ],
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
                ("ü", "u"),
                ("ce", "ze"), ("ci", "zi"), ("ca", "ka"), ("co", "ko"), ("cu", "ku"),
            ],
            multigraphs=["ch", "ll"],
            silent_segments=["h"],
        ),
        LanguageSpecification(
            name="Albanian",
            iso="sqi",
            funny_words={},
            replacement_rules=[
                ("é", "e"),
            ],
            multigraphs=["dh", "gj", "ll", "nj", "rr", "sh", "th", "xh", "zh"],
            silent_segments=[],
        ),
        LanguageSpecification(
            name="Tagalog",
            iso="tgl",
            funny_words={"ng": "nang", "mga": "manga"},
            replacement_rules=[
                ("ca", "ka"), ("ce", "se"), ("ci", "si"), ("co", "ko"), ("cu", "ku"),
                ("j", "h"), ("v", "b"), ("x", "s"), ("z", "s"),
                ("á", "a"), ("â", "a"), # unfortunately glottal stop is not indicated in Tagalog orthography
            ],
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
            replacement_rules=[
                ('n', 'N'),
                ('Na', 'na'), ('Ne', 'ne'), ('Ni', 'ni'), ('No', 'no'), ('Nu', 'nu'),
            ],
            multigraphs=[],
            silent_segments=[],
        ),
    ]
}


CHAPTERS = {
    "Joshua 1": 18,
    "Joshua 2": 24,
    "Joshua 3": 17,
    "Esther 1": 22,
    "Esther 2": 23,
    "Esther 3": 15,
    "Lamentations 1": 22,
    "Lamentations 2": 22,
    "Lamentations 3": 66,
}


@dataclass
class Segment:
    value: str
    word_position: int | None  # None is reserved for edge segments


def next_segment(multigraphs: list[str], word: str, i: int) -> str:
    for multigraph in multigraphs:
        if word[i:i + len(multigraph)] == multigraph:
            return multigraph
    return word[i]


def segment_word(lang: LanguageSpecification, word: str) -> list[Segment]:
    word = lang.funny_words.get(word, word)
    for x, y in lang.replacement_rules:
        word = word.replace(x, y)

    i = 0
    segments: list[Segment] = []
    while i < len(word):
        segment = next_segment(lang.multigraphs, word, i)
        i += len(segment)
        if segment not in lang.silent_segments:
            segments.append(Segment(segment, word_position=len(segments)))

    return segments


VerseID = tuple[str, int]


@dataclass
class Verse:
    id: VerseID
    content: str
    language: LanguageSpecification

    def __post_init__(self):
        self.whitespace_words = re.findall("[^\\W\\d_]+", self.content.lower())

    def segmented_words(self) -> list[list[Segment]]:
        word_segments = []
        for word in self.whitespace_words:
            word_segments.append(segment_word(self.language, word))

        return word_segments

    def all_segments(self) -> list[Segment]:
        segments = []
        for segmented_word in self.segmented_words():
            segments += segmented_word
        return segments


@dataclass
class Chapter:
    name: str
    verses: list[Verse | None]


class Translation:
    def __init__(self, language: LanguageSpecification, edition_name: str, chapters: list[Chapter]):
        self.language = language
        self.edition_name = edition_name

        assert len(CHAPTERS) == len(chapters)
        for expected_name, chapter in zip(CHAPTERS, chapters):
            assert expected_name == chapter.name

        self.chapters = {
            chapter.name: chapter
            for chapter in chapters
        }

    def name(self):
        return f"{self.edition_name} ({self.language.name})"

    @classmethod
    def from_filename(cls, filename: str):
        match = re.fullmatch("translations/verses-([a-z]{3})-([a-zA-Z_]+).txt", filename)
        language_code, edition_name = match.groups()
        language = LANGUAGES[language_code]

        with open(filename, "r") as fh:
            lines = fh.read().split("\n")

        chapters: list[Chapter] = []
        for i, line in enumerate(lines):
            if line.strip() != line:
                print(f"Warning: {filename} line {i+1} has leading/trailing whitespace")

            if i % 2 == 1:
                if line != "":
                    print(filename, i)
                assert line == ""
                continue

            if line[0].isdigit():
                current_chapter = chapters[-1]
                match = re.match("(\\d+): ", line)
                line_no = int(match.groups()[0])
                current_chapter.verses[line_no - 1] = Verse(
                    (current_chapter.name, line_no - 1),
                    line[match.end():],
                    language,
                )

            else:
                chapters.append(Chapter(
                    name=line,
                    verses=[None]*CHAPTERS[line],
                ))

        return cls(language=language, edition_name=edition_name.replace("_", " "), chapters=chapters)

    def all_verses(self, skip_verses: list[VerseID]):
        for chapter in self.chapters.values():
            for verse in chapter.verses:
                if verse is None:
                    continue

                if verse.id in skip_verses:
                    continue

                yield verse

    def segments(self, skip_verses: list[VerseID], word_breaks: bool = True):
        words: list[list[Segment]] = []
        for verse in self.all_verses(skip_verses):
            if word_breaks:
                words += verse.segmented_words()
            else:
                words.append(verse.all_segments())
        return words


def load_all_translations():
    translations: list[Translation] = []
    missing_verses: list[tuple[str, int]] = []

    for filename in os.listdir("translations"):
        translation = Translation.from_filename(f"translations/{filename}")

        for chapter_name, length in CHAPTERS.items():
            chapter = translation.chapters[chapter_name]
            for i in range(length):
                if chapter.verses[i] is None:
                    missing_verses.append((chapter_name, i))
                    print(f"{translation.name()} is missing {chapter_name}:{i + 1}")

        translations.append(translation)

    return translations, missing_verses


EDGE_SEGMENT = Segment("#", None)


class SegmentSummary:
    def __init__(self):
        self.ngram_continuations: dict[tuple, dict[str, int]] = {}

    def add(self, segments: list[Segment], n: int):
        segments_with_edge = [EDGE_SEGMENT.value] * n + [s.value for s in segments] + [EDGE_SEGMENT.value]
        for i in range(len(segments)):
            start = tuple(segments_with_edge[i:i+n])
            segment = segments_with_edge[i+n]
            if start not in self.ngram_continuations:
                self.ngram_continuations[start] = {}
            self.ngram_continuations[start][segment] = self.ngram_continuations[start].get(segment, 0) + 1

    def add_all(self, segmented_words: list[list[Segment]], n: int):
        for segments in segmented_words:
            self.add(segments, n)

    def segment_bytes(self, segment: Segment, context: list[Segment]):
        d = self.ngram_continuations[tuple([s.value for s in context])]
        odds = d[segment.value] / sum(d.values())
        return -math.log2(odds)

    def bytes(self, segments: list[Segment], n: int):
        segments_with_edge = [EDGE_SEGMENT]*n + segments + [EDGE_SEGMENT]
        out = 0
        for i in range(len(segments)):
            out += self.segment_bytes(segments_with_edge[i+n], segments_with_edge[i:i+n])
        return out


DEFAULT_N = 2
MAX_N = 8


def show_basic_stats():
    n = DEFAULT_N

    translations, missing_verses = load_all_translations()
    for translation in translations:
        print(translation.name())

        segmented_words = translation.segments(missing_verses)
        print(f"{len(segmented_words)} total words")
        print(f"{len(list(translation.all_verses([])))} verses")

        orthographic_words = set()
        for verse in translation.all_verses(missing_verses):
            orthographic_words |= set(verse.whitespace_words)
        print(f"{len(orthographic_words)} distinct orthographic words")

        num_segments = 0
        all_segments = set()
        for segments in segmented_words:
            num_segments += len(segments)
            for s in segments:
                all_segments.add(s.value)
        print(f"{num_segments} total segments")
        print(f"{num_segments/len(segmented_words):.2f} average segments per word")
        print(f"{len(all_segments)} distinct segments {sorted(list(all_segments))}")

        ss = SegmentSummary()
        ss.add_all(segmented_words, n)

        total_bytes = 0
        for segments in segmented_words:
            total_bytes += ss.bytes(segments, n)
        print(f"{round(total_bytes)} bytes")

        print()


def show_segmentation():
    translations, missing_verses = load_all_translations()
    for translation in translations:
        verses = list(translation.all_verses(missing_verses))
        segmented_words = verses[0].segmented_words()
        print(translation.name())
        print(verses[0].content)
        print([[s.value for s in w] for w in segmented_words])
        print()


def show_bytes_per_segment(word_breaks: bool):
    translations, missing_verses = load_all_translations()
    data = [
        (translation, [])
        for translation in translations
    ]

    for n in range(0, MAX_N):
        for translation, bytes_per_segment in data:
            print(translation.name())
            segmented_words = translation.segments(missing_verses, word_breaks)

            num_segments = 0
            segment_freqs = {}
            for segments in segmented_words:
                num_segments += len(segments)
                for s in segments:
                    segment_freqs[s.value] = segment_freqs.get(s.value, 0) + 1
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

    for translation, bytes_per_segment in data:
        plt.plot(*zip(*list(enumerate(bytes_per_segment))), label=translation.name())

    plt.title("Average bytes per segment by n")
    plt.legend()
    plt.show()


def show_total_bytes(word_breaks: bool):
    translations, missing_verses = load_all_translations()
    data = [
        (translation, [])
        for translation in translations
    ]

    for n in range(0, MAX_N):
        print(f"n = {n}")
        print()
        for translation, total_bytes_list in data:
            segmented_words = translation.segments(missing_verses, word_breaks)

            ss = SegmentSummary()
            ss.add_all(segmented_words, n)

            total_bytes = 0
            for segments in segmented_words:
                total_bytes += ss.bytes(segments, n)
            print(translation.name(), round(total_bytes))
            total_bytes_list.append(total_bytes)

            print(f"Average possible continuations: {statistics.mean([len(conts) for conts in ss.ngram_continuations.values()]):.2f}")
            # bs = []
            # for context, continuations in ss.ngram_continuations.items():
            #     total = sum(continuations.values())
            #     to_print = False
            #     for count in continuations.values():
            #         b = count*-math.log2(count/total)
            #         bs.append(b)
            #         if b > 5:
            #             to_print = True
            #     if to_print:
            #         print(context, continuations)
            # print([round(b, 2) for b in sorted(bs) if b != 0])

        print()

    for translation, total_bytes_list in data:
        plt.plot(*zip(*list(enumerate(total_bytes_list))), label=translation.name())

    plt.title("Total bytes by n")
    plt.legend()
    plt.show()


def show_first_segments():
    n = 1

    translations, missing_verses = load_all_translations()

    print("First segments")
    print()

    for translation in translations:
        print(translation.name())
        segmented_words = translation.segments(missing_verses)

        ss = SegmentSummary()
        ss.add_all(segmented_words, n)

        left_edge = tuple([EDGE_SEGMENT.value]*n)
        first_segments = ss.ngram_continuations[left_edge]
        total_words = sum(first_segments.values())
        expected_bytes = 0
        for segment, times in sorted(list(first_segments.items()), key=lambda x: -x[1]):
            odds = times/total_words
            expected_bytes += -math.log2(odds)*odds
            print(f"  {segment:<3} {times:>4}  {100*odds:.2f}%")
        print(f"Expected bytes: {expected_bytes:.2f}")
    print()


def show_segment_position_bytes(word_breaks: bool):
    n = DEFAULT_N
    max_position = 15

    translations, missing_verses = load_all_translations()

    for translation in translations:
        segmented_words = translation.segments(missing_verses, word_breaks)
        ss = SegmentSummary()
        ss.add_all(segmented_words, n)

        position_bytes = []
        for _ in range(max_position):
            position_bytes.append([])

        for word in segmented_words:
            segments = [EDGE_SEGMENT]*n
            for segment in word:
                if segment.word_position >= max_position:
                    break

                context = segments[-n:] if n > 0 else ()
                position_bytes[segment.word_position].append(ss.segment_bytes(segment, context))
                segments.append(segment)

        avgs = []
        for bs in position_bytes:
            if not bs:
                break
            avgs.append(statistics.mean(bs))
        plt.plot(*zip(*list(enumerate(avgs))), label=translation.name())

    plt.title(f"Average bytes for segment at word position (n = {n})")
    plt.legend()
    plt.show()


def show_most_common_words():
    n = DEFAULT_N
    translations, missing_verses = load_all_translations()
    for translation in translations:
        print(translation.name())
        words = []
        for verse in translation.all_verses(missing_verses):
            words += verse.whitespace_words
        segmented_words = []
        for word in words:
            segmented_words.append(segment_word(translation.language, word))

        ss = SegmentSummary()
        ss.add_all(segmented_words, n)

        word_freqs = {}
        for word in words:
            word_freqs[word] = word_freqs.get(word, 0) + 1

        word_bytes = []
        for word, count in sorted(list(word_freqs.items()), key=lambda x: -x[1])[:10]:
            segments = segment_word(translation.language, word)
            bs = ss.bytes(segments, n)
            print(f"{word:<8} {count:>4} {bs:.2f}")
            word_bytes.append(bs)

        print()

        plt.plot(*zip(*enumerate(word_bytes)), label=translation.name())

    plt.title(f"Bytes of most common words (n = {n})")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    show_most_common_words()
