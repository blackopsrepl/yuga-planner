"""
Markdown Analyzer Library

This library provides a comprehensive Markdown parsing and analysis system. It consists of three main components:

1. MarkdownParser: Converts Markdown text into a stream of tokens representing different structural elements
   (headers, paragraphs, lists, code blocks, etc.). It handles both block-level and inline elements.

2. InlineParser: Processes inline Markdown elements within block tokens, such as:
   - Links and images
   - Inline code
   - Emphasis (bold, italic)
   - Footnotes
   - HTML inline elements

3. MarkdownAnalyzer: The main interface that combines parsing and analysis. It:
   - Parses the input text into tokens
   - Processes inline elements within tokens
   - Provides methods to identify and analyze different Markdown elements
   - Generates statistics about the document structure

Usage:
    analyzer = MarkdownAnalyzer(markdown_text)
    analysis = analyzer.analyze()  # Get document statistics
    headers = analyzer.identify_headers()  # Get all headers
    links = analyzer.identify_links()  # Get all links
    # etc.

The library supports standard Markdown features including:
- Headers (ATX and Setext style)
- Lists (ordered, unordered, and task lists)
- Code blocks (fenced and inline)
- Blockquotes
- Tables
- Links and images
- Footnotes
- HTML blocks and inline elements
"""

import re
from collections import defaultdict


### MAIN INTERFACE ###
class MarkdownAnalyzer:
    # def __init__(self, file_path, encoding='utf-8'):
    def __init__(self, text):
        # with open(file_path, 'r', encoding=encoding) as f:
        #     self.text = f.read()
        self.text = text
        parser = MarkdownParser(self.text)
        self.tokens = parser.parse()
        self.references = parser.references
        self.footnotes = parser.footnotes
        self.inline_parser = InlineParser(
            references=self.references, footnotes=self.footnotes
        )

        self._parse_inline_tokens()

    def _parse_inline_tokens(self):
        inline_types = ("paragraph", "header", "blockquote")
        for token in self.tokens:
            if token.type in inline_types and token.content:
                inline_data = self.inline_parser.parse_inline(token.content)
                token.meta.update(inline_data)

    def identify_headers(self):
        result = defaultdict(list)
        for token in self.tokens:
            if token.type == "header":
                result["Header"].append(
                    {"line": token.line, "level": token.level, "text": token.content}
                )
        return dict(result)

    def identify_paragraphs(self):
        result = defaultdict(list)
        for token in self.tokens:
            if token.type == "paragraph":
                result["Paragraph"].append(token.content)
        return dict(result)

    def identify_blockquotes(self):
        result = defaultdict(list)
        for token in self.tokens:
            if token.type == "blockquote":
                result["Blockquote"].append(token.content)
        return dict(result)

    def identify_code_blocks(self):
        result = defaultdict(list)
        for token in self.tokens:
            if token.type == "code":
                result["Code block"].append(
                    {
                        "start_line": token.line,
                        "content": token.content,
                        "language": token.meta.get("language"),
                    }
                )
        return dict(result)

    def identify_lists(self):
        result = defaultdict(list)
        for token in self.tokens:
            if token.type == "ordered_list":
                result["Ordered list"].append(token.meta["items"])
            elif token.type == "unordered_list":
                result["Unordered list"].append(token.meta["items"])
        return dict(result)

    def identify_tables(self):
        result = defaultdict(list)
        for token in self.tokens:
            if token.type == "table":
                result["Table"].append(
                    {"header": token.meta["header"], "rows": token.meta["rows"]}
                )
        return dict(result)

    def identify_links(self):
        result = defaultdict(list)
        for token in self.tokens:
            if "text_links" in token.meta:
                for l in token.meta["text_links"]:
                    result["Text link"].append(
                        {"line": token.line, "text": l["text"], "url": l["url"]}
                    )
            if "image_links" in token.meta:
                for img in token.meta["image_links"]:
                    result["Image link"].append(
                        {
                            "line": token.line,
                            "alt_text": img["alt_text"],
                            "url": img["url"],
                        }
                    )
        return dict(result)

    def identify_footnotes(self):
        result = []
        seen = set()
        for token in self.tokens:
            if "footnotes_used" in token.meta:
                for fn in token.meta["footnotes_used"]:
                    key = (fn["id"], fn["content"])
                    if key not in seen:
                        seen.add(key)
                        result.append(
                            {
                                "line": token.line,
                                "id": fn["id"],
                                "content": fn["content"],
                            }
                        )
        return result

    def identify_inline_code(self):
        codes = []
        for token in self.tokens:
            if "inline_code" in token.meta:
                for c in token.meta["inline_code"]:
                    codes.append({"line": token.line, "code": c})
        return codes

    def identify_emphasis(self):
        ems = []
        for token in self.tokens:
            if "emphasis" in token.meta:
                for e in token.meta["emphasis"]:
                    ems.append({"line": token.line, "text": e})
        return ems

    def identify_task_items(self):
        tasks = []
        for token in self.tokens:
            if token.type in ("ordered_list", "unordered_list"):
                for it in token.meta["items"]:
                    if it.get("task_item"):
                        tasks.append(
                            {
                                "line": token.line,
                                "text": it["text"],
                                "checked": it["checked"],
                            }
                        )
        return tasks

    def identify_html_blocks(self):
        # Gets HTML blocks
        result = []
        for token in self.tokens:
            if token.type == "html_block":
                result.append({"line": token.line, "content": token.content})
        return result

    def identify_html_inline(self):
        # Gets HTML tags from inline tokens
        result = []
        inline_types = ("paragraph", "header", "blockquote")
        for token in self.tokens:
            if token.type in inline_types and "html_inline" in token.meta:
                for h in token.meta["html_inline"]:
                    result.append({"line": token.line, "html": h})
        return result

    def count_words(self):
        words = self.text.split()
        return len(words)

    def count_characters(self):
        characters = [char for char in self.text if not char.isspace()]
        return len(characters)

    def analyze(self):
        headers = self.identify_headers().get("Header", [])
        paragraphs = self.identify_paragraphs().get("Paragraph", [])
        blockquotes = self.identify_blockquotes().get("Blockquote", [])
        code_blocks = self.identify_code_blocks().get("Code block", [])
        lists = self.identify_lists()
        ordered_lists = lists.get("Ordered list", [])
        unordered_lists = lists.get("Unordered list", [])
        tables = self.identify_tables().get("Table", [])
        html_blocks = self.identify_html_blocks()
        html_inline = self.identify_html_inline()

        analysis = {
            "headers": len(headers),
            "paragraphs": len(paragraphs),
            "blockquotes": len(blockquotes),
            "code_blocks": len(code_blocks),
            "ordered_lists": sum(len(l) for l in ordered_lists),
            "unordered_lists": sum(len(l) for l in unordered_lists),
            "tables": len(tables),
            "html_blocks": len(html_blocks),
            "html_inline_count": len(html_inline),
            "words": self.count_words(),
            "characters": self.count_characters(),
        }
        return analysis


### PARSING CLASSES ###
class BlockToken:
    """Represents a block-level Markdown element with its type, content, and metadata."""

    def __init__(self, type_, content="", level=None, meta=None, line=None):
        self.type = type_  # Type of block (header, paragraph, code, etc.)
        self.content = content  # The actual content of the block
        self.level = level  # Used for headers (h1-h6) and list indentation
        self.meta = meta or {}  # Additional metadata (language for code blocks, etc.)
        self.line = line  # Line number in the original document


class InlineParser:
    # Regular expressions for matching inline Markdown elements
    IMAGE_OR_LINK_RE = re.compile(
        r"(!?\[([^\]]*)\])(\(([^\)]+)\)|\[([^\]]+)\])"
    )  # Matches [text](url) or ![alt](url)
    CODE_INLINE_RE = re.compile(r"`([^`]+)`")  # Matches `code`
    EMPHASIS_RE = re.compile(
        r"(\*\*|__)(.*?)\1|\*(.*?)\*|_(.*?)_"
    )  # Matches **bold**, *italic*, _underline_
    FOOTNOTE_RE = re.compile(r"\[\^([^\]]+)\]")  # Matches [^footnote]
    HTML_INLINE_RE = re.compile(r"<[a-zA-Z/][^>]*>")  # Matches HTML tags
    HTML_INLINE_BLOCK_RE = re.compile(
        r"<([a-zA-Z]+)([^>]*)>(.*?)</\1>", re.DOTALL
    )  # Matches HTML blocks with content

    def __init__(self, references=None, footnotes=None):
        # Initialize with optional reference links and footnotes from the document
        self.references = references or {}  # For [text][ref] style links
        self.footnotes = footnotes or {}  # For [^footnote] style references

    def parse_inline(self, text):
        """Parse inline Markdown elements within a block of text."""
        result = {
            "text_links": [],  # Regular [text](url) links
            "image_links": [],  # ![alt](url) images
            "inline_code": [],  # `code` blocks
            "emphasis": [],  # **bold**, *italic* text
            "footnotes_used": [],  # [^footnote] references
            "html_inline": [],  # HTML tags and blocks
        }

        # Process footnotes first to avoid conflicts with other patterns
        used_footnotes = set()
        for fm in self.FOOTNOTE_RE.finditer(text):
            fid = fm.group(1)
            if fid in self.footnotes and fid not in used_footnotes:
                used_footnotes.add(fid)
                result["footnotes_used"].append(
                    {"id": fid, "content": self.footnotes[fid]}
                )

        # Find inline code blocks
        for cm in self.CODE_INLINE_RE.finditer(text):
            code = cm.group(1)
            result["inline_code"].append(code)

        # Find emphasized text (bold, italic, underline)
        for em_match in self.EMPHASIS_RE.finditer(text):
            emphasized_text = (
                em_match.group(2) or em_match.group(3) or em_match.group(4)
            )
            if emphasized_text:
                result["emphasis"].append(emphasized_text)

        # Process HTML blocks first to avoid conflicts with other patterns
        temp_text = text
        for block_match in self.HTML_INLINE_BLOCK_RE.finditer(text):
            html_content = block_match.group(0)
            result["html_inline"].append(html_content)
            temp_text = temp_text.replace(html_content, "")

        # Process links and images
        for mm in self.IMAGE_OR_LINK_RE.finditer(temp_text):
            prefix = mm.group(1)  # The [text] or ![alt] part
            inner_text = mm.group(2)  # The text inside []
            url = mm.group(4)  # The (url) part
            ref_id = mm.group(5)  # The [ref] part for reference-style links

            is_image = prefix.startswith("!")
            final_url = url
            if ref_id and ref_id.lower() in self.references:
                final_url = self.references[ref_id.lower()]

            if is_image:
                if final_url:
                    result["image_links"].append(
                        {"alt_text": inner_text, "url": final_url}
                    )
            else:
                if final_url:
                    result["text_links"].append({"text": inner_text, "url": final_url})
        return result


class MarkdownParser:
    # Regular expressions for matching block-level Markdown elements
    FRONTMATTER_RE = re.compile(r"^---\s*$")  # Matches YAML frontmatter delimiters
    ATX_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$")  # Matches # Header style
    SETEXT_H1_RE = re.compile(r"^=+\s*$")  # Matches ==== style h1
    SETEXT_H2_RE = re.compile(r"^-+\s*$")  # Matches ---- style h2
    FENCE_RE = re.compile(r"^```([^`]*)$")  # Matches code fence start
    BLOCKQUOTE_RE = re.compile(r"^(>\s?)(.*)$")  # Matches > quote style
    ORDERED_LIST_RE = re.compile(r"^\s*\d+\.\s+(.*)$")  # Matches 1. list style
    UNORDERED_LIST_RE = re.compile(r"^\s*[-+*]\s+(.*)$")  # Matches - list style
    HR_RE = re.compile(r"^(\*{3,}|-{3,}|_{3,})\s*$")  # Matches horizontal rules
    TABLE_SEPARATOR_RE = re.compile(
        r"^\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$"
    )  # Matches table separators
    REFERENCE_DEF_RE = re.compile(
        r"^\[([^\]]+)\]:\s+(.*?)\s*$", re.MULTILINE
    )  # Matches [ref]: url definitions
    FOOTNOTE_DEF_RE = re.compile(
        r"^\[\^([^\]]+)\]:\s+(.*?)\s*$", re.MULTILINE
    )  # Matches [^footnote]: content
    HTML_BLOCK_START = re.compile(
        r"^(<([a-zA-Z]+)([^>]*)>|<!--)"
    )  # Matches HTML block start
    HTML_BLOCK_END_COMMENT = re.compile(r"-->\s*$")  # Matches HTML comment end

    def __init__(self, text):
        """Initialize parser with the Markdown text to parse."""
        self.lines = text.split("\n")
        self.length = len(self.lines)
        self.pos = 0  # Current position in the text
        self.tokens = []  # List of parsed tokens
        self.text = text
        self.references = {}  # Reference-style link definitions
        self.footnotes = {}  # Footnote definitions
        self.extract_references_and_footnotes()

    def extract_references_and_footnotes(self):
        """Extract all reference-style links and footnotes from the document."""
        for m in self.REFERENCE_DEF_RE.finditer(self.text):
            rid, url = m.groups()
            self.references[rid.lower()] = url

        for m in self.FOOTNOTE_DEF_RE.finditer(self.text):
            fid, content = m.groups()
            self.footnotes[fid] = content

    def parse(self):
        """Main parsing method that processes the entire document."""
        # Check for frontmatter at the start
        if self.pos < self.length and self.FRONTMATTER_RE.match(
            self.lines[self.pos].strip()
        ):
            self.parse_frontmatter()

        # Process the document line by line
        while self.pos < self.length:
            if self.pos >= self.length:
                break
            line = self.lines[self.pos]
            if not line.strip():
                self.pos += 1
                continue

            # Check for table start
            if self.is_table_start():
                self.parse_table()
                continue

            # Check for HTML block
            if self.is_html_block_start(line):
                self.parse_html_block()
                continue

            # Check for ATX-style headers (# Header)
            m = self.ATX_HEADER_RE.match(line)
            if m:
                level = len(m.group(1))
                text = m.group(2).strip()
                self.tokens.append(
                    BlockToken("header", content=text, level=level, line=self.pos + 1)
                )
                self.pos += 1
                continue

            # Check for Setext-style headers (=== or ---)
            if self.pos + 1 < self.length:
                next_line = self.lines[self.pos + 1].strip()
                if self.SETEXT_H1_RE.match(next_line):
                    text = line.strip()
                    self.tokens.append(
                        BlockToken("header", content=text, level=1, line=self.pos + 1)
                    )
                    self.pos += 2
                    continue
                if self.SETEXT_H2_RE.match(next_line):
                    text = line.strip()
                    self.tokens.append(
                        BlockToken("header", content=text, level=2, line=self.pos + 1)
                    )
                    self.pos += 2
                    continue

            # Check for horizontal rule
            if self.HR_RE.match(line.strip()):
                self.tokens.append(BlockToken("hr", line=self.pos + 1))
                self.pos += 1
                continue

            # Check for fenced code block
            fm = self.FENCE_RE.match(line.strip())
            if fm:
                lang = fm.group(1).strip()
                self.parse_fenced_code_block(lang)
                continue

            # Check for blockquote
            bm = self.BLOCKQUOTE_RE.match(line)
            if bm:
                self.parse_blockquote()
                continue

            # Check for lists
            om = self.ORDERED_LIST_RE.match(line)
            um = self.UNORDERED_LIST_RE.match(line)
            if om or um:
                self.parse_list(ordered=bool(om))
                continue

            # If no other block type matches, treat as paragraph
            self.parse_paragraph()

        return self.tokens

    def is_html_block_start(self, line):
        # Verify if line seems to be HTML
        return self.HTML_BLOCK_START.match(line.strip()) is not None

    def parse_html_block(self):
        start = self.pos
        lines = []
        first_line = self.lines[self.pos].strip()
        comment_mode = first_line.startswith("<!--")

        # Read HTML block until empty line / eof
        while self.pos < self.length:
            line = self.lines[self.pos]
            lines.append(line)
            self.pos += 1

            if comment_mode and self.HTML_BLOCK_END_COMMENT.search(line):
                break
            else:
                # If next line is empty or doesn't exist, stop
                if self.pos < self.length:
                    nxt_line = self.lines[self.pos]
                    if not nxt_line.strip():
                        # End of block
                        break
                else:
                    # End of file
                    break

        content = "\n".join(lines)
        self.tokens.append(BlockToken("html_block", content=content, line=start + 1))

    def starts_new_block_peek(self):
        # Check next line without advancing
        if self.pos < self.length:
            nxt = self.lines[self.pos].strip()
            return self.starts_new_block(nxt)
        return False

    def is_table_start(self):
        if self.pos + 1 < self.length:
            line = self.lines[self.pos].strip()
            next_line = self.lines[self.pos + 1].strip()
            if (
                "|" in line
                and "|" in next_line
                and self.TABLE_SEPARATOR_RE.match(next_line)
            ):
                return True
        return False

    def parse_table(self):
        start = self.pos
        header_line = self.lines[self.pos].strip()
        separator_line = self.lines[self.pos + 1].strip()
        self.pos += 2
        rows = []
        while self.pos < self.length:
            line = self.lines[self.pos].strip()
            if not line or self.starts_new_block(line):
                break
            rows.append(line)
            self.pos += 1

        header_cells = [
            h.strip() for h in header_line.strip("|").split("|") if h.strip()
        ]
        data_rows = []
        for r in rows:
            data_rows.append([c.strip() for c in r.strip("|").split("|") if c.strip()])

        self.tokens.append(
            BlockToken(
                "table",
                meta={"header": header_cells, "rows": data_rows},
                line=start + 1,
            )
        )

    def starts_new_block(self, line):
        return (
            self.ATX_HEADER_RE.match(line)
            or self.FRONTMATTER_RE.match(line)
            or self.FENCE_RE.match(line)
            or self.BLOCKQUOTE_RE.match(line)
            or self.ORDERED_LIST_RE.match(line)
            or self.UNORDERED_LIST_RE.match(line)
            or self.HR_RE.match(line)
            or self.SETEXT_H1_RE.match(line)
            or self.SETEXT_H2_RE.match(line)
            or self.HTML_BLOCK_START.match(line)
        )

    def parse_frontmatter(self):
        self.pos += 1
        start = self.pos
        while self.pos < self.length:
            if self.FRONTMATTER_RE.match(self.lines[self.pos].strip()):
                content = "\n".join(self.lines[start : self.pos])
                self.tokens.append(BlockToken("frontmatter", content=content))
                self.pos += 1
                return
            self.pos += 1
        content = "\n".join(self.lines[start:])
        self.tokens.append(BlockToken("frontmatter", content=content))
        self.pos = self.length

    def parse_fenced_code_block(self, lang):
        self.pos += 1
        start = self.pos
        while self.pos < self.length:
            line = self.lines[self.pos]
            if line.strip().startswith("```"):
                content = "\n".join(self.lines[start : self.pos])
                self.tokens.append(
                    BlockToken(
                        "code", content=content, meta={"language": lang}, line=start + 1
                    )
                )
                self.pos += 1
                return
            self.pos += 1
        content = "\n".join(self.lines[start:])
        self.tokens.append(
            BlockToken("code", content=content, meta={"language": lang}, line=start + 1)
        )
        self.pos = self.length

    def parse_blockquote(self):
        start = self.pos
        lines = []
        while self.pos < self.length:
            line = self.lines[self.pos]
            bm = self.BLOCKQUOTE_RE.match(line)
            if bm:
                lines.append(bm.group(2))
                self.pos += 1
            else:
                break
        content = "\n".join(lines)
        self.tokens.append(BlockToken("blockquote", content=content, line=start + 1))

    def parse_list(self, ordered):
        start = self.pos
        items = []
        current_item = []
        list_pattern = self.ORDERED_LIST_RE if ordered else self.UNORDERED_LIST_RE

        while self.pos < self.length:
            line = self.lines[self.pos]
            if not line.strip():
                if current_item:
                    items.append("\n".join(current_item).strip())
                    current_item = []
                self.pos += 1
                continue

            if self.starts_new_block(line.strip()) and not (
                self.ORDERED_LIST_RE.match(line.strip())
                or self.UNORDERED_LIST_RE.match(line.strip())
            ):
                break

            lm = list_pattern.match(line)
            if lm:
                if current_item:
                    items.append("\n".join(current_item).strip())
                    current_item = []
                current_item.append(lm.group(1))
                self.pos += 1
            else:
                current_item.append(line.strip())
                self.pos += 1

        if current_item:
            items.append("\n".join(current_item).strip())

        task_re = re.compile(r"^\[( |x)\]\s+(.*)$")
        final_items = []
        for it in items:
            lines = it.split("\n")
            first_line = lines[0].strip()
            m = task_re.match(first_line)
            if m:
                state = m.group(1)
                text = m.group(2)
                task_checked = state == "x"
                final_items.append(
                    {"text": text, "task_item": True, "checked": task_checked}
                )
            else:
                final_items.append({"text": it, "task_item": False})

        list_type = "ordered_list" if ordered else "unordered_list"
        self.tokens.append(
            BlockToken(list_type, meta={"items": final_items}, line=start + 1)
        )

    def parse_paragraph(self):
        start = self.pos
        lines = []
        while self.pos < self.length:
            line = self.lines[self.pos]
            if not line.strip():
                self.pos += 1
                break
            if self.starts_new_block(line.strip()):
                break
            lines.append(line)
            self.pos += 1

        content = "\n".join(lines).strip()
        if content:
            self.tokens.append(BlockToken("paragraph", content=content, line=start + 1))
